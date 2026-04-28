"""
Pure IP/CIDR utility functions.

These are stateless, side-effect-free helpers that operate on
Python's built-in ipaddress module. They are used by the service
layer but have NO dependency on the database, ORM, or HTTP layer.

All functions in this module are easily unit-testable in isolation.
"""

import ipaddress
from typing import Optional


def validate_cidr(cidr: str) -> ipaddress.IPv4Network:
    """
    Parse and validate a CIDR string (e.g. '10.0.1.0/24').

    Returns the normalized IPv4Network object on success.
    Raises ValueError with a descriptive message on failure.
    """
    try:
        network = ipaddress.IPv4Network(cidr, strict=True)
    except ValueError as exc:
        raise ValueError(f"Invalid CIDR notation '{cidr}': {exc}") from exc

    return network


def validate_ip_address(address: str) -> ipaddress.IPv4Address:
    """
    Parse and validate an IPv4 address string.

    Raises ValueError if the string is not a valid IPv4 address.
    """
    try:
        return ipaddress.IPv4Address(address)
    except ValueError as exc:
        raise ValueError(f"Invalid IPv4 address '{address}': {exc}") from exc


def is_ip_in_subnet(address: str, cidr: str) -> bool:
    """Check whether an IP address belongs to a given CIDR subnet."""
    ip = ipaddress.IPv4Address(address)
    network = ipaddress.IPv4Network(cidr, strict=False)
    return ip in network


def subnets_overlap(cidr_a: str, cidr_b: str) -> bool:
    """
    Determine whether two CIDR subnets overlap.

    Two subnets overlap if any IP address is contained in both.
    """
    net_a = ipaddress.IPv4Network(cidr_a, strict=False)
    net_b = ipaddress.IPv4Network(cidr_b, strict=False)
    return net_a.overlaps(net_b)


def find_overlapping_cidrs(new_cidr: str, existing_cidrs: list[str]) -> list[str]:
    """
    Given a new CIDR, return all existing CIDRs that overlap with it.

    Returns an empty list if there are no overlaps.
    """
    overlaps = []
    new_net = ipaddress.IPv4Network(new_cidr, strict=False)
    for cidr in existing_cidrs:
        existing_net = ipaddress.IPv4Network(cidr, strict=False)
        if new_net.overlaps(existing_net):
            overlaps.append(cidr)
    return overlaps


def get_usable_host_range(cidr: str) -> tuple[str, str, int]:
    """
    Compute the usable host range for a subnet.

    Returns (first_usable_ip, last_usable_ip, total_usable_count).
    For /31 and /32 subnets, special RFC rules apply.
    """
    network = ipaddress.IPv4Network(cidr, strict=False)
    hosts = list(network.hosts())

    if not hosts:
        # /32 — single host
        addr = str(network.network_address)
        return (addr, addr, 1)

    return (str(hosts[0]), str(hosts[-1]), len(hosts))


def next_available_ip(
    cidr: str,
    used_addresses: list[str],
    gateway: Optional[str] = None,
) -> Optional[str]:
    """
    Find the next available IP address in a subnet.

    Iterates through usable host addresses and returns the first one
    that is not in the used_addresses set and is not the gateway.
    Returns None if the subnet is fully utilized.
    """
    network = ipaddress.IPv4Network(cidr, strict=False)
    used_set = set(used_addresses)

    if gateway:
        used_set.add(gateway)

    for host in network.hosts():
        addr = str(host)
        if addr not in used_set:
            return addr

    return None


def get_subnet_capacity(cidr: str) -> int:
    """
    Return the total number of usable host addresses in a subnet.

    Excludes network and broadcast addresses (except for /31 and /32).
    """
    network = ipaddress.IPv4Network(cidr, strict=False)
    hosts = list(network.hosts())
    return len(hosts) if hosts else 1


def calculate_utilization(used_count: int, cidr: str) -> float:
    """
    Calculate subnet utilization as a percentage.

    Returns a float between 0.0 and 100.0.
    """
    capacity = get_subnet_capacity(cidr)
    if capacity == 0:
        return 0.0
    return round((used_count / capacity) * 100, 2)
