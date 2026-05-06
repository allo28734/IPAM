"""
Fortinet FortiGate Adapter.

Supports both API token and admin username/password authentication.
Communicates with the FortiOS REST API (CMDB + Monitor endpoints)
to pull interfaces, DHCP leases, and connected device information.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Optional

import httpx

from app.integrations.base_adapter import (
    BaseAdapter, NetworkData, ClientData, DeviceData,
)

logger = logging.getLogger(__name__)


class FortiGateAdapter(BaseAdapter):
    """Fortinet FortiGate REST API adapter."""

    VENDOR_ID = "fortigate"
    VENDOR_NAME = "Fortinet FortiGate"
    VENDOR_DESCRIPTION = "On-premises FortiGate firewall via the FortiOS REST API"
    REQUIRES_BASE_URL = True
    SUPPORTS_API_KEY = True
    SUPPORTS_USERNAME_PASSWORD = True
    EXTRA_CONFIG_FIELDS = [
        {
            "key": "vdom",
            "label": "VDOM",
            "type": "text",
            "required": False,
            "help": "Virtual domain. Defaults to 'root' if not specified.",
        },
        {
            "key": "verify_ssl",
            "label": "Verify SSL Certificate",
            "type": "boolean",
            "required": False,
            "help": "Set to false for self-signed certificates (common in lab environments).",
        },
    ]

    # ── Internal helpers ───────────────────────────────────────

    def _build_client(self) -> httpx.AsyncClient:
        """Build an httpx client with appropriate auth headers."""
        base = self.provider.base_url.rstrip("/")
        verify = self.extra.get("verify_ssl", False)
        headers = {}

        api_key = self.api_key
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        return httpx.AsyncClient(
            base_url=base,
            headers=headers,
            verify=verify,
            timeout=30.0,
        )

    async def _login_session(self, client: httpx.AsyncClient) -> None:
        """
        Fallback: authenticate with username/password to get a session cookie.
        Only used when no API key is configured.
        """
        if self.api_key:
            return  # Token auth takes precedence

        username = self.provider.username
        password = self.password
        if not username or not password:
            raise RuntimeError("FortiGate requires either an API key or username/password")

        resp = await client.post(
            "/logincheck",
            data=f"username={username}&secretkey={password}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200 or "error" in resp.text.lower():
            raise RuntimeError(f"FortiGate login failed: {resp.status_code}")

    @property
    def _vdom_param(self) -> dict:
        vdom = self.extra.get("vdom", "root")
        return {"vdom": vdom}

    # ── Public interface ───────────────────────────────────────

    async def test_connection(self) -> dict:
        try:
            async with self._build_client() as client:
                await self._login_session(client)
                resp = await client.get(
                    "/api/v2/cmdb/system/global",
                    params=self._vdom_param,
                )
                resp.raise_for_status()
                data = resp.json()
                hostname = data.get("results", {}).get("hostname", "unknown")
                return {
                    "ok": True,
                    "message": f"Connected to FortiGate: {hostname}",
                    "details": {"hostname": hostname},
                }
        except Exception as e:
            logger.error(f"FortiGate connection test failed: {e}")
            return {"ok": False, "message": str(e), "details": None}

    async def fetch_networks(self) -> list[NetworkData]:
        results: list[NetworkData] = []
        try:
            async with self._build_client() as client:
                await self._login_session(client)

                # Fetch interfaces
                resp = await client.get(
                    "/api/v2/cmdb/system/interface",
                    params=self._vdom_param,
                )
                resp.raise_for_status()
                interfaces = resp.json().get("results", [])

                for iface in interfaces:
                    ip_str = iface.get("ip")
                    if not ip_str or ip_str == "0.0.0.0 0.0.0.0":
                        continue

                    # FortiGate returns IP as "10.0.1.1 255.255.255.0"
                    parts = ip_str.split()
                    if len(parts) == 2:
                        try:
                            addr = parts[0]
                            mask = parts[1]
                            network = ipaddress.ip_network(
                                f"{addr}/{mask}", strict=False
                            )
                            cidr = str(network)
                        except ValueError:
                            continue
                    else:
                        continue

                    results.append(NetworkData(
                        cidr=cidr,
                        name=iface.get("alias") or iface.get("name"),
                        vlan_id=iface.get("vlanid"),
                        gateway=parts[0],  # interface IP is often the gateway
                        description=f"FortiGate interface: {iface.get('name', '')}",
                        raw=iface,
                    ))

                # Fetch DHCP server scopes
                try:
                    dhcp_resp = await client.get(
                        "/api/v2/cmdb/system.dhcp/server",
                        params=self._vdom_param,
                    )
                    dhcp_resp.raise_for_status()
                    dhcp_servers = dhcp_resp.json().get("results", [])

                    for srv in dhcp_servers:
                        for ip_range in srv.get("ip-range", []):
                            start = ip_range.get("start-ip")
                            end = ip_range.get("end-ip")
                            if start and end:
                                # Add DHCP scope info to description of matching network
                                for net in results:
                                    try:
                                        if (ipaddress.ip_address(start) in
                                                ipaddress.ip_network(net.cidr, strict=False)):
                                            net.description = (
                                                f"{net.description} | DHCP: {start}-{end}"
                                            )
                                    except ValueError:
                                        pass
                except Exception as e:
                    logger.warning(f"FortiGate DHCP fetch failed (non-fatal): {e}")

        except Exception as e:
            logger.error(f"FortiGate fetch_networks failed: {e}")

        return results

    async def fetch_clients(self) -> list[ClientData]:
        results: list[ClientData] = []
        try:
            async with self._build_client() as client:
                await self._login_session(client)

                # Try to get DHCP leases from monitor endpoint
                try:
                    resp = await client.get(
                        "/api/v2/monitor/dhcp/server/leases",
                        params=self._vdom_param,
                    )
                    resp.raise_for_status()
                    leases = resp.json().get("results", [])

                    for lease in leases:
                        ip = lease.get("ip")
                        if not ip:
                            continue
                        results.append(ClientData(
                            ip_address=ip,
                            mac_address=lease.get("mac"),
                            hostname=lease.get("hostname"),
                            vendor=lease.get("manufacturer"),
                            vlan_id=lease.get("vci", {}).get("vlanid") if isinstance(lease.get("vci"), dict) else None,
                            raw=lease,
                        ))
                except Exception as e:
                    logger.warning(f"FortiGate DHCP leases fetch failed: {e}")

                # Also try the device query endpoint
                try:
                    resp = await client.get(
                        "/api/v2/monitor/user/device/query",
                        params=self._vdom_param,
                    )
                    resp.raise_for_status()
                    devices = resp.json().get("results", [])

                    existing_ips = {c.ip_address for c in results}
                    for dev in devices:
                        ip = dev.get("ipv4_address")
                        if not ip or ip in existing_ips:
                            continue
                        results.append(ClientData(
                            ip_address=ip,
                            mac_address=dev.get("mac"),
                            hostname=dev.get("host", {}).get("name") if isinstance(dev.get("host"), dict) else None,
                            os=dev.get("os_name"),
                            vendor=dev.get("vendor"),
                            device_type=dev.get("type"),
                            raw=dev,
                        ))
                except Exception as e:
                    logger.warning(f"FortiGate device query failed: {e}")

        except Exception as e:
            logger.error(f"FortiGate fetch_clients failed: {e}")

        return results

    async def fetch_devices(self) -> list[DeviceData]:
        results: list[DeviceData] = []
        try:
            async with self._build_client() as client:
                await self._login_session(client)

                resp = await client.get(
                    "/api/v2/monitor/system/interface",
                    params=self._vdom_param,
                )
                resp.raise_for_status()
                interfaces = resp.json().get("results", {})

                # The FortiGate itself is the primary device
                try:
                    status_resp = await client.get(
                        "/api/v2/cmdb/system/global",
                        params=self._vdom_param,
                    )
                    status_resp.raise_for_status()
                    global_cfg = status_resp.json().get("results", {})

                    results.append(DeviceData(
                        name=global_cfg.get("hostname", "FortiGate"),
                        model=global_cfg.get("platform-type"),
                        serial=global_cfg.get("serial-number"),
                        firmware=global_cfg.get("version"),
                        device_type="firewall",
                    ))
                except Exception:
                    pass

                # Report each active interface as a sub-entry
                for iface_name, iface_data in interfaces.items():
                    if isinstance(iface_data, dict):
                        ip = iface_data.get("ip")
                        mac = iface_data.get("mac")
                        if ip and ip != "0.0.0.0":
                            results.append(DeviceData(
                                ip_address=ip,
                                mac_address=mac,
                                name=f"FortiGate:{iface_name}",
                                device_type="firewall_interface",
                                raw=iface_data,
                            ))

        except Exception as e:
            logger.error(f"FortiGate fetch_devices failed: {e}")

        return results
