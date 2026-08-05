import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LiveTest")

import pychromecast
from cast_client import ChromecastCastClient
from remote_client import AndroidTVRemoteClient
from config_manager import ConfigManager

async def run_live_tests():
    cfg = ConfigManager()
    target_ip = cfg.last_device_ip
    print(f"Target IP from config: {target_ip}")
    
    if not target_ip:
        casts, browser = pychromecast.get_chromecasts()
        for c in casts:
            if "Chromecast" in c.model_name or "TV" in c.model_name or c.cast_type == "cast":
                target_ip = c.cast_info.host
                print(f"Found target Chromecast: {c.name} ({target_ip})")
                break
        browser.stop_discovery()

    if not target_ip:
        print("ERROR: No target IP found.")
        return

    print(f"\n--- Testing RemoteClient to {target_ip} ---")
    certfile, keyfile = cfg.get_cert_paths()
    rc = AndroidTVRemoteClient(target_ip, certfile, keyfile)
    try:
        await rc.connect()
        print(f"RemoteClient connected! Sending test keys...")
        print("Sending KEY: RIGHT (SHORT)")
        await rc.send_key("RIGHT", "SHORT")
        await asyncio.sleep(0.5)
        print("Sending KEY: RIGHT (START_LONG)")
        await rc.send_key("RIGHT", "START_LONG")
        await asyncio.sleep(0.5)
        print("Sending KEY: RIGHT (END_LONG)")
        await rc.send_key("RIGHT", "END_LONG")
    except Exception as ex:
        print(f"RemoteClient error: {ex}")

    print(f"\n--- Testing CastClient to {target_ip} ---")
    cc = ChromecastCastClient(ip=target_ip)
    try:
        cc.connect()
        print("CastClient connected!")
        if cc.cast:
            mc = cc.cast.media_controller
            print(f"Cast status: app_id={cc.cast.app_id}, app_name={cc.cast.app_display_name}")
            print(f"Media state: player_state={mc.status.player_state}, content_id={mc.status.content_id}")
            print(f"Current subtitle_tracks: {mc.status.subtitle_tracks}")
            
            print("\nTesting seek_relative(+10)...")
            cc.seek_relative(10.0)
            await asyncio.sleep(1.0)

            print("Testing set_playback_rate(1.5)...")
            cc.set_playback_rate(1.5)
            await asyncio.sleep(1.0)

            print("Testing toggle_subtitles(True)...")
            cc.toggle_subtitles(True, "ja")
            await asyncio.sleep(1.0)

    except Exception as ex:
        print(f"CastClient error: {ex}")
        import traceback
        traceback.print_exc()
    finally:
        rc.disconnect()
        cc.disconnect()

if __name__ == "__main__":
    asyncio.run(run_live_tests())
