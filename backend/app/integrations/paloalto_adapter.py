"""
Palo Alto Networks PAN-OS Adapter.

Communicates with the PAN-OS XML/REST API to retrieve interface
configurations, DHCP leases, ARP tables, and system information
from Palo Alto Networks firewalls and Panorama.
"""

from __future__ import annotations

import asyncio
import ipaddress as ipmod
import logging
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

from app.integrations.base_adapter import (
    BaseAdapter, NetworkData, ClientData, DeviceData,
)

logger = logging.getLogger(__name__)


class PaloAltoAdapter(BaseAdapter):
    """Palo Alto Networks PAN-OS API adapter."""

    VENDOR_ID = "paloalto"
    VENDOR_NAME = "Palo Alto Networks"
    VENDOR_DESCRIPTION = "PAN-OS firewalls and Panorama via the XML/REST API"
    REQUIRES_BASE_URL = True
    SUPPORTS_API_KEY = True
    SUPPORTS_USERNAME_PASSWORD = True
    EXTRA_CONFIG_FIELDS = [
        {
            "key": "vsys",
            "label": "Virtual System",
            "type": "text",
            "required": False,
            "help": "Virtual system name. Defaults to 'vsys1'.",
        },
        {
            "key": "verify_ssl",
            "label": "Verify SSL Certificate",
            "type": "boolean",
            "required": False,
            "help": "Set to false for self-signed certificates.",
        },
    ]

    # ── Internal helpers ───────────────────────────────────────

    def _build_client(self) -> httpx.AsyncClient:
        base = self.provider.base_url.rstrip("/")
        verify = self.extra.get("verify_ssl", False)
        return httpx.AsyncClient(
            base_url=base,
            verify=verify,
            timeout=30.0,
        )

    async def _get_api_key(self, client: httpx.AsyncClient) -> str:
        """
        Return the stored API key, or generate one from username/password
        via the PAN-OS keygen endpoint.
        """
        key = self.api_key
        if key:
            return key

        username = self.provider.username
        password = self.password
        if not username or not password:
            raise RuntimeError(
                "Palo Alto requires either an API key or username/password"
            )

        resp = await client.get(
            "/api/",
            params={
                "type": "keygen",
                "user": username,
                "password": password,
            },
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        key_elem = root.find(".//key")
        if key_elem is None or not key_elem.text:
            raise RuntimeError("Failed to generate PAN-OS API key")
        return key_elem.text

    async def _op_command(
        self, client: httpx.AsyncClient, key: str, cmd_xml: str
    ) -> ET.Element:
        """Execute a PAN-OS operational command and return the XML root."""
        resp = await client.get(
            "/api/",
            params={"type": "op", "cmd": cmd_xml, "key": key},
        )
        resp.raise_for_status()
        return ET.fromstring(resp.text)

    async def _config_get(
        self, client: httpx.AsyncClient, key: str, xpath: str
    ) -> ET.Element:
        """Execute a PAN-OS config GET and return the XML root."""
        resp = await client.get(
            "/api/",
            params={"type": "config", "action": "get", "xpath": xpath, "key": key},
        )
        resp.raise_for_status()
        return ET.fromstring(resp.text)

    @property
    def _vsys(self) -> str:
        return self.extra.get("vsys", "vsys1")

    # ── Public interface ───────────────────────────────────────

    async def test_connection(self) -> dict:
        try:
            async with self._build_client() as client:
                key = await self._get_api_key(client)
                root = await self._op_command(
                    client, key,
                    "<show><system><info></info></system></show>"
                )
                hostname = "unknown"
                hn_elem = root.find(".//hostname")
                if hn_elem is not None and hn_elem.text:
                    hostname = hn_elem.text

                model = "unknown"
                model_elem = root.find(".//model")
                if model_elem is not None and model_elem.text:
                    model = model_elem.text

                return {
                    "ok": True,
                    "message": f"Connected to PAN-OS: {hostname} ({model})",
                    "details": {"hostname": hostname, "model": model},
                }
        except Exception as e:
            logger.error(f"Palo Alto connection test failed: {e}")
            return {"ok": False, "message": str(e), "details": None}

    async def fetch_networks(self) -> list[NetworkData]:
        results: list[NetworkData] = []
        try:
            async with self._build_client() as client:
                key = await self._get_api_key(client)

                # Get interface configuration via config API
                xpath = (
                    f"/config/devices/entry[@name='localhost.localdomain']"
                    f"/network/interface"
                )
                root = await self._config_get(client, key, xpath)

                # Parse ethernet interfaces
                for iface in root.iter("entry"):
                    iface_name = iface.get("name", "")
                    # Look for layer3 IP addresses
                    for ip_elem in iface.iter("ip"):
                        for entry in ip_elem.findall("entry"):
                            cidr = entry.get("name")
                            if not cidr or "/" not in cidr:
                                continue
                            try:
                                network = ipmod.ip_network(cidr, strict=False)
                                gateway_ip = cidr.split("/")[0]
                                results.append(NetworkData(
                                    cidr=str(network),
                                    name=iface_name,
                                    gateway=gateway_ip,
                                    description=f"PAN-OS interface: {iface_name}",
                                    raw={"interface": iface_name, "cidr": cidr},
                                ))
                            except ValueError:
                                continue

                # Try to get DHCP server info
                try:
                    dhcp_root = await self._op_command(
                        client, key,
                        "<show><dhcp><server><lease><all></all></lease></server></dhcp></show>"
                    )
                    for entry in dhcp_root.iter("entry"):
                        ip_elem = entry.find("ip")
                        iface_elem = entry.find("interface")
                        if ip_elem is not None and ip_elem.text and iface_elem is not None:
                            # Annotate matching networks with DHCP info
                            for net in results:
                                try:
                                    if (ipmod.ip_address(ip_elem.text) in
                                            ipmod.ip_network(net.cidr, strict=False)):
                                        if "DHCP" not in (net.description or ""):
                                            net.description = f"{net.description} | DHCP active"
                                        break
                                except ValueError:
                                    pass
                except Exception:
                    pass  # DHCP may not be configured

        except Exception as e:
            logger.error(f"Palo Alto fetch_networks failed: {e}")

        return results

    async def fetch_clients(self) -> list[ClientData]:
        results: list[ClientData] = []
        try:
            async with self._build_client() as client:
                key = await self._get_api_key(client)

                # Get ARP table for connected hosts
                root = await self._op_command(
                    client, key,
                    "<show><arp><entry name = 'all'/></arp></show>"
                )

                for entry in root.iter("entry"):
                    ip_elem = entry.find("ip")
                    mac_elem = entry.find("mac")
                    iface_elem = entry.find("interface")

                    ip = ip_elem.text if ip_elem is not None else None
                    if not ip:
                        continue

                    results.append(ClientData(
                        ip_address=ip,
                        mac_address=mac_elem.text if mac_elem is not None else None,
                        switch_port=iface_elem.text if iface_elem is not None else None,
                        raw={
                            "ip": ip,
                            "mac": mac_elem.text if mac_elem is not None else None,
                            "interface": iface_elem.text if iface_elem is not None else None,
                        },
                    ))

                # Try DHCP leases for richer hostname data
                try:
                    dhcp_root = await self._op_command(
                        client, key,
                        "<show><dhcp><server><lease><all></all></lease></server></dhcp></show>"
                    )
                    lease_map = {}
                    for entry in dhcp_root.iter("entry"):
                        ip_elem = entry.find("ip")
                        hostname_elem = entry.find("hostname")
                        mac_elem = entry.find("mac")
                        if ip_elem is not None and ip_elem.text:
                            lease_map[ip_elem.text] = {
                                "hostname": hostname_elem.text if hostname_elem is not None else None,
                                "mac": mac_elem.text if mac_elem is not None else None,
                            }

                    # Enrich ARP results with DHCP data
                    for c in results:
                        if c.ip_address in lease_map:
                            lease = lease_map[c.ip_address]
                            if not c.hostname and lease.get("hostname"):
                                c.hostname = lease["hostname"]
                            if not c.mac_address and lease.get("mac"):
                                c.mac_address = lease["mac"]

                except Exception:
                    pass  # DHCP may not be configured

        except Exception as e:
            logger.error(f"Palo Alto fetch_clients failed: {e}")

        return results

    async def fetch_devices(self) -> list[DeviceData]:
        results: list[DeviceData] = []
        try:
            async with self._build_client() as client:
                key = await self._get_api_key(client)

                root = await self._op_command(
                    client, key,
                    "<show><system><info></info></system></show>"
                )

                info = {}
                for child in root.iter():
                    if child.text and child.text.strip():
                        info[child.tag] = child.text.strip()

                results.append(DeviceData(
                    ip_address=info.get("ip-address"),
                    mac_address=info.get("mac-address"),
                    name=info.get("hostname", "PAN-OS"),
                    model=info.get("model"),
                    serial=info.get("serial"),
                    firmware=info.get("sw-version"),
                    device_type="firewall",
                    raw=info,
                ))

                # Get interface operational status for additional IPs
                try:
                    if_root = await self._op_command(
                        client, key,
                        "<show><interface>all</interface></show>"
                    )
                    for iface in if_root.iter("ifnet"):
                        name_elem = iface.find("name")
                        ip_elem = iface.find("ip")
                        if (ip_elem is not None and ip_elem.text and
                                ip_elem.text != "N/A" and
                                name_elem is not None):
                            results.append(DeviceData(
                                ip_address=ip_elem.text.split("/")[0],
                                name=f"PAN-OS:{name_elem.text}",
                                device_type="firewall_interface",
                                raw={"interface": name_elem.text},
                            ))
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Palo Alto fetch_devices failed: {e}")

        return results
