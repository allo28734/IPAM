"""
Ping utilities for network sweeping.
"""

import asyncio
import platform

async def ping_ip(ip: str) -> bool:
    """Asynchronously ping an IP address. Returns True if it responds, False otherwise."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    # Windows timeout is in milliseconds (1000). Linux timeout is in seconds (1).
    timeout_val = '1000' if platform.system().lower() == 'windows' else '1'
    
    try:
        process = await asyncio.create_subprocess_exec(
            'ping', param, '1', timeout_param, timeout_val, ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.communicate()
        return process.returncode == 0
    except Exception:
        return False

async def ping_sweep(ips: list[str], max_concurrency: int = 50) -> dict[str, bool]:
    """Ping a list of IPs concurrently with a limit."""
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def _ping_with_sem(ip: str):
        async with semaphore:
            result = await ping_ip(ip)
            return ip, result
            
    tasks = [_ping_with_sem(ip) for ip in ips]
    results = await asyncio.gather(*tasks)
    return dict(results)
