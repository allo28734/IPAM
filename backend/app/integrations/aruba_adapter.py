"""
Aruba Central Adapter.

Uses the ``pycentral`` SDK to communicate with the Aruba Central
REST API, pulling access points, switches, clients, and network
configurations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.integrations.base_adapter import (
    BaseAdapter, NetworkData, ClientData, DeviceData,
)

logger = logging.getLogger(__name__)


class ArubaCentralAdapter(BaseAdapter):
    """Aruba Central cloud management adapter."""

    VENDOR_ID = "aruba_central"
    VENDOR_NAME = "Aruba Central"
    VENDOR_DESCRIPTION = "HPE Aruba Central cloud-managed networking"
    REQUIRES_BASE_URL = True
    SUPPORTS_API_KEY = False
    SUPPORTS_USERNAME_PASSWORD = True  # client_id / client_secret
    EXTRA_CONFIG_FIELDS = [
        {
            "key": "customer_id",
            "label": "Customer ID",
            "type": "text",
            "required": True,
            "help": "Your Aruba Central customer ID (found under API Gateway).",
        },
    ]

    # ── Internal helpers ───────────────────────────────────────

    def _get_central(self):
        """Create an ArubaCentralBase connection."""
        from pycentral.base import ArubaCentralBase

        central_info = {
            "base_url": self.provider.base_url,
            "client_id": self.provider.username,
            "client_secret": self.password,
            "customer_id": self.extra.get("customer_id", ""),
            "token_store": {"type": "local", "path": "/tmp/aruba_tokens"},
        }

        return ArubaCentralBase(central_info=central_info)

    async def _api_call(self, central, method: str, path: str, **kwargs) -> dict:
        """Execute an API call in a thread to avoid blocking."""
        return await asyncio.to_thread(
            central.command, api_method=method, api_path=path, **kwargs
        )

    # ── Public interface ───────────────────────────────────────

    async def test_connection(self) -> dict:
        try:
            central = self._get_central()
            resp = await self._api_call(central, "GET", "/monitoring/v1/aps", limit=1)

            if resp.get("code") == 200 or "aps" in resp.get("msg", {}):
                return {
                    "ok": True,
                    "message": "Connected to Aruba Central successfully.",
                    "details": {"response_code": resp.get("code")},
                }
            else:
                return {
                    "ok": False,
                    "message": f"Unexpected response: {resp.get('code', 'unknown')}",
                    "details": resp,
                }
        except Exception as e:
            logger.error(f"Aruba Central connection test failed: {e}")
            return {"ok": False, "message": str(e), "details": None}

    async def fetch_networks(self) -> list[NetworkData]:
        results: list[NetworkData] = []
        try:
            central = self._get_central()

            # Fetch network groups and their VLAN/subnet configs
            resp = await self._api_call(
                central, "GET", "/configuration/v1/groups"
            )
            groups = resp.get("msg", {}).get("data", [])
            if isinstance(groups, list):
                for group in groups:
                    group_name = group if isinstance(group, str) else group.get("group", "")
                    # Try to fetch VLAN details for each group
                    try:
                        vlan_resp = await self._api_call(
                            central, "GET",
                            f"/configuration/v1/groups/{group_name}/vlans"
                        )
                        vlans = vlan_resp.get("msg", {}).get("data", [])
                        if isinstance(vlans, list):
                            for vlan in vlans:
                                subnet = vlan.get("ipaddress")
                                mask = vlan.get("netmask") or vlan.get("subnet_mask")
                                if subnet and mask:
                                    import ipaddress as ipmod
                                    try:
                                        network = ipmod.ip_network(
                                            f"{subnet}/{mask}", strict=False
                                        )
                                        results.append(NetworkData(
                                            cidr=str(network),
                                            name=vlan.get("name", f"Group:{group_name}"),
                                            vlan_id=vlan.get("id"),
                                            gateway=subnet,
                                            description=f"Aruba Central group: {group_name}",
                                            raw=vlan,
                                        ))
                                    except ValueError:
                                        continue
                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"Aruba Central fetch_networks failed: {e}")

        return results

    async def fetch_clients(self) -> list[ClientData]:
        results: list[ClientData] = []
        try:
            central = self._get_central()

            # Paginate through wireless clients
            offset = 0
            limit = 500
            while True:
                resp = await self._api_call(
                    central, "GET", "/monitoring/v1/clients/wireless",
                    offset=offset, limit=limit,
                )
                clients = resp.get("msg", {}).get("clients", [])
                if not isinstance(clients, list) or not clients:
                    break

                for c in clients:
                    ip = c.get("ip_address")
                    if not ip:
                        continue
                    results.append(ClientData(
                        ip_address=ip,
                        mac_address=c.get("macaddr"),
                        hostname=c.get("name") or c.get("hostname"),
                        os=c.get("os_type"),
                        vendor=c.get("manufacturer"),
                        device_type="wireless_client",
                        vlan_id=c.get("vlan"),
                        raw=c,
                    ))

                if len(clients) < limit:
                    break
                offset += limit

            # Also fetch wired clients
            offset = 0
            while True:
                resp = await self._api_call(
                    central, "GET", "/monitoring/v1/clients/wired",
                    offset=offset, limit=limit,
                )
                clients = resp.get("msg", {}).get("clients", [])
                if not isinstance(clients, list) or not clients:
                    break

                existing_ips = {r.ip_address for r in results}
                for c in clients:
                    ip = c.get("ip_address")
                    if not ip or ip in existing_ips:
                        continue
                    results.append(ClientData(
                        ip_address=ip,
                        mac_address=c.get("macaddr"),
                        hostname=c.get("name") or c.get("hostname"),
                        os=c.get("os_type"),
                        vendor=c.get("manufacturer"),
                        device_type="wired_client",
                        vlan_id=c.get("vlan"),
                        switch_port=c.get("interface_port"),
                        raw=c,
                    ))

                if len(clients) < limit:
                    break
                offset += limit

        except Exception as e:
            logger.error(f"Aruba Central fetch_clients failed: {e}")

        return results

    async def fetch_devices(self) -> list[DeviceData]:
        results: list[DeviceData] = []
        try:
            central = self._get_central()

            # Fetch APs
            resp = await self._api_call(
                central, "GET", "/monitoring/v1/aps", limit=1000
            )
            aps = resp.get("msg", {}).get("aps", [])
            if isinstance(aps, list):
                for ap in aps:
                    results.append(DeviceData(
                        ip_address=ap.get("ip_address"),
                        mac_address=ap.get("macaddr"),
                        name=ap.get("name"),
                        model=ap.get("model"),
                        serial=ap.get("serial"),
                        firmware=ap.get("firmware_version"),
                        device_type="wireless_ap",
                        raw=ap,
                    ))

            # Fetch switches
            resp = await self._api_call(
                central, "GET", "/monitoring/v1/switches", limit=1000
            )
            switches = resp.get("msg", {}).get("switches", [])
            if isinstance(switches, list):
                for sw in switches:
                    results.append(DeviceData(
                        ip_address=sw.get("ip_address"),
                        mac_address=sw.get("macaddr"),
                        name=sw.get("name"),
                        model=sw.get("model"),
                        serial=sw.get("serial"),
                        firmware=sw.get("firmware_version"),
                        device_type="switch",
                        raw=sw,
                    ))

            # Fetch gateways
            resp = await self._api_call(
                central, "GET", "/monitoring/v1/gateways", limit=1000
            )
            gateways = resp.get("msg", {}).get("gateways", [])
            if isinstance(gateways, list):
                for gw in gateways:
                    results.append(DeviceData(
                        ip_address=gw.get("ip_address"),
                        mac_address=gw.get("macaddr"),
                        name=gw.get("name"),
                        model=gw.get("model"),
                        serial=gw.get("serial"),
                        firmware=gw.get("firmware_version"),
                        device_type="gateway",
                        raw=gw,
                    ))

        except Exception as e:
            logger.error(f"Aruba Central fetch_devices failed: {e}")

        return results
