import pytest
from unittest.mock import patch, MagicMock
from app.utils.discovery_utils import fingerprint_ip

@patch('app.utils.discovery_utils.mac_lookup.lookup')
@patch('app.utils.discovery_utils.nmap.PortScanner')
def test_fingerprint_ip_success(mock_portscanner, mock_lookup):
    mock_nm = MagicMock()
    mock_portscanner.return_value = mock_nm
    mock_nm.all_hosts.return_value = ['192.168.1.5']
    
    # Mock the dictionary return for nm[ip]
    mock_nm.__getitem__.return_value = {
        'addresses': {'mac': '00:1A:2B:3C:4D:5E'},
        'vendor': {'00:1A:2B:3C:4D:5E': 'Test Vendor Inc.'},
        'osmatch': [
            {
                'name': 'Linux 5.4',
                'osclass': [{'type': 'general purpose'}]
            }
        ]
    }
    
    result = fingerprint_ip('192.168.1.5')
    
    mock_nm.scan.assert_called_once_with('192.168.1.5', arguments='-O -T4')
    
    assert result['mac_address'] == '00:1A:2B:3C:4D:5E'
    assert result['vendor'] == 'Test Vendor Inc.'
    assert result['os_guess'] == 'Linux 5.4'
    assert result['device_type'] == 'general purpose'
    mock_lookup.assert_not_called()

@patch('app.utils.discovery_utils.mac_lookup.lookup')
@patch('app.utils.discovery_utils.nmap.PortScanner')
def test_fingerprint_ip_fallback_vendor(mock_portscanner, mock_lookup):
    mock_nm = MagicMock()
    mock_portscanner.return_value = mock_nm
    mock_nm.all_hosts.return_value = ['192.168.1.6']
    mock_nm.__getitem__.return_value = {
        'addresses': {'mac': 'AA:BB:CC:DD:EE:FF'},
    }
    mock_lookup.return_value = "Fallback Vendor"
    
    result = fingerprint_ip('192.168.1.6')
    
    assert result['mac_address'] == 'AA:BB:CC:DD:EE:FF'
    assert result['vendor'] == 'Fallback Vendor'
    assert result['os_guess'] is None
    assert result['device_type'] is None
    mock_lookup.assert_called_once_with('AA:BB:CC:DD:EE:FF')

@patch('app.utils.discovery_utils.nmap.PortScanner')
def test_fingerprint_ip_host_down(mock_portscanner):
    mock_nm = MagicMock()
    mock_portscanner.return_value = mock_nm
    mock_nm.all_hosts.return_value = []  # Host down / no response
    
    result = fingerprint_ip('192.168.1.7')
    
    assert result['mac_address'] is None
    assert result['vendor'] is None
    assert result['os_guess'] is None
    assert result['device_type'] is None
