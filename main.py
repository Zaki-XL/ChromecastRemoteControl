import asyncio
import logging
import threading
import time
import socket
import sys
import subprocess
from typing import Any, Dict

import flet as ft

from config_manager import ConfigManager
from device_tracker import AndroidTVTracker
from remote_client import AndroidTVRemoteClient, PairingRequiredException
from cast_client import ChromecastCastClient

# 多重起動防止用のグローバルソケット保持変数
_lock_socket = None

def prevent_multiple_instances(port: int = 64660):
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # ローカルの排他的なポートをバインド
        _lock_socket.bind(('127.0.0.1', port))
        _lock_socket.listen(1)
    except OSError:
        logger = logging.getLogger(__name__)
        logger.warning("GoogleTVRemote is already running. Exiting...")
        sys.exit(0)

# ログの設定 (ファイルとコンソールの両方に出力。サイズ制限付きローテーションを実装)
import os
from logging.handlers import RotatingFileHandler

def get_app_dir() -> str:
    """PyInstallerでexe化されている場合も、実行ファイルのあるフォルダパスを正しく取得します。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

log_file_path = os.path.join(get_app_dir(), "app_debug.log")
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s (%(threadName)s): %(message)s")

# RotatingFileHandler を使用し、最大10MB・3世代でローテーション (65GB肥大化防止のガードレール)
file_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=10 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
# 重複ハンドラ防止
root_logger.handlers = [file_handler, console_handler]

# サードパーティライブラリのDEBUGログを抑制し、無制限の書き込みを防止する
logging.getLogger("pychromecast").setLevel(logging.INFO)
logging.getLogger("zeroconf").setLevel(logging.INFO)
logging.getLogger("androidtvremote2").setLevel(logging.INFO)
logging.getLogger("flet").setLevel(logging.INFO)
logging.getLogger("flet_core").setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info(f"=== Debug logging initialized -> {log_file_path} (Max 10MB x 3 backup rotation enabled) ===")

def force_exit_app() -> None:
    """OSレベルで即時かつ確実にアプリを完全終了させます。"""
    logger.info("[SHUTDOWN] App termination ordered. Executing instant process termination via os._exit(0)...")
    for h in root_logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    import os
    os._exit(0)




# グローバル状態・インスタンスの管理
config = ConfigManager()
remote_client: AndroidTVRemoteClient = None
cast_client: ChromecastCastClient = None
tracker: AndroidTVTracker = None
loop: asyncio.AbstractEventLoop = None

# キーボードおよびGUIボタンの長押し処理用の状態辞書
held_keys: Dict[str, float] = {}
held_keys_lock = threading.Lock()

held_buttons: Dict[str, float] = {}
held_buttons_lock = threading.Lock()

# ネオンパープル/ブルーのグラデーション定義
neon_gradient = ft.LinearGradient(
    begin=ft.alignment.Alignment.TOP_LEFT,
    end=ft.alignment.Alignment.BOTTOM_RIGHT,
    colors=["#8A2BE2", "#00D2FF"]  # 鮮やかなパープルからシアンブルー
)

# キーボード入力とリモートキーコードの対応マッピング
KEY_MAPPING = {
    "Arrow Up": "UP",
    "Arrow Down": "DOWN",
    "Arrow Left": "LEFT",
    "Arrow Right": "RIGHT",
    "Up": "UP",
    "Down": "DOWN",
    "Left": "LEFT",
    "Right": "RIGHT",
    "Enter": "ENTER",
    "Backspace": "BACK",
    "Escape": "BACK",
    "Home": "HOME",
    " ": "PLAY_PAUSE",
    "Space": "PLAY_PAUSE",
    "Page Up": "VOLUME_UP",
    "Page Down": "VOLUME_DOWN",
    "PageUp": "VOLUME_UP",
    "PageDown": "VOLUME_DOWN",
    "+": "VOLUME_UP",
    "-": "VOLUME_DOWN",
    "Add": "VOLUME_UP",
    "Subtract": "VOLUME_DOWN",
    "M": "MUTE",
    "m": "MUTE"
}

def get_border_all(width: int, color: str) -> ft.Border:
    """Fletのバージョン互換性を保つためのボーダー生成ヘルパーです。"""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, bottom=side, left=side, right=side)


def GlassCard(content: ft.Control, width: int = None, height: int = None, padding: int = 12, border_radius: int = 16) -> ft.Container:
    """グラスモルフィズム風のコンテナカードを生成します。"""
    return ft.Container(
        content=content,
        width=width,
        height=height,
        padding=padding,
        border_radius=border_radius,
        bgcolor="#0fffffff",  # 6% 不透明度の白
        border=get_border_all(1, "#1effffff"),  # 12% 不透明度の白
        blur=ft.Blur(15, 15, tile_mode=ft.BlurTileMode.CLAMP),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=12,
            color="#268A2BE2",  # 15% 不透明度のネオンパープル
            offset=ft.Offset(0, 4)
        )
    )


async def main(page: ft.Page) -> None:
    global remote_client, cast_client, tracker, loop
    loop = asyncio.get_running_loop()

    # ページの初期設定（INIから読み込み）
    page.title = "Android TV & Cast Remote"
    page.window.width = config.window_width
    page.window.height = config.window_height
    page.window.resizable = True
    page.window.opacity = config.window_opacity
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = True
    page.window.prevent_close = True
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121214"  # 深い背景色
    page.padding = 15

    def on_page_error(e):
        err_msg = e.data if hasattr(e, 'data') else str(e)
        logger.error(f"Flet Page Global Error: {err_msg}")

    page.on_error = on_page_error


    def window_event(e):
        event_data = e.data if hasattr(e, 'data') else str(e)
        if event_data == "close":
            logger.info("ウィンドウクローズイベントを受信しました。リソースを解放して強制終了します...")
            try:
                if tracker:
                    tracker.stop()
                if remote_client:
                    remote_client.disconnect()
                if cast_client:
                    cast_client.disconnect()
            except Exception as ex:
                logger.error(f"クリーンアップエラー: {ex}")
            import os
            os._exit(0)

    page.window.on_event = window_event

    def on_window_resized(e):
        nonlocal current_scale
        if page.window.width and page.window.width > 0:
            new_scale = max(0.5, min(2.0, page.window.width / 420.0))
            if abs(new_scale - current_scale) > 0.02:
                current_scale = new_scale
                if 'size_slider' in locals() and size_slider:
                    size_slider.value = current_scale
                    size_label.value = f"サイズ: {int(page.window.width)}×{int(page.window.height)}"
                if 'root_listener' in locals() and root_listener:
                    root_listener.content = build_main_layout()
                page.update()

    page.on_resized = on_window_resized

    # 1. 各クライアントのインスタンス化
    certfile, keyfile = config.get_cert_paths()
    remote_client = AndroidTVRemoteClient(
        ip="",
        certfile=certfile,
        keyfile=keyfile
    )
    cast_client = ChromecastCastClient(ip="")

    # --- UI Design Tokens & Base Font Size Standards ---
    FONT_SIZE_TITLE_MAIN = 15        # Header title "Google TV Remote"
    FONT_SIZE_ACCORDION_TITLE = 11    # Accordion titles ("Settings & Devices", "Quick Launch Apps")
    FONT_SIZE_LABEL = 10             # Setting labels ("Scale Multiplier", "Window Opacity")
    FONT_SIZE_STATUS = 11            # Status text ("Status: Disconnected")
    FONT_SIZE_DEVICE_LABEL = 9       # Discovered devices label
    FONT_SIZE_CHIP = 10              # Device chip text
    FONT_SIZE_BUTTON_LG = 18         # D-Pad arrow buttons (▲, ▼, ◀, ▶)
    FONT_SIZE_BUTTON_MD = 14         # OK Center button
    FONT_SIZE_BUTTON_SM = 13         # Action buttons (Power, Back, Home, Vol etc)
    FONT_SIZE_APP_LABEL = 9          # Quick launch app label
    FONT_SIZE_MEDIA_TITLE = 11       # Media player title
    FONT_SIZE_MEDIA_ARTIST = 9       # Media player artist

    initial_scale = max(0.5, min(1.5, config.window_width / 420.0))
    current_scale: float = initial_scale

    # --- 動的相対サイズ計算プロパティ (Scale Factor) ---
    def S(val: float) -> int:
        """現在のスケール倍率に比例した整数ピクセルサイズを返します。"""
        return max(1, int(val * current_scale))

    def FS(base_font_size: float) -> int:
        """現在のスケール倍率に追随した動的フォントサイズを返します。"""
        return max(7, int(base_font_size * current_scale))

    # 2. UIコンポーネントの作成
    # スナックバー（通知用）
    snackbar = ft.SnackBar(content=ft.Text(""), bgcolor="#8A2BE2")
    page.overlay.append(snackbar)

    def show_info(text: str) -> None:
        snackbar.content.value = text
        snackbar.bgcolor = "#8A2BE2"
        snackbar.open = True
        page.update()

    def show_error(text: str) -> None:
        snackbar.content.value = text
        snackbar.bgcolor = "#E50914"
        snackbar.open = True
        page.update()

    # 接続中プログレスリング
    progress_ring = ft.ProgressRing(width=20, height=20, stroke_width=2, color="#8A2BE2", visible=False)

    # 接続ステータステキスト
    status_text = ft.Text("Status: Disconnected", color="#FF453A", size=FS(FONT_SIZE_STATUS), weight=ft.FontWeight.BOLD)

    # デバイスチップ一覧パネル
    devices_panel = ft.Row(
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    def create_device_chip(friendly_name: str, ip: str, device_id: str) -> ft.Container:
        def on_chip_click(e):
            logger.info(f"Device chip clicked: {friendly_name} ({ip})")
            asyncio.create_task(connect_to_device(device_id, ip, force=True))

        chip_container = ft.Container(
            content=ft.Row(
                [
                    ft.Text("📺", size=FS(11)),
                    ft.Text(friendly_name, color="white", size=FS(FONT_SIZE_CHIP), weight=ft.FontWeight.BOLD)
                ],
                spacing=5
            ),
            bgcolor="#1C1C24",
            padding=8,
            border_radius=12,
            border=get_border_all(1, "#33ffffff"),
            data=ip,
            on_click=on_chip_click
        )
        return chip_container

    def update_device_chips_ui(active_ip: str) -> None:
        try:
            for chip in devices_panel.controls:
                if chip.data == active_ip:
                    # 接続中：背景をネオンパープルに染め、枠線も明るく光らせる
                    chip.bgcolor = "#8A2BE2"
                    chip.border = get_border_all(2, "#A855F7")
                else:
                    # 未接続：通常ダーク
                    chip.bgcolor = "#1C1C24"
                    chip.border = get_border_all(1, "#33ffffff")
            page.update()
        except Exception as ex:
            logger.error(f"Device chip UI update error: {ex}")

    # 8. デバイス探索サービス (mDNS) コールバックとインスタンスの初期化
    async def handle_device_discovered_async(device_info: Dict[str, Any]) -> None:
        dev_id = device_info['device_id']
        friendly_name = device_info['friendly_name']
        ip = device_info['ip']
        
        if not any(chip.key == dev_id for chip in devices_panel.controls):
            chip = create_device_chip(friendly_name, ip, dev_id)
            chip.key = dev_id
            devices_panel.controls.append(chip)
            
            if remote_client and remote_client.is_connected:
                update_device_chips_ui(remote_client.ip)
            else:
                page.update()
            logger.info(f"UI device panel auto-added chip: {friendly_name} ({ip})")

    def on_device_discovered(device_info: Dict[str, Any]) -> None:
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(handle_device_discovered_async(device_info), loop)

    def on_device_ip_changed(device_id: str, new_ip: str) -> None:
        active_id = config.last_device_id
        if device_id == active_id:
            logger.info(f"Active device IP change detected: ID={device_id}, New IP={new_ip}")
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(handle_ip_changed_async(new_ip), loop)

    async def handle_ip_changed_async(new_ip: str) -> None:
        show_info(f"Device IP change detected. Reconnecting to: {new_ip}")
        config.last_device_ip = new_ip
        await remote_client.update_ip_and_reconnect(new_ip)
        start_cast_connection(new_ip)

    tracker = AndroidTVTracker(
        on_ip_changed=on_device_ip_changed,
        on_device_discovered=on_device_discovered
    )

    # スキャン（リフレッシュ）ボタン
    def on_refresh_click(e: ft.ControlEvent) -> None:
        async def do_refresh():
            devices_panel.controls = []
            progress_ring.visible = True
            page.update()

            logger.info("Starting rediscovery...")
            tracker.stop()
            tracker.start()

            await asyncio.sleep(3)

            devices = tracker.list_devices()
            logger.info(f"Device discovery complete: {len(devices)} found")
            for dev in devices:
                chip = create_device_chip(dev['friendly_name'], dev['ip'], dev['device_id'])
                chip.key = dev['device_id']
                devices_panel.controls.append(chip)
                
            progress_ring.visible = False
            
            if config.last_device_id and any(d['device_id'] == config.last_device_id for d in devices):
                asyncio.create_task(connect_to_device(config.last_device_id, config.last_device_ip))
                
            if remote_client and remote_client.is_connected:
                update_device_chips_ui(remote_client.ip)
            else:
                page.update()

        asyncio.create_task(do_refresh())

    refresh_btn = ft.Container(
        content=ft.Text("🔄", color="#8A2BE2", size=14, weight=ft.FontWeight.BOLD),
        alignment=ft.alignment.Alignment.CENTER,
        width=36,
        height=36,
        border_radius=18,
        on_click=on_refresh_click
    )

    # ウィンドウ設定スライダーパネル

    header_title = ft.Text("Google TV Remote", color="white", weight=ft.FontWeight.BOLD, size=FS(FONT_SIZE_TITLE_MAIN))
    size_label = ft.Text(f"Size: {int(page.window.width)}×{int(page.window.height)}", color="#b3ffffff", size=FS(FONT_SIZE_LABEL))
    opacity_label = ft.Text(f"Opacity: {int(page.window.opacity * 100)}%", color="#b3ffffff", size=FS(FONT_SIZE_LABEL))
    discovered_devices_label = ft.Text("Discovered Devices (Tap to connect):", color="#b3ffffff", size=FS(FONT_SIZE_DEVICE_LABEL))

    settings_accordion_title = ft.Text("⚙️ Settings & Devices", size=FS(FONT_SIZE_ACCORDION_TITLE), color="#00D2FF", weight=ft.FontWeight.BOLD)
    apps_accordion_title = ft.Text("🚀 Quick Launch Apps", size=FS(FONT_SIZE_ACCORDION_TITLE), color="#00D2FF", weight=ft.FontWeight.BOLD)

    def update_all_font_sizes():
        """スケール変更に伴い、すべてのテキスト・ラベルのフォントサイズを一括追随更新します。"""
        header_title.size = FS(FONT_SIZE_TITLE_MAIN)
        status_text.size = FS(FONT_SIZE_STATUS)
        size_label.size = FS(FONT_SIZE_LABEL)
        opacity_label.size = FS(FONT_SIZE_LABEL)
        discovered_devices_label.size = FS(FONT_SIZE_DEVICE_LABEL)
        settings_accordion_title.size = FS(FONT_SIZE_ACCORDION_TITLE)
        apps_accordion_title.size = FS(FONT_SIZE_ACCORDION_TITLE)
        media_title.size = FS(FONT_SIZE_MEDIA_TITLE)
        media_artist.size = FS(FONT_SIZE_MEDIA_ARTIST)

    save_timer: Optional[threading.Timer] = None

    def schedule_config_save():
        nonlocal save_timer
        if save_timer:
            save_timer.cancel()
        save_timer = threading.Timer(0.5, config.save)
        save_timer.start()

    def on_size_change(e):
        nonlocal current_scale
        current_scale = e.control.value  # 0.5 〜 1.5
        new_w = int(420 * current_scale)
        new_h = int(750 * current_scale)
        page.window.width = new_w
        page.window.height = new_h
        config.config.set(config.SECTION_WINDOW, 'width', str(new_w))
        config.config.set(config.SECTION_WINDOW, 'height', str(new_h))
        schedule_config_save()
        size_label.value = f"Size: {new_w}×{new_h}"
        
        # フォントサイズおよびレイアウト寸法を一括追随更新
        update_all_font_sizes()
        if 'root_listener' in locals() and root_listener:
            root_listener.content = build_main_layout()
        page.update()

    def on_opacity_change(e):
        opacity = e.control.value  # 0.2 〜 1.0
        page.window.opacity = opacity
        config.config.set(config.SECTION_WINDOW, 'opacity', f'{opacity:.2f}')
        schedule_config_save()
        opacity_label.value = f"Opacity: {int(opacity * 100)}%"
        page.update()

    size_slider = ft.Slider(
        min=0.5, max=1.5, value=initial_scale, divisions=20,
        active_color="#8A2BE2", inactive_color="#33ffffff",
        on_change=on_size_change,
        expand=True
    )
    opacity_slider = ft.Slider(
        min=0.2, max=1.0, value=config.window_opacity, divisions=16,
        active_color="#00D2FF", inactive_color="#33ffffff",
        on_change=on_opacity_change,
        expand=True
    )

    def on_close_click(e):
        logger.info("[UI_EVENT] Close button clicked by user. Destroying window...")
        try:
            asyncio.create_task(page.window.destroy())
        except Exception as ex:
            logger.error(f"Failed to destroy window: {ex}")

    global on_close_click_ref
    on_close_click_ref = on_close_click

    close_btn = ft.Container(
        content=ft.Text("✕", color="#b3ffffff", size=FS(11), weight=ft.FontWeight.BOLD),
        width=S(26),
        height=S(26),
        alignment=ft.alignment.Alignment.CENTER,
        border_radius=13,
        bgcolor="#1C1C24",
        border=get_border_all(1, "#33ffffff"),
        on_click=on_close_click
    )

    header_drag_area = ft.WindowDragArea(
        content=ft.Row(
            [
                ft.Text("📺", size=FS(13)),
                header_title
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        expand=True
    )

    header_row = ft.Row(
        [
            header_drag_area,
            close_btn
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    # ペアリング入力ダイアログ
    pin_input = ft.TextField(
        label="6-digit PIN",
        max_length=6,
        width=180,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        color="white",
        border_color="#8A2BE2"
    )

    def on_pairing_submit(e: ft.ControlEvent) -> None:
        pin = pin_input.value
        if not pin or len(pin) != 6:
            show_error("Please enter a valid 6-digit PIN code.")
            return

        pairing_dialog.open = False
        page.update()

        async def do_submit():
            try:
                show_info("Completing pairing authentication...")
                await remote_client.send_pin(pin)
                show_info("Pairing complete! Connected successfully.")

                status_text.value = f"Status: Remote Connected ({remote_client.ip})"
                status_text.color = "#30D158"
                page.update()

                devices = tracker.list_devices()
                selected_dev = next((d for d in devices if d['ip'] == remote_client.ip), None)
                if selected_dev:
                    config.last_device_id = selected_dev['device_id']
                    config.last_device_name = selected_dev['friendly_name']
                    config.last_device_ip = selected_dev['ip']

                start_cast_connection(remote_client.ip)
            except Exception as ex:
                logger.error(f"PIN submit error: {ex}")
                show_error(f"Pairing failed: {ex}")

        asyncio.create_task(do_submit())

    def on_pairing_cancel(e: ft.ControlEvent) -> None:
        pairing_dialog.open = False
        remote_client.disconnect()
        page.update()

    pairing_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Pairing Authentication", size=18, weight=ft.FontWeight.BOLD),
        content=ft.Column(
            [
                ft.Text("Enter the 6-digit PIN code shown on your TV screen.", size=12),
                pin_input
            ],
            spacing=15,
            height=110,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        actions=[
            ft.TextButton("Connect", on_click=on_pairing_submit),
            ft.TextButton("Cancel", on_click=on_pairing_cancel)
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    # 6. コールバックとバックグラウンドタスクの定義
    async def connect_to_device(device_id: str, ip: str, force: bool = False) -> None:
        """指定されたデバイスへのリモートおよびキャストの接続処理を非同期に行います。"""
        show_info(f"Connecting to device: {ip}...")
        status_text.value = f"Status: Connecting... ({ip})"
        status_text.color = "#FFCC00"
        page.update()
        try:
            remote_client.ip = ip
            # 5秒のタイムアウト保護を設けてリモート接続を実行
            await asyncio.wait_for(remote_client.connect(), timeout=5.0)
            show_info("Remote connected!")
            status_text.value = f"Status: Remote Connected ({ip})"
            status_text.color = "#30D158"
            update_device_chips_ui(ip)
            page.update()

            config.last_device_id = device_id
            config.last_device_ip = ip
            
            devices = tracker.list_devices()
            target = next((d for d in devices if d['device_id'] == device_id), None)
            if target:
                config.last_device_name = target['friendly_name']

            start_cast_connection(ip, force=force)

        except PairingRequiredException:
            pin_input.value = ""
            pairing_dialog.open = True
            status_text.value = "Status: Pairing Required"
            status_text.color = "#FFCC00"
            page.update()
            try:
                await remote_client.start_pairing()
            except Exception as ex:
                show_error(f"Pairing failed to start: {ex}")
                status_text.value = "Status: Disconnected"
                status_text.color = "#FF453A"
                update_device_chips_ui("")
                page.update()
        except Exception as e:
            logger.error(f"Device connection error: {e}")
            show_error(f"Connection failed: {e}")
            status_text.value = "Status: Connection Failed"
            status_text.color = "#FF453A"
            update_device_chips_ui("")
            page.update()

    def start_cast_connection(ip: str, force: bool = False) -> None:
        """別スレッドでChromecastCastClientの同期接続を開始します。"""
        cast_client.ip = ip
        cast_client.set_event_loop(asyncio.get_running_loop())

        def bg_connect():
            try:
                cast_client.connect(force=force)
                
                # Castソケットの本当の接続状態を判定
                sc = getattr(cast_client.cast, "socket_client", None) if cast_client.cast else None
                is_connected = sc and hasattr(sc, "is_connected") and sc.is_connected
                
                if is_connected:
                    logger.info("Cast client connected successfully.")
                    cast_client.apply_preferred_language(config.preferred_language)
                    
                    def update_status_connected():
                        status_text.value = f"Status: Connected ({ip})"
                        status_text.color = "#30D158"
                        update_device_chips_ui(ip)
                        page.update()
                    
                    loop.call_soon_threadsafe(update_status_connected)
                else:
                    raise RuntimeError("Cast client socket is not connected after connect()")
            except Exception as ex:
                logger.error(f"Cast client connection error: {ex}")
                def update_status_failed():
                    status_text.value = f"Status: Remote Connected ({ip})"
                    status_text.color = "#30D158"
                    update_device_chips_ui(ip)
                    page.update()
                loop.call_soon_threadsafe(update_status_failed)

        threading.Thread(target=bg_connect, daemon=True).start()

    # 3. D-pad & リモコンボタンのアクション処理
    async def send_remote_key(key: str, direction: str) -> None:
        """リモコンキーの送信を実行します。"""
        try:
            if key in ("VOLUME_UP", "VOLUME_DOWN", "MUTE") and cast_client and cast_client.cast:
                logger.info(f"キャストクライアント経由で音量・ミュート制御を実行します: {key}")
                try:
                    if key == "VOLUME_UP":
                        cast_client.volume_up()
                    elif key == "VOLUME_DOWN":
                        cast_client.volume_down()
                    elif key == "MUTE":
                        status = cast_client.cast.status
                        is_muted = status.volume_muted if status else False
                        cast_client.mute(not is_muted)
                    
                    if remote_client and remote_client.is_connected:
                        await remote_client.send_key(key, direction)
                    return
                except Exception as cast_ex:
                    logger.warning(f"キャスト経由の音量制御に失敗、リモコン経由を試みます: {cast_ex}")

            if key == "POWER":
                logger.info("電源オフ (POWER) 信号を送信します...")
                if remote_client and remote_client.is_connected:
                    try:
                        await remote_client.send_key("POWER", direction)
                    except Exception as p_ex:
                        logger.warning(f"POWER送信時の通信切断: {p_ex}")
                if cast_client:
                    cast_client.disconnect()
                if remote_client:
                    remote_client.disconnect()
                status_text.value = "Status: Power Off"
                status_text.color = "#8E8E93"
                update_device_chips_ui("")
                page.update()
                show_info("電源オフ信号を送信しました。")
                return

            if remote_client and remote_client.is_connected:
                await remote_client.send_key(key, direction)
            else:
                show_error("デバイスと接続されていません。")
        except Exception as ex:
            logger.error(f"キー送信エラー ({key}, {direction}): {ex}")

    # ボタン押し下げ (Press-Hold) トラッキングタスク辞書
    held_button_tasks: Dict[str, asyncio.Task] = {}

    def stop_button_hold(button_name: str) -> None:
        if button_name in held_button_tasks:
            task = held_button_tasks.pop(button_name)
            task.cancel()

    # シーク操作のデバウンス保護タイムスタンプ
    last_user_seek_time: float = 0.0

    def perform_seek(button_name: str):
        nonlocal last_user_seek_time
        last_user_seek_time = time.time()
        
        delta_seconds = 10.0 if button_name == "RIGHT" else (-10.0 if button_name == "LEFT" else 0.0)
        
        if delta_seconds != 0.0 and cast_client and cast_client.cast and cast_client.cast.media_controller:
            status = cast_client.cast.media_controller.status
            if status and getattr(status, 'duration', 0):
                dur = status.duration
                curr = getattr(status, 'current_time', 0) or 0
                target = max(0.0, min(dur, curr + delta_seconds))
                progress_bar.value = min(1.0, max(0.0, target / dur))
                progress_text.value = f"{format_time(target)} / {format_time(dur)}"
                page.update()

        if remote_client and remote_client.is_connected:
            asyncio.create_task(send_remote_key(button_name, "SHORT"))
        elif cast_client and cast_client.cast and button_name in ("LEFT", "RIGHT"):
            cast_client.seek_relative(delta_seconds)

    global perform_seek_ref
    perform_seek_ref = perform_seek

    async def start_button_hold_loop(button_name: str) -> None:
        try:
            while True:
                if remote_client and remote_client.is_connected:
                    await remote_client.send_key(button_name, "SHORT")
                elif cast_client and cast_client.cast and button_name in ("LEFT", "RIGHT"):
                    perform_seek(button_name)
                await asyncio.sleep(0.15)  # リピート間隔
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            logger.error(f"Long press loop error ({button_name}): {ex}")

    def on_button_tap(button_name: str, container: ft.Container):
        container.bgcolor = "#8A2BE2"
        container.border = get_border_all(2, "#A855F7")
        page.update()
        
        perform_seek(button_name)
            
        def reset():
            container.bgcolor = "#1C1C24"
            container.border = get_border_all(1, "#33ffffff")
            page.update()
        threading.Timer(0.15, reset).start()



    def on_long_press_start(button_name: str, container: ft.Container, *args, **kwargs):
        container.bgcolor = "#8A2BE2"
        container.border = get_border_all(2, "#00D2FF")
        page.update()
        stop_button_hold(button_name)
        held_button_tasks[button_name] = asyncio.create_task(start_button_hold_loop(button_name))

    def on_long_press_end(button_name: str, container: ft.Container, default_bgcolor: str = "#1C1C24", *args, **kwargs):
        stop_button_hold(button_name)
        container.bgcolor = default_bgcolor
        container.border = get_border_all(1, "#33ffffff")
        page.update()

    # 7. グローバルキーボード操作イベントハンドラ
    async def wait_for_key_long_press(key: str, mapped_key: str, start_time: float) -> None:
        await asyncio.sleep(0.4)
        with held_keys_lock:
            if key in held_keys and held_keys[key] == start_time:
                await send_remote_key(mapped_key, "START_LONG")

    def on_key_down(e: ft.KeyboardEvent) -> None:
        key = e.key
        mapped = KEY_MAPPING.get(key)
        if not mapped:
            return

        with held_keys_lock:
            if key in held_keys:
                return
            start_time = time.time()
            held_keys[key] = start_time

        asyncio.create_task(wait_for_key_long_press(key, mapped, start_time))

    def on_key_up(e: ft.KeyboardEvent) -> None:
        key = e.key
        mapped = KEY_MAPPING.get(key)
        if not mapped:
            return

        with held_keys_lock:
            if key not in held_keys:
                return
            start_time = held_keys.pop(key)

        duration = time.time() - start_time
        if duration < 0.4:
            asyncio.create_task(send_remote_key(mapped, "SHORT"))
        else:
            asyncio.create_task(send_remote_key(mapped, "END_LONG"))

    # D-pad ボタンのファクトリ (タップ短押し & 長押し連続リピート)
    def DPadBtn(label: str, name: str, base_size: int = 60) -> ft.Control:
        sz = S(base_size)
        font_sz = FS(FONT_SIZE_BUTTON_LG)

        container = ft.Container(
            content=ft.Text(label, color="white", size=font_sz, weight=ft.FontWeight.BOLD),
            width=sz,
            height=sz,
            alignment=ft.alignment.Alignment.CENTER,
            shape=ft.BoxShape.CIRCLE,
            bgcolor="#1C1C24",
            border=get_border_all(1, "#33ffffff")
        )

        return ft.GestureDetector(
            content=container,
            on_tap=lambda e: on_button_tap(name, container),
            on_long_press_start=lambda e: on_long_press_start(name, container),
            on_long_press_end=lambda e: on_long_press_end(name, container),
            on_long_press_cancel=lambda e: on_long_press_end(name, container)
        )

    # 決定ボタン (OK)
    def DPadCenterBtn(base_size: int = 60) -> ft.Control:
        sz = S(base_size)
        font_sz = FS(FONT_SIZE_BUTTON_MD)

        container = ft.Container(
            content=ft.Text("OK", color="white", weight=ft.FontWeight.BOLD, size=font_sz),
            width=sz,
            height=sz,
            alignment=ft.alignment.Alignment.CENTER,
            shape=ft.BoxShape.CIRCLE,
            gradient=neon_gradient,
            border=get_border_all(1, "#33ffffff"),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color="#668A2BE2"
            )
        )

        return ft.GestureDetector(
            content=container,
            on_tap=lambda e: on_button_tap("ENTER", container),
            on_long_press_start=lambda e: on_long_press_start("ENTER", container),
            on_long_press_end=lambda e: on_long_press_end("ENTER", container),
            on_long_press_cancel=lambda e: on_long_press_end("ENTER", container)
        )

    # 左右の物理的バランスを取るための透明スペーサー
    def Spacer60(base_size: int = 60) -> ft.Container:
        sz = S(base_size)
        return ft.Container(width=sz, height=sz, bgcolor="transparent")

    # リモコン周辺ボタン
    def ActionBtn(label: str, name: str, color: str = "white", bgcolor: str = "#1A1A24", base_size: int = 46) -> ft.Control:
        sz = S(base_size)
        font_sz = FS(FONT_SIZE_BUTTON_SM if base_size < 60 else FONT_SIZE_BUTTON_LG)

        container = ft.Container(
            content=ft.Text(label, color=color, size=font_sz, weight=ft.FontWeight.BOLD),
            width=sz,
            height=sz,
            alignment=ft.alignment.Alignment.CENTER,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=bgcolor,
            border=get_border_all(1, "#19ffffff")
        )

        return ft.GestureDetector(
            content=container,
            on_tap=lambda e: on_button_tap(name, container),
            on_long_press_start=lambda e: on_long_press_start(name, container),
            on_long_press_end=lambda e: on_long_press_end(name, container, bgcolor),
            on_long_press_cancel=lambda e: on_long_press_end(name, container, bgcolor)
        )

    # 4. アプリケーションクイック起動グリッド (スケール追随)
    def AppBtn(name: str, symbol: str, color: str, app_link: str) -> ft.Container:
        def on_app_click(e: ft.ControlEvent) -> None:
            async def do_launch():
                try:
                    if remote_client and remote_client.is_connected:
                          show_info(f"Launching {name}...")
                          await remote_client.launch_app(app_link)
                    else:
                          show_error("Remote is not connected.")
                except Exception as ex:
                    show_error(f"Failed to launch app: {ex}")
            asyncio.create_task(do_launch())

        sym_sz = FS(18)
        label_sz = FS(FONT_SIZE_APP_LABEL)
        w = S(65)
        h = S(50)
        
        container = ft.Container(
            content=ft.Column(
                [
                    ft.Text(symbol, size=sym_sz),
                    ft.Text(name, size=label_sz, color="white", weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2
            ),
            width=w,
            height=h,
            border_radius=8,
            bgcolor="#1A1A24",
            border=get_border_all(1, color if color else "#19ffffff"),
            on_click=on_app_click
        )

        def on_hover(e):
            if e.data == "true":
                container.border = get_border_all(2.5, "#00D2FF")
            else:
                container.border = get_border_all(1, color if color else "#19ffffff")
            page.update()

        container.on_hover = on_hover
        return container

    # 5. ボトムメディア操作 & 情報表示パネル
    media_art = ft.Image(
        src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe",
        width=55,
        height=55,
        border_radius=6,
        fit="cover"
    )

    media_title = ft.Text(
        "Media Stopped",
        size=FS(FONT_SIZE_MEDIA_TITLE),
        color="white",
        weight=ft.FontWeight.BOLD,
        overflow=ft.TextOverflow.ELLIPSIS,
        max_lines=1
    )
    
    media_artist = ft.Text(
        "No Device Connected",
        size=FS(FONT_SIZE_MEDIA_ARTIST),
        color="#99ffffff",
        overflow=ft.TextOverflow.ELLIPSIS,
        max_lines=1
    )

    current_duration: float = 0.0
    is_slider_dragging: bool = False

    def on_slider_change(e):
        nonlocal is_slider_dragging
        is_slider_dragging = True
        current_val = e.control.value
        progress_text.value = f"{format_time(current_val)} / {format_time(current_duration)} (Seeking...)"
        page.update()

    def on_slider_change_end(e):
        nonlocal is_slider_dragging, last_user_seek_time
        target_val = e.control.value
        if cast_client:
            cast_client.seek(target_val)
        is_slider_dragging = False
        last_user_seek_time = time.time()
        progress_text.value = f"{format_time(target_val)} / {format_time(current_duration)}"
        page.update()

    progress_bar = ft.Slider(
        value=0.0,
        min=0.0,
        max=100.0,
        on_change=on_slider_change,
        on_change_end=on_slider_change_end,
        disabled=True,
        active_color="#8A2BE2",
        inactive_color="#2C2C35",
    )
    progress_text = ft.Text("0:00 / 0:00", size=9, color="#80ffffff")

    def format_time(seconds: float | None) -> str:
        if seconds is None or seconds < 0:
            return "0:00"
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

    subtitle_enabled_state: bool = False

    def on_subtitle_click(e):
        nonlocal subtitle_enabled_state
        subtitle_enabled_state = not subtitle_enabled_state
        
        # 1. Android TV Remote 経由で KEYCODE_CAPTIONS (175) を送信
        send_key(175)
        
        # 2. Chromecast CastClient 経由で字幕の表示状態をトグル切り替え (状態同期)
        if cast_client:
            actual_sub_state = cast_client.toggle_subtitles(enable=subtitle_enabled_state, language=config.preferred_language)
            subtitle_enabled_state = actual_sub_state
            
        subtitle_btn.bgcolor = "#8A2BE2" if subtitle_enabled_state else "#1C1C24"
        subtitle_btn.border = get_border_all(2 if subtitle_enabled_state else 1, "#00D2FF" if subtitle_enabled_state else "#33ffffff")
        page.update()

    subtitle_btn = ft.Container(
        content=ft.Text("CC", color="white", size=FS(10), weight=ft.FontWeight.BOLD),
        width=S(36),
        height=S(26),
        alignment=ft.alignment.Alignment.CENTER,
        border_radius=13,
        bgcolor="#1C1C24",
        border=get_border_all(1, "#33ffffff"),
        on_click=on_subtitle_click
    )

    def on_media_status_changed(status_info: Dict[str, Any]) -> None:
        logger.info(f"[UI_STATUS_RECEIVE] メディアステータス受信: Title={status_info.get('title')}, State={status_info.get('player_state')}")
        def update_ui():
            try:
                nonlocal current_duration
                title = status_info.get("title") or "Media Stopped"
                artist = status_info.get("artist") or status_info.get("album_name") or "Device Connected"
                album_art = status_info.get("album_art") or status_info.get("images")
                
                media_title.value = title
                media_artist.value = artist
                
                if album_art:
                    art_url = album_art[0] if isinstance(album_art, list) and len(album_art) > 0 else album_art
                    if isinstance(art_url, str) and art_url.startswith("http"):
                        media_art.src = art_url
                
                duration = status_info.get("duration")
                current_time = status_info.get("current_time")
                
                if duration and duration > 0:
                    current_duration = float(duration)
                
                player_state = status_info.get("player_state")
                is_media_stopped = player_state in ("IDLE", "STOPPED", "UNKNOWN") or title == "Media Stopped"

                if is_media_stopped:
                    progress_bar.disabled = True
                    progress_bar.value = 0.0
                    progress_bar.max = 100.0
                    progress_text.value = "0:00 / 0:00"
                else:
                    progress_bar.disabled = False
                    # ユーザーが操作（ドラッグ）中でなく、かつ直近2.5秒以内にリモコンキーでのシークをしていない場合のみ、実機状態と同期
                    if not is_slider_dragging and time.time() - last_user_seek_time > 2.5:
                        if duration and duration > 0 and current_time is not None:
                            progress_bar.max = float(duration)
                            progress_bar.value = min(float(duration), max(0.0, float(current_time)))
                            progress_text.value = f"{format_time(current_time)} / {format_time(duration)}"
                        else:
                            progress_bar.value = 0.0
                            progress_bar.max = 100.0
                            progress_text.value = "0:00 / 0:00"

                if player_state == "PLAYING":
                    cast_play.content.value = "⏸"
                else:
                    cast_play.content.value = "▶"

                sub_enabled = status_info.get("subtitles_enabled", False)
                subtitle_btn.bgcolor = "#8A2BE2" if sub_enabled else "#1C1C24"
                subtitle_btn.border = get_border_all(2 if sub_enabled else 1, "#00D2FF" if sub_enabled else "#33ffffff")

                page.update()
            except Exception as ex:
                logger.error(f"Media status UI update error: {ex}")

        if loop and loop.is_running():
            loop.call_soon_threadsafe(update_ui)
        else:
            # ループがNoneまたは停止中の場合は同期直接実行 (フォールバック)
            try:
                update_ui()
            except Exception as ex:
                logger.error(f"Direct update_ui error: {ex}")

    cast_client.on_status_changed = on_media_status_changed







    def run_cast_action(action: str) -> None:
        try:
            if cast_client and cast_client.cast:
                if action == "PLAY_PAUSE":
                    cast_client.toggle_play_pause()
                elif action == "PREV":
                    cast_client.prev()
                elif action == "NEXT":
                    cast_client.next()
                elif action == "STOP":
                    cast_client.stop()
            else:
                show_error("Cast feature is not connected.")
        except Exception as ex:
            logger.error(f"Cast action error ({action}): {ex}")


    def create_media_btn(label: str, name: str, size: int = 14, color: str = "white", bgcolor: str = "#1C1C24", width: int = 36) -> ft.Container:
        btn_container = ft.Container(
            content=ft.Text(label, color=color, size=size, weight=ft.FontWeight.BOLD),
            width=width,
            height=36,
            alignment=ft.alignment.Alignment.CENTER,
            border_radius=18,
            bgcolor=bgcolor,
            border=get_border_all(1, "#33ffffff"),
            on_click=lambda e: run_cast_action(name)
        )
        return btn_container

    cast_prev = create_media_btn("⏮", "PREV", size=12, color="white")
    cast_play = create_media_btn("▶", "PLAY_PAUSE", size=16, color="#8A2BE2", bgcolor="#1C1C24")
    cast_next = create_media_btn("⏭", "NEXT", size=12, color="white")

    media_info = ft.Row(
        [
            media_art,
            ft.Column(
                [
                    media_title,
                    media_artist
                ],
                spacing=1,
                expand=True
            ),
            subtitle_btn
        ],
        spacing=8,
        expand=True
    )

    bottom_media_panel = GlassCard(
        content=ft.Column(
            [
                ft.Row([media_info]),
                ft.Column(
                    [
                        progress_bar,
                        ft.Row([progress_text], alignment=ft.MainAxisAlignment.END)
                    ],
                    spacing=2
                ),
                ft.Row(
                    [cast_prev, cast_play, cast_next, subtitle_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12
                )
            ],
            spacing=8
        )
    )

    # 優先言語ドロップダウン
    lang_label = ft.Text("Preferred Language (キャスト開始時優先言語):", color="#b3ffffff", size=FS(FONT_SIZE_LABEL))

    def on_language_change(e):
        val = e.control.value
        config.preferred_language = val
        show_info(f"優先言語を更新しました: {val}")
        if cast_client and cast_client.cast:
            cast_client.apply_preferred_language(val)

    language_dropdown = ft.Dropdown(
        value=config.preferred_language,
        options=[
            ft.dropdown.Option("ja", "日本語 (Japanese)"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("zh", "中文 (Chinese)"),
            ft.dropdown.Option("ko", "한국語 (Korean)"),
            ft.dropdown.Option("off", "Off / デフォルト")
        ],
        content_padding=5,
        text_size=FS(10),
        border_color="#8A2BE2",
        bgcolor="#1C1C24"
    )
    language_dropdown.on_change = on_language_change

    # ⚙️ 設定 & 検出されたデバイスのアコーディオン
    settings_accordion = ft.ExpansionTile(
        title=ft.Row(
            [
                settings_accordion_title,
                progress_ring
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        subtitle=status_text,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row([size_label], alignment=ft.MainAxisAlignment.START),
                        size_slider,
                        ft.Row([opacity_label], alignment=ft.MainAxisAlignment.START),
                        opacity_slider,
                        ft.Row([lang_label], alignment=ft.MainAxisAlignment.START),
                        language_dropdown,
                        ft.Divider(color="#19ffffff", height=1),
                        ft.Row([discovered_devices_label, refresh_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        devices_panel
                    ],
                    spacing=4
                ),
                padding=8,
                bgcolor="#14141B",
                border_radius=8
            )
        ]
    )

    # 9. レイアウト構築関数
    def build_main_layout():
        dpad_panel = ft.Column(
            [
                ft.Row([Spacer60(), DPadBtn("▲", "UP"), Spacer60()], alignment=ft.MainAxisAlignment.CENTER, spacing=S(15)),
                ft.Row([DPadBtn("◀", "LEFT"), DPadCenterBtn(), DPadBtn("▶", "RIGHT")], alignment=ft.MainAxisAlignment.CENTER, spacing=S(15)),
                ft.Row([Spacer60(), DPadBtn("▼", "DOWN"), Spacer60()], alignment=ft.MainAxisAlignment.CENTER, spacing=S(15)),
            ],
            spacing=S(10)
        )

        # 要望5: 戻る(⏎) と 再生/一時停止(⏯) を方向キーと同サイズ (base_size=60) で横並び配置
        back_play_row = ft.Row(
            [
                ActionBtn("⏎", "BACK", base_size=60),
                ActionBtn("⏯", "PLAY_PAUSE", color="#30D158", base_size=60)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=S(15)
        )

        # 要望6: HOME(🏠) と 電源(⏻) を現在と同サイズ (base_size=46) で横並び配置
        power_home_row = ft.Row(
            [
                ActionBtn("⏻", "POWER", color="#FF453A", base_size=46),
                ActionBtn("🏠", "HOME", base_size=46)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=S(15)
        )

        volume_row = ft.Row(
            [
                ActionBtn("🔉", "VOLUME_DOWN", base_size=46),
                ActionBtn("🔇", "MUTE", color="#FFCC00", base_size=46),
                ActionBtn("🔊", "VOLUME_UP", base_size=46)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=S(12)
        )

        action_buttons = ft.Column(
            [
                power_home_row,
                volume_row,
                back_play_row
            ],
            spacing=S(10),
            alignment=ft.MainAxisAlignment.CENTER
        )

        remote_panel = ft.Row([dpad_panel, action_buttons], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

        apps_accordion = ft.ExpansionTile(
            title=apps_accordion_title,
            controls=[
                ft.Container(
                    content=ft.Row(
                        [
                            AppBtn("YouTube", "🔴", "#FF0000", "com.google.android.youtube.tv"),
                            AppBtn("Netflix", "🎬", "#E50914", "com.netflix.ninja"),
                            AppBtn("Prime Video", "💙", "#00A8E1", "com.amazon.amazonvideo.livingroom"),
                            AppBtn("Spotify", "🎵", "#1DB954", "com.spotify.tv.android"),
                            AppBtn("Google TV", "📺", "#4285F4", "com.google.android.apps.tv.launcherx")
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_EVENLY
                    ),
                    padding=6,
                    bgcolor="#14141B",
                    border_radius=8
                )
            ]
        )

        return ft.Column(
            [
                header_row,
                remote_panel,
                apps_accordion,
                bottom_media_panel,
                ft.Divider(color="#19ffffff", height=S(4)),
                settings_accordion
            ],
            spacing=S(6),
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

    main_layout = build_main_layout()

    # グローバルキーボードイベントをフックするため、KeyboardListenerをルートにする
    root_listener = ft.KeyboardListener(
        on_key_down=on_key_down,
        on_key_up=on_key_up,
        autofocus=True,
        content=main_layout,
        expand=True
    )

    # 全画面ビビッド・ダークネオングラデーション背景
    background_gradient = ft.LinearGradient(
        begin=ft.alignment.Alignment.TOP_LEFT,
        end=ft.alignment.Alignment.BOTTOM_RIGHT,
        colors=["#3B0D66", "#0D325E", "#050C1A"],
        stops=[0.0, 0.5, 1.0]
    )

    root_wrapper = ft.Container(
        content=root_listener,
        gradient=background_gradient,
        expand=True,
        margin=-15,
        padding=15
    )

    page.add(root_wrapper)
    page.update()

    # UIの初回レンダリングが完了した後にトラッカーを起動
    if tracker:
        tracker.start()

    # 接続監視タスクとシステム休止復旧監視タスクの開始
    async def monitor_system_resume():
        """時間のギャップを監視し、スリープ/休止状態からの復旧を検知して再接続を試みます。"""
        logger.info("[RESUME_MONITOR] 休止復旧監視タスクを開始しました。")
        last_time = time.time()
        while True:
            await asyncio.sleep(3)
            now = time.time()
            # 3秒待機したはずなのに、10秒以上経過していた場合はスリープからの復旧とみなす
            if now - last_time > 10.0:
                logger.warning(f"[RESUME_MONITOR] システム休止復旧を検知しました (時間のギャップ: {now - last_time:.2f}秒)。")
                show_info("休止状態からの復旧を検知しました。ネットワークとデバイスの再接続を開始します...")
                
                # 1. 探索サービス (tracker) のリスタートを完全別スレッドで実行 (UIフリーズ防止)
                try:
                    if tracker:
                        logger.info("[RESUME_MONITOR] 探索サービス(Zeroconf)を別スレッドで再起動します。")
                        await asyncio.to_thread(tracker.stop)
                        await asyncio.sleep(1.5)
                        await asyncio.to_thread(tracker.start)
                except Exception as e:
                    logger.error(f"[RESUME_MONITOR] 探索サービスの再起動エラー: {e}")

                # 2. 切断処理（古い接続リソースを確実に掃除）を完全別スレッドで実行
                try:
                    if remote_client:
                        await asyncio.to_thread(remote_client.disconnect)
                    if cast_client:
                        await asyncio.to_thread(cast_client.disconnect)
                except Exception as e:
                    logger.error(f"[RESUME_MONITOR] 切断クリーンアップエラー: {e}")
                
                status_text.value = "Status: Reconnecting..."
                status_text.color = "#FFCC00"
                page.update()

                # 3. ネットワーク復帰を待つためのウェイト
                await asyncio.sleep(3.5)

                # 4. 自動再接続試行 (force=True を指定してデッドソケットを強制破棄)
                if config.last_device_id and config.last_device_ip:
                    logger.info(f"[RESUME_MONITOR] 前回接続デバイスへ強制再接続をキックします: IP={config.last_device_ip}")
                    asyncio.create_task(connect_to_device(config.last_device_id, config.last_device_ip, force=True))
            
            last_time = now

    async def connection_monitor_loop():
        """定期的に接続状態を監視し、切断されている場合は自動的に再接続を試みます。"""
        logger.info("[CONN_MONITOR] 接続監視タスクを開始しました。")
        while True:
            await asyncio.sleep(15) # 15秒ごとに監視
            
            if config.last_device_id and config.last_device_ip:
                is_remote_connected = remote_client and remote_client.is_connected
                
                # pychromecast のソケットクライアント接続状態を安全にチェック
                is_cast_connected = False
                if cast_client and cast_client.cast:
                    sc = getattr(cast_client.cast, "socket_client", None)
                    if sc and hasattr(sc, "is_connected"):
                        try:
                            is_cast_connected = sc.is_connected
                        except Exception:
                            pass
                
                if not is_remote_connected or not is_cast_connected:
                    logger.info(f"[CONN_MONITOR] 接続の切断を検出しました（Remote={is_remote_connected}, Cast={is_cast_connected}）。再接続を試みます...")
                    
                    # 接続処理中のステータスであれば二重にキックしない
                    if status_text.value and "Connecting" in status_text.value:
                        logger.info("[CONN_MONITOR] 現在接続処理中のため、自動再接続のキックを見送ります。")
                        continue
                        
                    asyncio.create_task(connect_to_device(config.last_device_id, config.last_device_ip))

    async def media_status_poll_loop():
        """Chromecast 接続中、定期的に (3秒ごと) メディアステータスの更新要求を送り、メディア情報を画面へリアルタイム同期します。"""
        logger.info("[MEDIA_POLL] メディアステータス定期同期タスクを開始しました。")
        while True:
            await asyncio.sleep(3)
            try:
                if cast_client and cast_client.cast:
                    sc = getattr(cast_client.cast, "socket_client", None)
                    if sc and hasattr(sc, "is_connected") and sc.is_connected:
                        mc = getattr(cast_client.cast, "media_controller", None)
                        if mc and hasattr(mc, "update_status"):
                            # メインUIスレッドをブロックしないよう to_thread で呼び出し、かつタイムアウト保護 (2.0秒) を適用
                            try:
                                await asyncio.wait_for(asyncio.to_thread(mc.update_status), timeout=2.0)
                            except asyncio.TimeoutError:
                                logger.warning("[MEDIA_POLL] update_status がタイムアウトしました。ソケットがハングしている可能性があります。")
            except Exception as ex:
                logger.debug(f"[MEDIA_POLL] ステータス要求例外 (無視可): {ex}")

    asyncio.create_task(monitor_system_resume())
    asyncio.create_task(connection_monitor_loop())
    asyncio.create_task(media_status_poll_loop())

    # 10. クローズハンドラでのリソースクリーンアップ（決定論的切断フック）
    def on_window_disconnect(e: ft.ControlEvent) -> None:
        logger.info("[SHUTDOWN] Flet connection disconnected. Invoking os._exit(0)...")
        for h in root_logger.handlers:
            try:
                h.flush()
            except Exception:
                pass
        import os
        os._exit(0)

    page.on_disconnect = on_window_disconnect

    # 11. スタートアップ時の自動再接続処理
    if config.last_device_id and config.last_device_ip:
        logger.info(f"起動時自動再接続を試みます: {config.last_device_name} ({config.last_device_ip})")
        # 前回の接続デバイスを初期表示としてチップ追加
        chip = create_device_chip(config.last_device_name, config.last_device_ip, config.last_device_id)
        chip.key = config.last_device_id
        devices_panel.controls.append(chip)
        page.update()

        # 自動接続をキック (初期状態のため force=True で確実にコールバックを紐付け直す)
        asyncio.create_task(connect_to_device(config.last_device_id, config.last_device_ip, force=True))

    # 決定論的クローズフック（Flutter UI切断時に確実に os._exit(0) を実行）
    def on_window_disconnect(e: ft.ControlEvent) -> None:
        logger.info("[SHUTDOWN] Flet connection disconnected. Invoking os._exit(0)...")
        import os
        os._exit(0)

    page.on_disconnect = on_window_disconnect



if __name__ == "__main__":
    prevent_multiple_instances(config.lock_port)
    ft.app(target=main)




