"""
Tests for ip_utils — Pure utility functions.

These tests verify CIDR validation, overlap detection,
next-available-IP computation, and utilization calculations.
Since these are pure functions with no side effects, no database
fixture is needed.
"""

import pytest

from app.utils.ip_utils import (
    calculate_utilization,
    find_overlapping_cidrs,
    get_subnet_capacity,
    get_usable_host_range,
    is_ip_in_subnet,
    next_available_ip,
    subnets_overlap,
    validate_cidr,
    validate_ip_address,
)


class TestValidateCidr:
    """Tests for CIDR validation."""

    def test_valid_cidr(self):
        net = validate_cidr("10.0.1.0/24")
        assert str(net) == "10.0.1.0/24"

    def test_valid_cidr_slash_16(self):
        net = validate_cidr("172.16.0.0/16")
        assert str(net) == "172.16.0.0/16"

    def test_valid_cidr_slash_32(self):
        net = validate_cidr("10.0.1.1/32")
        assert str(net) == "10.0.1.1/32"

    def test_invalid_cidr_host_bits_set(self):
        """strict=True rejects CIDRs with host bits set."""
        with pytest.raises(ValueError, match="Invalid CIDR"):
            validate_cidr("10.0.1.5/24")

    def test_invalid_cidr_garbage(self):
        with pytest.raises(ValueError, match="Invalid CIDR"):
            validate_cidr("not-a-cidr")

    def test_invalid_cidr_empty(self):
        with pytest.raises(ValueError):
            validate_cidr("")

    def test_invalid_cidr_ipv6(self):
        """IPv6 must be rejected in our IPv4-only MVP."""
        with pytest.raises(ValueError):
            validate_cidr("2001:db8::/32")


class TestValidateIpAddress:
    """Tests for IP address validation."""

    def test_valid_ip(self):
        addr = validate_ip_address("10.0.1.42")
        assert str(addr) == "10.0.1.42"

    def test_invalid_ip(self):
        with pytest.raises(ValueError, match="Invalid IPv4"):
            validate_ip_address("999.999.999.999")

    def test_invalid_ip_string(self):
        with pytest.raises(ValueError):
            validate_ip_address("not-an-ip")


class TestIsIpInSubnet:
    """Tests for IP-in-subnet membership check."""

    def test_ip_in_subnet(self):
        assert is_ip_in_subnet("10.0.1.42", "10.0.1.0/24") is True

    def test_ip_not_in_subnet(self):
        assert is_ip_in_subnet("10.0.2.1", "10.0.1.0/24") is False

    def test_network_address(self):
        assert is_ip_in_subnet("10.0.1.0", "10.0.1.0/24") is True

    def test_broadcast_address(self):
        assert is_ip_in_subnet("10.0.1.255", "10.0.1.0/24") is True


class TestSubnetsOverlap:
    """Tests for subnet overlap detection."""

    def test_identical_subnets(self):
        assert subnets_overlap("10.0.1.0/24", "10.0.1.0/24") is True

    def test_supernet_overlaps_subnet(self):
        assert subnets_overlap("10.0.0.0/16", "10.0.1.0/24") is True

    def test_subnet_overlaps_supernet(self):
        assert subnets_overlap("10.0.1.0/24", "10.0.0.0/16") is True

    def test_adjacent_subnets_no_overlap(self):
        assert subnets_overlap("10.0.1.0/24", "10.0.2.0/24") is False

    def test_completely_disjoint(self):
        assert subnets_overlap("10.0.0.0/8", "192.168.0.0/16") is False

    def test_partial_overlap(self):
        """A /23 overlaps with the second /24 within its range."""
        assert subnets_overlap("10.0.0.0/23", "10.0.1.0/24") is True


class TestFindOverlappingCidrs:
    """Tests for finding overlaps against a list of existing CIDRs."""

    def test_no_overlaps(self):
        existing = ["10.0.1.0/24", "10.0.2.0/24"]
        assert find_overlapping_cidrs("192.168.1.0/24", existing) == []

    def test_one_overlap(self):
        existing = ["10.0.1.0/24", "192.168.1.0/24"]
        result = find_overlapping_cidrs("10.0.0.0/16", existing)
        assert result == ["10.0.1.0/24"]

    def test_multiple_overlaps(self):
        existing = ["10.0.1.0/24", "10.0.2.0/24", "192.168.1.0/24"]
        result = find_overlapping_cidrs("10.0.0.0/16", existing)
        assert set(result) == {"10.0.1.0/24", "10.0.2.0/24"}

    def test_empty_existing(self):
        assert find_overlapping_cidrs("10.0.1.0/24", []) == []


class TestGetUsableHostRange:
    """Tests for usable host range computation."""

    def test_slash_24(self):
        first, last, count = get_usable_host_range("10.0.1.0/24")
        assert first == "10.0.1.1"
        assert last == "10.0.1.254"
        assert count == 254

    def test_slash_30(self):
        """A /30 has 2 usable hosts (common for point-to-point links)."""
        first, last, count = get_usable_host_range("10.0.1.0/30")
        assert first == "10.0.1.1"
        assert last == "10.0.1.2"
        assert count == 2

    def test_slash_32(self):
        """A /32 is a single host."""
        first, last, count = get_usable_host_range("10.0.1.1/32")
        assert first == "10.0.1.1"
        assert last == "10.0.1.1"
        assert count == 1


class TestNextAvailableIp:
    """Tests for next-available-IP allocation logic."""

    def test_first_ip_in_empty_subnet(self):
        result = next_available_ip("10.0.1.0/24", [])
        assert result == "10.0.1.1"

    def test_skips_used_addresses(self):
        used = ["10.0.1.1", "10.0.1.2"]
        result = next_available_ip("10.0.1.0/24", used)
        assert result == "10.0.1.3"

    def test_skips_gateway(self):
        result = next_available_ip("10.0.1.0/24", [], gateway="10.0.1.1")
        assert result == "10.0.1.2"

    def test_skips_used_and_gateway(self):
        used = ["10.0.1.2"]
        result = next_available_ip("10.0.1.0/24", used, gateway="10.0.1.1")
        assert result == "10.0.1.3"

    def test_full_subnet_returns_none(self):
        """When all addresses are used, returns None."""
        used = [f"10.0.1.{i}" for i in range(1, 255)]  # .1-.254
        result = next_available_ip("10.0.1.0/24", used)
        assert result is None


class TestGetSubnetCapacity:
    """Tests for subnet capacity calculation."""

    def test_slash_24(self):
        assert get_subnet_capacity("10.0.1.0/24") == 254

    def test_slash_16(self):
        assert get_subnet_capacity("172.16.0.0/16") == 65534

    def test_slash_30(self):
        assert get_subnet_capacity("10.0.1.0/30") == 2

    def test_slash_32(self):
        assert get_subnet_capacity("10.0.1.1/32") == 1


class TestCalculateUtilization:
    """Tests for utilization percentage calculation."""

    def test_zero_utilization(self):
        assert calculate_utilization(0, "10.0.1.0/24") == 0.0

    def test_full_utilization(self):
        assert calculate_utilization(254, "10.0.1.0/24") == 100.0

    def test_partial_utilization(self):
        result = calculate_utilization(127, "10.0.1.0/24")
        assert result == 50.0

    def test_one_address_in_slash_30(self):
        result = calculate_utilization(1, "10.0.1.0/30")
        assert result == 50.0
