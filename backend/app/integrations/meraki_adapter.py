"""
Cisco Meraki Adapter.

Uses the official ``meraki`` Python SDK to pull organizations,
networks, VLANs, clients, and device inventory from the Meraki
Dashboard API.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.integrations.base_adapter import (
    BaseAdapter, NetworkData, ClientData, DeviceData,
)

logger = logging.getLogger(__name__)


class MerakiAdapter(BaseAdapter):
    """Cisco Meraki Dashboard API adapter."""

    VENDOR_ID = "meraki"
    VENDOR_NAME = "Cisco Meraki"
    VENDOR_DESCRIPTION = "Cloud-managed networking via the Meraki Dashboard API"
    REQUIRES_BASE_URL = False  # Meraki SDK handles the base URL
    SUPPORTS_API_KEY = True
    SUPPORTS_USERNAME_PASSWORD = False
    EXTRA_CONFIG_FIELDS = [
        {
            "key": "org_id",
            "label": "Organization ID",
            "type": "text",
            "required": False,
            "help": "If blank, the first org associated with the API key is used.",
        },
    ]

    # ── Internal helpers ───────────────────────────────────────

    def _get_dashboard(self):
        """Lazily import and create a Meraki DashboardAPI instance."""
        import meraki

        return meraki.DashboardAPI(
            api_key=self.api_key,
            suppress_logging=True,
            single_request_timeout=30,
            maximum_retries=2,
        )

    async def _resolve_org_id(self, dashboard) -> str:
        """Return the configured org_id or auto-detect the first one."""
        org_id = self.extra.get("org_id")
        if org_id:
            return str(org_id)

        orgs = await asyncio.to_thread(
            dashboard.organizations.getOrganizations
        )
        if not orgs:
            raise RuntimeError("No organizations found for this API key")
        return orgs[0]["id"]

    # ── Public interface ───────────────────────────────────────

    async def test_connection(self) -> dict:
        try:
            dashboard = self._get_dashboard()
            orgs = await asyncio.to_thread(
                dashboard.organizations.getOrganizations
            )
            org_names = [o.get("name", "?") for o in orgs]
            return {
                "ok": True,
                "message": f"Connected successfully. Found {len(orgs)} organization(s).",
                "details": {"organizations": org_names},
            }
        except Exception as e:
            logger.error(f"Meraki connection test failed: {e}")
            return {"ok": False, "message": str(e), "details": None}

    async def fetch_networks(self) -> list[NetworkData]:
        results: list[NetworkData] = []
        try:
            dashboard = self._get_dashboard()
            org_id = await self._resolve_org_id(dashboard)

            networks = await asyncio.to_thread(
                dashboard.organizations.getOrganizationNetworks, org_id
            )

            for net in networks:
                network_id = net["id"]
                try:
                    vlans = await asyncio.to_thread(
                        dashboard.appliance.getNetworkApplianceVlans, network_id
                    )
                except Exception:
                    # Network may not have an MX appliance
                    continue

                for vlan in vlans:
                    subnet = vlan.get("subnet")
                    mask = vlan.get("maskLen") or vlan.get("cidr", "").split("/")[-1]
                    if subnet and mask:
                        cidr = f"{subnet}/{mask}" if "/" not in subnet else subnet
                    elif vlan.get("cidr"):
                        cidr = vlan["cidr"]
                    else:
                        continue

                    results.append(NetworkData(
                        cidr=cidr,
                        name=vlan.get("name") or net.get("name"),
                        vlan_id=vlan.get("id"),
                        gateway=vlan.get("applianceIp"),
                        description=f"Meraki network: {net.get('name', '')}",
                        raw=vlan,
                    ))
        except Exception as e:
            logger.error(f"Meraki fetch_networks failed: {e}")

        return results

    async def fetch_clients(self) -> list[ClientData]:
        results: list[ClientData] = []
        try:
            dashboard = self._get_dashboard()
            org_id = await self._resolve_org_id(dashboard)

            networks = await asyncio.to_thread(
                dashboard.organizations.getOrganizationNetworks, org_id
            )

            for net in networks:
                try:
                    clients = await asyncio.to_thread(
                        dashboard.networks.getNetworkClients,
                        net["id"],
                        timespan=86400,  # last 24 hours
                        perPage=1000,
                        total_pages="all",
                    )
                except Exception:
                    continue

                for c in clients:
                    ip = c.get("ip")
                    if not ip:
                        continue
                    results.append(ClientData(
                        ip_address=ip,
                        mac_address=c.get("mac"),
                        hostname=c.get("description") or c.get("dhcpHostname"),
                        os=c.get("os"),
                        vendor=c.get("manufacturer"),
                        vlan_id=c.get("vlan"),
                        switch_port=c.get("switchport"),
                        last_seen=c.get("lastSeen"),
                        raw=c,
                    ))
        except Exception as e:
            logger.error(f"Meraki fetch_clients failed: {e}")

        return results

    async def fetch_devices(self) -> list[DeviceData]:
        results: list[DeviceData] = []
        try:
            dashboard = self._get_dashboard()
            org_id = await self._resolve_org_id(dashboard)

            devices = await asyncio.to_thread(
                dashboard.organizations.getOrganizationDevices,
                org_id,
                total_pages="all",
            )

            for d in devices:
                results.append(DeviceData(
                    ip_address=d.get("lanIp") or d.get("wan1Ip"),
                    mac_address=d.get("mac"),
                    name=d.get("name") or d.get("serial"),
                    model=d.get("model"),
                    serial=d.get("serial"),
                    firmware=d.get("firmware"),
                    device_type=self._guess_device_type(d.get("model", "")),
                    raw=d,
                ))
        except Exception as e:
            logger.error(f"Meraki fetch_devices failed: {e}")

        return results

    @staticmethod
    def _guess_device_type(model: str) -> str:
        model_lower = model.lower()
        if model_lower.startswith("mr") or "wireless" in model_lower:
            return "wireless_ap"
        elif model_lower.startswith("ms") or "switch" in model_lower:
            return "switch"
        elif model_lower.startswith("mx") or "appliance" in model_lower:
            return "security_appliance"
        elif model_lower.startswith("mv") or "camera" in model_lower:
            return "camera"
        return "network_device"
