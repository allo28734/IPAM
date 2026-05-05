"""
Discovery utilities for network IPAM.

Contains functions to fingerprint IPs using Nmap and lookup MAC vendor data.
"""

import logging
import nmap
from mac_vendor_lookup import MacLookup, VendorNotFoundError

logger = logging.getLogger(__name__)

# Initialize the MAC lookup tool
mac_lookup = MacLookup()

def fingerprint_ip(ip: str) -> dict:
    """
    Run an Nmap OS detection scan on a single IP.
    
    Args:
        ip: The IP address to scan (e.g., "192.168.1.5").
        
    Returns:
        dict: A dictionary containing:
            - mac_address: The discovered MAC address (or None)
            - vendor: The hardware vendor string (or None)
            - os_guess: The best OS guess string (or None)
            - device_type: The generic device type (or None)
    """
    nm = nmap.PortScanner()
    result = {
        "mac_address": None,
        "vendor": None,
        "os_guess": None,
        "device_type": None
    }
    
    try:
        # Run OS detection and set timing template to T4
        # Note: OS detection requires root privileges. In this container, Celery runs as root.
        nm.scan(ip, arguments='-O -T4')
        
        if ip not in nm.all_hosts():
            return result
            
        host_data = nm[ip]
        
        # 1. MAC Address
        addresses = host_data.get('addresses', {})
        mac = addresses.get('mac')
        if mac:
            result["mac_address"] = mac
            
            # 2. Vendor
            vendor_dict = host_data.get('vendor', {})
            vendor = vendor_dict.get(mac)
            if vendor:
                result["vendor"] = vendor
            else:
                try:
                    result["vendor"] = mac_lookup.lookup(mac)
                except Exception:
                    pass
                
        # 3. OS Guess & 4. Device Type
        osmatch_list = host_data.get('osmatch', [])
        if osmatch_list:
            # Take the best match (Nmap orders them by accuracy)
            best_match = osmatch_list[0]
            result["os_guess"] = best_match.get('name')
            
            osclass_list = best_match.get('osclass', [])
            if osclass_list:
                result["device_type"] = osclass_list[0].get('type')
                
    except nmap.PortScannerError as e:
        logger.error(f"Nmap scan failed for {ip}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during fingerprinting {ip}: {e}")
        
    return result
