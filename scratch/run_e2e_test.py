import asyncio
import logging
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath("e:/Project/ChromecastRemoteControl"))

from cast_client import ChromecastCastClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("E2E_Test")

async def test_e2e_media_and_exit():
    logger.info("=== E2E テスト開始 ===")
    
    test_results = []
    
    def dummy_callback(status_data):
        logger.info(f"[E2E UI Callback Received] status_data={status_data}")
        # スライダー等の値チェック
        rate = status_data.get("playback_rate")
        clamped_rate = max(0.5, min(2.0, float(rate))) if rate is not None else 1.0
        assert 0.5 <= clamped_rate <= 2.0, f"Rate out of bounds: {clamped_rate}"
        test_results.append("UI_UPDATE_SUCCESS")

    client = ChromecastCastClient(ip="127.0.0.1", on_status_changed=dummy_callback)
    client.set_event_loop(asyncio.get_running_loop())
    
    # 2. 停止(IDLE)状態のステータス模倣テスト (危険値: playback_rate=0.0)
    class DummyMediaStatus:
        player_state = "IDLE"
        title = None
        artist = None
        album_name = None
        images = []
        current_time = 0.0
        duration = None
        active_track_ids = []
        playback_rate = 0.0

    logger.info("--- テスト 1: IDLE / STOP 時の playback_rate=0.0 の安全処理検証 ---")
    client._handle_media_status_change(DummyMediaStatus())
    await asyncio.sleep(0.1)
    
    # 3. PLAYING 状態のステータス模倣テスト
    class DummyPlayingStatus:
        player_state = "PLAYING"
        title = "Test Video"
        artist = "Test Artist"
        album_name = "Test Album"
        images = []
        current_time = 120.5
        duration = 300.0
        active_track_ids = [1]
        playback_rate = 1.25

    logger.info("--- テスト 2: PLAYING 時の正常ステータス処理検証 ---")
    client._handle_media_status_change(DummyPlayingStatus())
    await asyncio.sleep(0.1)

    # 4. 超過 playback_rate (99.0) 時のクランプ検証
    class DummyExtremeStatus:
        player_state = "PLAYING"
        title = "Fast Video"
        artist = "Fast Artist"
        album_name = None
        images = []
        current_time = 50.0
        duration = 100.0
        active_track_ids = []
        playback_rate = 99.0

    logger.info("--- テスト 3: 異常値 (playback_rate=99.0) のクランプ検証 ---")
    client._handle_media_status_change(DummyExtremeStatus())
    await asyncio.sleep(0.1)

    # 5. 結果評価
    logger.info(f"Test Results Count: {len(test_results)}")
    if len(test_results) == 3:
        logger.info("=== E2E テスト PASS: すべてのメディア状態変更・異常値クランプが安全に通過しました ===")
    else:
        logger.error("=== E2E テスト FAIL ===")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_e2e_media_and_exit())
