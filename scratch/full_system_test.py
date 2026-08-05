import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("FullSystemTest")

from remote_client import AndroidTVRemoteClient
from cast_client import ChromecastCastClient
from config_manager import ConfigManager
import pychromecast

async def run_comprehensive_test():
    print("\n" + "="*60)
    print("      COMPREHENSIVE LIVE DEVICE & PROTOCOL TEST")
    print("="*60 + "\n")

    cfg = ConfigManager()
    target_ip = cfg.last_device_ip or "192.168.1.136"
    print(f"[TARGET DEVICE IP]: {target_ip}\n")

    # --- TEST 1: RemoteClient Connection ---
    print("--- [TEST 1] Testing Android TV Remote Client Connection (Port 6466) ---")
    t0 = time.time()
    certfile, keyfile = cfg.get_cert_paths()
    rc = AndroidTVRemoteClient(target_ip, certfile, keyfile)
    try:
        await rc.connect()
        t1 = time.time()
        print(f" -> SUCCESS: RemoteClient connected in {t1-t0:.3f} seconds!\n")
    except Exception as ex:
        print(f" -> FAILED: RemoteClient connection error: {ex}\n")
        return

    # --- TEST 2: Seek / Fast-Forward Repeat Key Test ---
    print("--- [TEST 2] Testing Seek / Fast-Forward Key Repeat (10 items every 120ms) ---")
    try:
        start_seek_t = time.time()
        for i in range(1, 11):
            await rc.send_key("FAST_FORWARD", "SHORT")
            await rc.send_key("RIGHT", "SHORT")
            print(f" -> Sent seek repeat #{i}")
            await asyncio.sleep(0.12)
        end_seek_t = time.time()
        print(f" -> SUCCESS: 10 Seek repeats sent in {end_seek_t - start_seek_t:.3f} seconds!\n")
    except Exception as ex:
        print(f" -> FAILED: Seek repeat error: {ex}\n")

    # --- TEST 3: Subtitle (CC) Key Test ---
    print("--- [TEST 3] Testing Subtitle Toggle Key ('CAPTIONS' KeyCode 175) ---")
    try:
        t_sub_start = time.time()
        await rc.send_key("CAPTIONS", "SHORT")
        t_sub_end = time.time()
        print(f" -> SUCCESS: KEYCODE_CAPTIONS (175) sent in {t_sub_end - t_sub_start:.3f} seconds!\n")
    except Exception as ex:
        print(f" -> FAILED: Subtitle key error: {ex}\n")

    # --- TEST 4: CastClient Connection & App Status ---
    print("--- [TEST 4] Testing Chromecast CastClient Connection (Port 8009) ---")
    cc = ChromecastCastClient(ip=target_ip)
    try:
        t_cast_start = time.time()
        cc.connect()
        t_cast_end = time.time()
        if cc.cast:
            print(f" -> SUCCESS: CastClient connected in {t_cast_end - t_cast_start:.3f} seconds!")
            print(f" -> Active App: {cc.cast.app_display_name} (App ID: {cc.cast.app_id})")
            mc = cc.cast.media_controller
            print(f" -> Player State: {mc.status.player_state}")
            print(f" -> Content ID: {mc.status.content_id}\n")
        else:
            print(" -> WARNING: CastClient connected but cast object is None.\n")
    except Exception as ex:
        print(f" -> FAILED: CastClient connection error: {ex}\n")

    # --- TEST 5: Clean Disconnect & Exit Responsiveness Test ---
    print("--- [TEST 5] Testing Clean Resource Disconnect & Exit Responsiveness ---")
    try:
        t_disc_start = time.time()
        rc.disconnect()
        cc.disconnect()
        t_disc_end = time.time()
        print(f" -> SUCCESS: Both RemoteClient & CastClient disconnected cleanly in {t_disc_end - t_disc_start:.4f} seconds!")
    except Exception as ex:
        print(f" -> FAILED: Disconnect error: {ex}")

    print("\n" + "="*60)
    print("      COMPREHENSIVE TEST COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
