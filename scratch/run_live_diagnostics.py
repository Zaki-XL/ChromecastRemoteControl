import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Diagnostic")

from remote_client import AndroidTVRemoteClient
from cast_client import ChromecastCastClient
from config_manager import ConfigManager
import pychromecast

async def test_all_features():
    cfg = ConfigManager()
    target_ip = cfg.last_device_ip or "192.168.1.136"
    print(f"\n==================================================")
    print(f"STARTING LIVE TEST ON DEVICE IP: {target_ip}")
    print(f"==================================================\n")

    certfile, keyfile = cfg.get_cert_paths()
    rc = AndroidTVRemoteClient(target_ip, certfile, keyfile)
    
    print("[1] Connecting to Android TV Remote (Port 6466)...")
    try:
        await rc.connect()
        print(" -> RemoteClient SUCCESSFUL!")
    except Exception as ex:
        print(f" -> RemoteClient FAILED: {ex}")
        return

    # 1. シーク連続連打テスト (5秒間連続で右キーを送信してみる)
    print("\n[TEST 1] Testing Seek / Fast Forward Continuous Key Repeat (5 seconds)...")
    print("Sending MEDIA_FAST_FORWARD repeatedly every 150ms for 3 seconds...")
    start_t = asyncio.get_event_loop().time()
    count = 0
    while asyncio.get_event_loop().time() - start_t < 3.0:
        await rc.send_key("FAST_FORWARD", "SHORT")
        await rc.send_key("RIGHT", "SHORT")
        count += 1
        await asyncio.sleep(0.15)
    print(f" -> Sent {count} seek key combinations!")

    # 2. 字幕キーコードテスト (CAPTIONS, SUBTITLE, CC などのキーコード試行)
    print("\n[TEST 2] Testing Remote Subtitle Keycodes...")
    test_sub_keys = ["CAPTIONS", "SUBTITLE", "CLOSED_CAPTIONS", "C"]
    for k in test_sub_keys:
        try:
            print(f" -> Trying key: '{k}'")
            await rc.send_key(k, "SHORT")
            await asyncio.sleep(0.5)
        except Exception as ex:
            print(f" -> Key '{k}' failed: {ex}")

    # 3. CastClient 接続 & メディアプロトコルテスト
    print("\n[TEST 3] Testing CastClient & PyChromecast Media Controller...")
    cc = ChromecastCastClient(ip=target_ip)
    try:
        cc.connect()
        if cc.cast:
            print(f" -> Connected to Cast! App: {cc.cast.app_display_name} (ID: {cc.cast.app_id})")
            mc = cc.cast.media_controller
            print(f" -> Player State: {mc.status.player_state}")
            print(f" -> Content ID: {mc.status.content_id}")
            print(f" -> Subtitle Tracks: {mc.status.subtitle_tracks}")

            print("\n   [3-A] Testing set_playback_rate(1.5)...")
            try:
                mc.set_playback_rate(1.5)
                print("   -> set_playback_rate(1.5) executed cleanly.")
            except Exception as ex:
                print(f"   -> set_playback_rate failed: {ex}")

            print("\n   [3-B] Testing enable_subtitle / disable_subtitle...")
            try:
                mc.disable_subtitle()
                print("   -> disable_subtitle executed cleanly.")
            except Exception as ex:
                print(f"   -> disable_subtitle failed: {ex}")

    except Exception as ex:
        print(f" -> CastClient Connection FAILED: {ex}")

    print("\n==================================================")
    print("LIVE DIAGNOSTIC COMPLETE")
    print("==================================================")
    rc.disconnect()
    cc.disconnect()

if __name__ == "__main__":
    asyncio.run(test_all_features())
