import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import asyncio
from remote_client import AndroidTVRemoteClient
from config_manager import ConfigManager

async def test_power_key():
    cfg = ConfigManager()
    target_ip = cfg.last_device_ip or "192.168.1.136"
    certfile, keyfile = cfg.get_cert_paths()
    rc = AndroidTVRemoteClient(target_ip, certfile, keyfile)
    
    print(f"Connecting to {target_ip}...")
    await rc.connect()
    print("Connected! Testing Power key variations...")
    
    power_keys = ["POWER", "POWER_TOGGLE", "SLEEP", "GLOBAL_ACTIONS"]
    for k in power_keys:
        try:
            print(f"Trying key: '{k}'...")
            await rc.send_key(k, "SHORT")
            print(f" -> Sent key '{k}' SUCCESS!")
            await asyncio.sleep(1.0)
        except Exception as ex:
            print(f" -> Key '{k}' FAILED: {ex}")
            
    rc.disconnect()

if __name__ == "__main__":
    asyncio.run(test_power_key())
