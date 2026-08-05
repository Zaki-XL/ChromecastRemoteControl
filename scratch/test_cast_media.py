import time
import sys
import pychromecast
from pychromecast.controllers.media import MediaStatusListener, MediaStatus
from pychromecast.models import CastInfo, HostServiceInfo

class TestMediaListener(MediaStatusListener):
    def new_media_status(self, status: MediaStatus) -> None:
        print("\n======== [MEDIA STATUS RECEIVED] ========")
        print(f"Player State: {status.player_state}")
        print(f"Title: {status.title}")
        print(f"Artist: {status.artist}")
        print(f"Duration: {status.duration}")
        print(f"Current Time: {status.current_time}")
        print(f"Images: {status.images}")
        print(f"Custom Data: {status.media_custom_data}")
        print("=========================================\n")

    def load_media_failed(self, queue_item_id, error_code):
        print(f"Load media failed: item_id={queue_item_id}, error_code={error_code}")

def test_connection():
    ip = "192.168.1.136"
    print(f"Connecting to Chromecast at {ip} using CastInfo manually...")
    try:
        # CastInfo オブジェクトの手動構築
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
        
        # 直接初期化
        cast = pychromecast.Chromecast(cast_info=cast_info)
        cast.wait(timeout=5.0)
        print(f"Successfully connected to: {cast.name} ({cast.model_name})")
        
        # リスナーの登録
        listener = TestMediaListener()
        cast.media_controller.register_status_listener(listener)
        print("Registered MediaStatusListener successfully.")

        # 強制ステータスアップデート
        print("Sending update_status() request...")
        cast.media_controller.update_status()
        
        # 10秒間監視
        print("Waiting 10 seconds for events...")
        for i in range(10):
            time.sleep(1)
            sys.stdout.write(f".")
            sys.stdout.flush()
            
        print("\nDisconnecting...")
        cast.disconnect()
        print("Done!")
    except Exception as ex:
        print(f"\nTest failed with error: {ex}")

if __name__ == '__main__':
    test_connection()
