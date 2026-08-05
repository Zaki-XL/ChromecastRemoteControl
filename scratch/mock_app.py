import asyncio
import logging
import time
import flet as ft

# ログの設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MockApp")

# 1. pychromecast / ChromecastCastClient のモック化
class MockSocketClient:
    def __init__(self):
        self._connected = True

    def is_connected(self):
        return self._connected

class MockMediaController:
    def __init__(self):
        self.status = None

    def set_playback_rate(self, rate: float) -> None:
        logger.info(f"[MOCK_CHROMECAST] set_playback_rate({rate}) が呼び出されました。")

class MockChromecast:
    def __init__(self, name="MockChromecast"):
        self.name = name
        self.socket_client = MockSocketClient()
        self.media_controller = MockMediaController()

class MockCastClient:
    def __init__(self):
        self.cast = None
        self.ip = "192.168.1.100"

    def connect(self):
        logger.info(f"[MOCK_CLIENT] Chromecast (IP={self.ip}) に接続しました。")
        self.cast = MockChromecast()

    def disconnect(self):
        logger.info("[MOCK_CLIENT] Chromecast から切断しました。")
        self.cast = None

    def set_playback_rate(self, rate: float):
        # 修正後の実装方針を再現
        if not (self.cast and self.cast.media_controller):
            logger.warning("[MOCK_CLIENT] キャストデバイスが接続されていません。")
            return

        # 標準メソッドを直接叩く
        mc = self.cast.media_controller
        if hasattr(mc, "set_playback_rate"):
            logger.info(f"[MOCK_CLIENT] 標準の set_playback_rate メソッドで再生速度変更を送信します: rate={rate}")
            try:
                mc.set_playback_rate(rate)
            except Exception as ex:
                logger.error(f"[MOCK_CLIENT] 送信エラー: {ex}")
        else:
            logger.warning("[MOCK_CLIENT] set_playback_rate が存在しません。")

class MockRemoteClient:
    def __init__(self):
        self.is_connected = False

    def connect(self):
        logger.info("[MOCK_CLIENT] Android TV Remote に接続しました。")
        self.is_connected = True

    def disconnect(self):
        logger.info("[MOCK_CLIENT] Android TV Remote から切断しました。")
        self.is_connected = False

class MockTracker:
    def __init__(self):
        self.running = False

    def start(self):
        logger.info("[MOCK_TRACKER] デバイス探索サービス (Zeroconf) を開始しました。")
        self.running = True

    def stop(self):
        logger.info("[MOCK_TRACKER] デバイス探索サービス (Zeroconf) を停止しました。")
        self.running = False

# グローバルなモック状態
cast_client = MockCastClient()
remote_client = MockRemoteClient()
tracker = MockTracker()

last_device_id = "mock_device_123"
last_device_ip = "192.168.1.100"

async def main(page: ft.Page):
    page.title = "速度スライダー & スリープ復帰検証モック"
    page.window.width = 450
    page.window.height = 650
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    status_text = ft.Text("ステータス: 未接続", color="#FF453A", size=14, weight=ft.FontWeight.BOLD)
    log_text = ft.Text("--- ログ出力 ---\n", size=11, font_family="monospace")
    border_side = ft.BorderSide(1, "#33ffffff")
    log_container = ft.Container(
        content=ft.Column([log_text], scroll=ft.ScrollMode.ALWAYS, auto_scroll=True),
        bgcolor="#1C1C24",
        padding=10,
        height=200,
        border_radius=8,
        border=ft.Border(top=border_side, bottom=border_side, left=border_side, right=border_side)
    )

    def append_log(msg: str):
        log_text.value += f"{time.strftime('%H:%M:%S')} {msg}\n"
        page.update()

    # 接続処理のモック
    async def connect_to_device(device_id: str, ip: str):
        append_log(f"デバイスに接続中: IP={ip}...")
        status_text.value = f"ステータス: 接続中... ({ip})"
        status_text.color = "#FFCC00"
        page.update()

        await asyncio.sleep(1) # 接続のディレイを模倣
        remote_client.connect()
        cast_client.connect()

        status_text.value = f"ステータス: 接続済み ({ip})"
        status_text.color = "#30D158"
        append_log("Remote & Cast への接続が完了しました。")
        page.update()

    # スライダーのイベント
    def on_speed_change(e):
        val = round(e.control.value, 2)
        speed_label.value = f"再生速度: {val}x"
        append_log(f"速度変更スライダーを検知: {val}x")
        cast_client.set_playback_rate(val)
        page.update()

    # スリープシミュレーション用の変数を共有するためのコンテナ
    time_offset = {"value": 0.0}

    # スリープ復旧監視タスク (時間のギャップ検出)
    async def monitor_system_resume():
        append_log("[監視開始] 休止復旧監視タスクがバックグラウンドで開始されました。")
        last_time = time.time() + time_offset["value"]
        while True:
            await asyncio.sleep(2)
            # シミュレートされたタイムシフトを考慮
            now = time.time() + time_offset["value"]
            gap = now - last_time
            if gap > 7.0: # 2秒のループに対して7秒以上のギャップがあれば休止復旧とみなす
                append_log(f"⚠️ [警告] システムの休止復旧（時間のギャップ: {gap:.1f}秒）を検出しました！")
                status_text.value = "ステータス: 休止復旧検知 (再起動中)"
                status_text.color = "#FFCC00"
                page.update()

                # 1. 探索サービス (tracker) のリスタート
                append_log("[復旧フロー] 1/3: 探索サービスをリスタートします...")
                tracker.stop()
                await asyncio.sleep(0.5)
                tracker.start()

                # 2. 古い接続の切断
                append_log("[復旧フロー] 2/3: 古いソケットを切断クリーンアップします...")
                remote_client.disconnect()
                cast_client.disconnect()

                # 3. ネットワーク復帰ウェイトの後、再接続
                append_log("[復旧フロー] 3/3: ネットワーク復帰を待ち、自動再接続を試みます...")
                await asyncio.sleep(1.5)
                asyncio.create_task(connect_to_device(last_device_id, last_device_ip))

            last_time = now

    # 定期接続監視タスク
    async def connection_monitor_loop():
        append_log("[監視開始] 接続自動復旧監視タスクが開始されました (10秒ごと)。")
        while True:
            await asyncio.sleep(10)
            is_remote = remote_client.is_connected
            is_cast = cast_client.cast and cast_client.cast.socket_client.is_connected() if cast_client.cast else False

            if not is_remote or not is_cast:
                append_log(f"[接続監視] 切断を検知しました (Remote={is_remote}, Cast={is_cast})。自動接続を行います。")
                if "接続中" in status_text.value:
                    append_log("[接続監視] すでに接続処理中のためスキップします。")
                    continue
                asyncio.create_task(connect_to_device(last_device_id, last_device_ip))

    # コントロールUI
    speed_label = ft.Text("再生速度: 1.0x", size=14, weight=ft.FontWeight.BOLD)
    speed_slider = ft.Slider(
        min=0.5, max=2.0, value=1.0, divisions=6,
        active_color="#00D2FF", inactive_color="#33ffffff",
        on_change=on_speed_change,
        expand=True
    )

    def trigger_sleep_mock(e):
        append_log("🔴 [操作] PCの休止状態（スリープ）をシミュレートします...")
        append_log("PCがスリープに入りました。ソケット接続を切断します...")
        # スリープに入るとソケットが切れる
        remote_client.disconnect()
        cast_client.disconnect()
        page.update()

        # 時間を12秒進めるシミュレーション
        time_offset["value"] += 12.0
        append_log("PCが復帰しました。12秒の時間が経過しました。")
        page.update()

    sleep_btn = ft.ElevatedButton(
        "スリープ & 復帰 をシミュレート",
        bgcolor="#FF453A",
        color="white",
        on_click=trigger_sleep_mock
    )

    def trigger_manual_disconnect(e):
        append_log("🔴 [操作] 手動で接続を切断します（自動接続監視のテスト用）...")
        remote_client.disconnect()
        cast_client.disconnect()
        page.update()

    disconnect_btn = ft.ElevatedButton(
        "手動で接続を切断 (監視テスト用)",
        bgcolor="#FF9500",
        color="white",
        on_click=trigger_manual_disconnect
    )

    page.add(
        ft.Column([
            ft.Text("Google TV Remote モック検証ツール", size=18, weight=ft.FontWeight.BOLD, color="white"),
            ft.Divider(color="#33ffffff"),
            status_text,
            ft.Divider(color="#19ffffff"),
            ft.Text("1. 再生速度制御テスト", size=14, weight=ft.FontWeight.BOLD, color="#00D2FF"),
            ft.Row([speed_label], alignment=ft.MainAxisAlignment.START),
            ft.Row([speed_slider]),
            ft.Divider(color="#19ffffff"),
            ft.Text("2. 休止状態・自動再接続テスト", size=14, weight=ft.FontWeight.BOLD, color="#00D2FF"),
            ft.Row([sleep_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([disconnect_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color="#19ffffff"),
            ft.Text("実行ログ:", size=12, color="#99ffffff"),
            log_container
        ], spacing=15, expand=True)
    )

    # 最初の接続
    tracker.start()
    asyncio.create_task(connect_to_device(last_device_id, last_device_ip))
    
    # バックグラウンドタスク起動
    asyncio.create_task(monitor_system_resume())
    asyncio.create_task(connection_monitor_loop())

if __name__ == "__main__":
    ft.app(target=main)
