"""
Pure IP/CIDR utility functions.

These are stateless, side-effect-free helpers that operate on
Python's built-in ipaddress module. They are used by the service
layer but have NO dependency on the database, ORM, or HTTP layer.

All functions in this module are easily unit-testable in isolation.
"""

import ipaddress
from typing import Optional, Union


def validate_cidr(cidr: str) -> Union[ipaddress.IPv4Network, ipaddress.IPv6Network]:
    """
    Parse and validate a CIDR string (e.g. '10.0.1.0/24' or '2001:db8::/32').

    Returns the normalized IPv4Network or IPv6Network object on success.
    Raises ValueError with a descriptive message on failure.
    """
    try:
        network = ipaddress.ip_network(cidr, strict=True)
    except ValueError as exc:
        raise ValueError(f"Invalid CIDR notation '{cidr}': {exc}") from exc

    return network


def validate_ip_address(address: str) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    """
    Parse and validate an IPv4 or IPv6 address string.

    Raises ValueError if the string is not a valid IP address.
    """
    try:
        return ipaddress.ip_address(address)
    except ValueError as exc:
        raise ValueError(f"Invalid IP address '{address}': {exc}") from exc


def is_ip_in_subnet(address: str, cidr: str) -> bool:
    """Check whether an IP address belongs to a given CIDR subnet."""
    try:
        ip = ipaddress.ip_address(address)
        network = ipaddress.ip_network(cidr, strict=False)
        if ip.version != network.version:
            return False
        return ip in network
    except ValueError:
        return False


def subnets_overlap(cidr_a: str, cidr_b: str) -> bool:
    """
    Determine whether two CIDR subnets overlap.

    Two subnets overlap if any IP address is contained in both.
    """
    try:
        net_a = ipaddress.ip_network(cidr_a, strict=False)
        net_b = ipaddress.ip_network(cidr_b, strict=False)
        if net_a.version != net_b.version:
            return False
        return net_a.overlaps(net_b)
    except ValueError:
        return False


def is_subnet_of(child_cidr: str, parent_cidr: str) -> bool:
    """
    Determine whether child_cidr is strictly a subnet of parent_cidr.
    """
    try:
        child_net = ipaddress.ip_network(child_cidr, strict=False)
        parent_net = ipaddress.ip_network(parent_cidr, strict=False)
        if child_net.version != parent_net.version:
            return False
        return child_net.subnet_of(parent_net)
    except ValueError:
        return False


def find_overlapping_cidrs(new_cidr: str, existing_cidrs: list[str]) -> list[str]:
    """
    Given a new CIDR, return all existing CIDRs that overlap with it.

    Returns an empty list if there are no overlaps.
    """
    overlaps = []
    new_net = ipaddress.ip_network(new_cidr, strict=False)
    for cidr in existing_cidrs:
        existing_net = ipaddress.ip_network(cidr, strict=False)
        if new_net.version == existing_net.version and new_net.overlaps(existing_net):
            overlaps.append(cidr)
    return overlaps


def get_usable_host_range(cidr: str) -> tuple[str, str, int]:
    """
    Compute the usable host range for a subnet without expanding it in memory.

    Returns (first_usable_ip, last_usable_ip, total_usable_count).
    """
    network = ipaddress.ip_network(cidr, strict=False)
    
    if network.version == 4:
        if network.prefixlen == 32:
            addr = str(network.network_address)
            return (addr, addr, 1)
        elif network.prefixlen == 31:
            return (str(network[0]), str(network[1]), 2)
        else:
            return (str(network[1]), str(network[-2]), network.num_addresses - 2)
    else:
        # IPv6
        if network.prefixlen == 128:
            addr = str(network.network_address)
            return (addr, addr, 1)
        else:
            # First is Subnet-Router anycast (usually skipped for hosts) -> network[1]
            # Last is network[-1]
            return (str(network[1]), str(network[-1]), network.num_addresses - 1)


def next_available_ip(
    cidr: str,
    used_addresses: list[str],
    gateway: Optional[str] = None,
) -> Optional[str]:
    """
    Find the next available IP address in a subnet efficiently.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    used_set = set(used_addresses)

    if gateway:
        used_set.add(gateway)

    # Convert used IPs back to ipaddress objects for exact string matching/integer conversion
    # However, just iterating over integers and casting to IP is faster
    used_ints = {int(ipaddress.ip_address(ip)) for ip in used_set if ipaddress.ip_address(ip).version == network.version}
    
    if network.version == 4:
        if network.prefixlen == 32:
            start_int = int(network.network_address)
            end_int = int(network.network_address)
        elif network.prefixlen == 31:
            start_int = int(network.network_address)
            end_int = int(network.network_address) + 1
        else:
            start_int = int(network.network_address) + 1
            end_int = int(network.broadcast_address) - 1
    else:
        if network.prefixlen == 128:
            start_int = int(network.network_address)
            end_int = int(network.network_address)
        else:
            start_int = int(network.network_address) + 1
            end_int = int(network.network_address) + network.num_addresses - 1
            
    # Iterate mathematically without creating a massive list in memory
    curr = start_int
    while curr <= end_int:
        if curr not in used_ints:
            return str(ipaddress.ip_address(curr))
        curr += 1
        
    return None


def get_subnet_capacity(cidr: str) -> int:
    """
    Return the total number of usable host addresses in a subnet.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    if network.version == 4:
        if network.prefixlen >= 31:
            return network.num_addresses
        return network.num_addresses - 2
    else:
        if network.prefixlen == 128:
            return 1
        return network.num_addresses - 1


def calculate_utilization(used_count: int, cidr: str) -> float:
    """
    Calculate subnet utilization as a percentage.
    """
    capacity = get_subnet_capacity(cidr)
    if capacity == 0:
        return 0.0
    return round((used_count / capacity) * 100, 2)
