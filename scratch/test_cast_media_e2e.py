import time
import sys
import asyncio
import pychromecast
from pychromecast.controllers.media import MediaStatusListener, MediaStatus
from pychromecast.models import CastInfo, HostServiceInfo

# 1. 本番 main.py 内の on_media_status_changed コールバックを再現
def on_media_status_changed(status_info):
    print("\n======== [UI CALLBACK TRIGGERED] ========")
    try:
        title = status_info.get("title") or "Media Stopped"
        artist = status_info.get("artist") or "Device Connected"
        album_art = status_info.get("album_art")
        current_time = status_info.get("current_time")
        duration = status_info.get("duration")
        
        print(f"UI Display Title: {title}")
        print(f"UI Display Artist: {artist}")
        print(f"UI Display Time: {current_time} / {duration}")
        print(f"UI Display Art: {album_art}")
    except Exception as ex:
        print(f"UI Update Exception: {ex}")
    print("=========================================\n")

# 2. 本番 cast_client.py 内のリスナーおよびパース処理を再現
class E2EMediaListener(MediaStatusListener):
    def __init__(self, callback, loop):
        self.callback = callback
        self.loop = loop

    def new_media_status(self, status: MediaStatus) -> None:
        print(f"\n[new_media_status] Received raw status from Chromecast")
        try:
            # 本番 cast_client.py 内の _handle_media_status_change の処理を完全再現
            album_art_url = None
            if status.images and len(status.images) > 0:
                album_art_url = status.images[0].url

            active_ids = getattr(status, 'active_track_ids', []) or []
            raw_rate = getattr(status, 'playback_rate', 1.0)
            try:
                playback_rate = float(raw_rate) if raw_rate is not None and float(raw_rate) > 0 else 1.0
            except (ValueError, TypeError):
                playback_rate = 1.0

            player_state = getattr(status, 'player_state', 'UNKNOWN') or 'UNKNOWN'
            title = getattr(status, 'title', None)
            artist = getattr(status, 'artist', None)
            album_name = getattr(status, 'album_name', None)
            current_time = getattr(status, 'current_time', 0.0) or 0.0
            duration = getattr(status, 'duration', None)

            if player_state in ("IDLE", "STOPPED", "UNKNOWN"):
                playback_rate = 1.0

            # UIに引き渡す辞書データの整形
            status_data = {
                'player_state': player_state,
                'title': title,
                'artist': artist,
                'album_name': album_name,
                'album_art': album_art_url,
                'current_time': current_time,
                'duration': duration,
                'subtitles_enabled': bool(active_ids),
                'playback_rate': playback_rate
            }

            print(f"[Parser Success] status_data constructed: {status_data}")
            
            # 本番と同じスレッド安全イベントループ通知の再現
            if self.loop and self.loop.is_running():
                print("Scheduling callback in asyncio event loop threadsafe...")
                self.loop.call_soon_threadsafe(self.callback, status_data)
            else:
                print("Fallback execution (no running loop)...")
                self.callback(status_data)

        except Exception as e:
            print(f"\n!!! CRITICAL EXCEPTION IN _handle_media_status_change !!!")
            import traceback
            traceback.print_exc()

    def load_media_failed(self, queue_item_id, error_code):
        print(f"Load failed: {queue_item_id}")

async def main():
    ip = "192.168.1.136"
    print(f"E2E Testing: Connecting to {ip}...")
    loop = asyncio.get_running_loop()
    
    cast_info = CastInfo(
        services={HostServiceInfo(ip, 8009)},
        uuid=None,
        model_name="Chromecast",
        friendly_name="Bedroom Cast",
        host=ip,
        port=8009,
        cast_type="cast",
        manufacturer="Google Inc."
    )
    
    cast = pychromecast.Chromecast(cast_info=cast_info)
    # pychromecast の接続待ちを完全非同期実行
    await asyncio.to_thread(cast.wait, 5.0)
    print("Connected to Chromecast socket.")

    listener = E2EMediaListener(on_media_status_changed, loop)
    cast.media_controller.register_status_listener(listener)
    print("Registered listener. Sending initial update_status()...")
    
    # ステータスを要求
    await asyncio.to_thread(cast.media_controller.update_status)
    
    # イベント受領と処理を監視するため5秒待機
    await asyncio.sleep(5.0)
    
    print("Disconnecting...")
    cast.disconnect()
    print("E2E Test Done!")

if __name__ == '__main__':
    asyncio.run(main())
