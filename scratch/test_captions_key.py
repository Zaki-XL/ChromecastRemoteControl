import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import asyncio
from remote_client import AndroidTVRemoteClient
from config_manager import ConfigManager

async def test_captions():
    cfg = ConfigManager()
    target_ip = cfg.last_device_ip or "192.168.1.136"
    certfile, keyfile = cfg.get_cert_paths()
    rc = AndroidTVRemoteClient(target_ip, certfile, keyfile)
    
    print(f"Connecting to {target_ip}...")
    await rc.connect()
    print("Connected! Sending 'CAPTIONS' key...")
    try:
        await rc.send_key("CAPTIONS", "SHORT")
        print("SUCCESS! Sent KEYCODE_CAPTIONS (175) to Android TV!")
    except Exception as ex:
        print(f"FAILED: {ex}")
    finally:
        rc.disconnect()

if __name__ == "__main__":
    asyncio.run(test_captions())
