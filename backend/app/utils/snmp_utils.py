"""
SNMP Utilities for Deep Discovery.

Provides functions for securely polling SNMPv3 agents.
"""

import logging
from pysnmp.hlapi import (
    SnmpEngine, UsmUserData, usmHMACMD5AuthProtocol, usmHMACSHAAuthProtocol,
    usmDESPrivProtocol, usm3DESEDEPrivProtocol, usmAesCfb128Protocol,
    usmAesCfb192Protocol, usmAesCfb256Protocol, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity, getCmd,
    usmHMAC128SHA224AuthProtocol, usmHMAC192SHA256AuthProtocol,
    usmHMAC256SHA384AuthProtocol, usmHMAC384SHA512AuthProtocol
)

logger = logging.getLogger(__name__)

# Map string protocols to pysnmp constants
AUTH_PROTOCOLS = {
    "MD5": usmHMACMD5AuthProtocol,
    "SHA": usmHMACSHAAuthProtocol,
    "SHA224": usmHMAC128SHA224AuthProtocol,
    "SHA256": usmHMAC192SHA256AuthProtocol,
    "SHA384": usmHMAC256SHA384AuthProtocol,
    "SHA512": usmHMAC384SHA512AuthProtocol,
}

PRIV_PROTOCOLS = {
    "DES": usmDESPrivProtocol,
    "3DES": usm3DESEDEPrivProtocol,
    "AES": usmAesCfb128Protocol,
    "AES192": usmAesCfb192Protocol,
    "AES256": usmAesCfb256Protocol,
}

def poll_snmpv3(ip: str, credentials: dict, timeout: int = 2, retries: int = 1) -> dict:
    """
    Poll an IP using SNMPv3.
    
    Returns a dictionary with keys matching discovery fields:
    hostname, os_guess, vendor, device_type
    """
    result = {
        "hostname": None,
        "os_guess": None,
        "vendor": None,
        "device_type": None
    }
    
    username = credentials.get("username")
    if not username:
        return result
        
    auth_protocol = AUTH_PROTOCOLS.get(credentials.get("auth_protocol", ""), usmHMACSHAAuthProtocol)
    auth_password = credentials.get("auth_password")
    
    priv_protocol = PRIV_PROTOCOLS.get(credentials.get("priv_protocol", ""), usmAesCfb128Protocol)
    priv_password = credentials.get("priv_password")
    
    # Construct user data
    if priv_password:
        user_data = UsmUserData(
            username,
            authKey=auth_password,
            privKey=priv_password,
            authProtocol=auth_protocol,
            privProtocol=priv_protocol
        )
    elif auth_password:
        user_data = UsmUserData(
            username,
            authKey=auth_password,
            authProtocol=auth_protocol
        )
    else:
        user_data = UsmUserData(username)

    try:
        # sysName.0 and sysDescr.0
        iterator = getCmd(
            SnmpEngine(),
            user_data,
            UdpTransportTarget((ip, 161), timeout=timeout, retries=retries),
            ContextData(),
            ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysName', 0)),
            ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            logger.debug(f"SNMP error on {ip}: {errorIndication}")
            return result
        elif errorStatus:
            logger.debug(f"SNMP status error on {ip}: {errorStatus.prettyPrint()}")
            return result
        else:
            for varBind in varBinds:
                oid = varBind[0].prettyPrint()
                val = varBind[1].prettyPrint()
                
                if 'sysName' in oid and val:
                    result['hostname'] = val
                elif 'sysDescr' in oid and val:
                    # Very rough heuristic to extract OS, vendor, device type
                    # sysDescr is freeform, e.g. "Cisco IOS Software, C2960X Software..."
                    result['os_guess'] = val[:255]  # limit to DB size
                    
                    val_lower = val.lower()
                    if "cisco" in val_lower:
                        result['vendor'] = "Cisco"
                        if "ios" in val_lower or "nx-os" in val_lower:
                            result['device_type'] = "switch/router"
                    elif "linux" in val_lower:
                        result['vendor'] = "Linux"
                        result['device_type'] = "general purpose"
                    elif "windows" in val_lower:
                        result['vendor'] = "Microsoft"
                        result['device_type'] = "general purpose"
                    
    except Exception as e:
        logger.error(f"Failed to poll SNMPv3 for {ip}: {e}")

    # If any field has a value, we consider it a success
    return result
