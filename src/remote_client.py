import logging
from typing import Dict, Optional

from androidtvremote2.androidtv_remote import AndroidTVRemote
from androidtvremote2.exceptions import CannotConnect, ConnectionClosed, InvalidAuth

# ロガーのセットアップ
logger = logging.getLogger(__name__)

# ライブラリの対応文字列にマッピングするキーコード定数辞書（毎回の関数呼び出しでの再生成を回避）
KEY_MAP: Dict[str, str] = {
    "UP": "DPAD_UP",
    "DOWN": "DPAD_DOWN",
    "LEFT": "DPAD_LEFT",
    "RIGHT": "DPAD_RIGHT",
    "ENTER": "DPAD_CENTER",
    "BACK": "BACK",
    "HOME": "HOME",
    "PLAY_PAUSE": "MEDIA_PLAY_PAUSE",
    "FAST_FORWARD": "MEDIA_FAST_FORWARD",
    "REWIND": "MEDIA_REWIND",
    "CAPTIONS": "CAPTIONS",
    "CC": "CAPTIONS",
    "VOLUME_UP": "VOLUME_UP",
    "VOLUME_DOWN": "VOLUME_DOWN",
    "MUTE": "VOLUME_MUTE",
    "ASSIST": "ASSIST",
    "SEARCH": "SEARCH"
}

class PairingRequiredException(Exception):
    """デバイス接続時にペアリング（認証キーの取得）が必要であることを示す例外。"""
    pass

class AndroidTVRemoteClient:
    """androidtvremote2.AndroidTVRemote をラッピングした非同期クライアントクラス。
    
    Android TV / Google TV デバイスとの接続、ペアリング、キー送信、アプリ起動、
    および再接続の管理を行います。
    """

    def __init__(
        self,
        ip: str,
        certfile: str,
        keyfile: str,
        client_name: str = "GoogleTVRemoteApp"
    ) -> None:
        """AndroidTVRemoteClient を初期化します。
        
        Args:
            ip: 対象 Android TV のIPアドレス。
            certfile: SSL証明書(cert.pem)の絶対パス。
            keyfile: SSL秘密鍵(key.pem)の絶対パス。
            client_name: 接続クライアントとしてテレビ側に表示される名前。
        """
        self.ip = ip
        self.certfile = certfile
        self.keyfile = keyfile
        self.client_name = client_name
        self.remote: Optional[AndroidTVRemote] = None
        self._is_pairing: bool = False

    async def connect(self) -> None:
        """デバイスへの接続を確立します。
        
        ペアリングされていない場合は、PairingRequiredException を発生させます。
        
        Raises:
            PairingRequiredException: ペアリングが完了していないか、再ペアリングが必要な場合。
            CannotConnect: ネットワークエラーなどで接続できない場合。
            ConnectionClosed: 接続が途中で切断された場合。
        """
        self.disconnect()

        logger.info(f"Android TV Remote 接続試行中: {self.ip}")
        self.remote = AndroidTVRemote(
            client_name=self.client_name,
            certfile=self.certfile,
            keyfile=self.keyfile,
            host=self.ip
        )

        # 証明書ファイルが存在しない場合は自動生成します
        await self.remote.async_generate_cert_if_missing()

        try:
            await self.remote.async_connect()
            logger.info(f"Android TV Remote 接続成功: {self.ip}")
        except InvalidAuth as e:
            logger.warning(f"認証エラー（ペアリングが必要です）: {e}")
            raise PairingRequiredException("Pairing is required for this device.") from e
        except CannotConnect as e:
            logger.error(f"接続失敗: {e}")
            raise e
        except ConnectionClosed as e:
            logger.error(f"接続切断: {e}")
            raise e

    def disconnect(self) -> None:
        """現在の接続を切断し、リソースを解放します。"""
        if self.remote:
            try:
                self.remote.disconnect()
                logger.info("Android TV Remote 切断完了")
            except Exception as e:
                logger.debug(f"切断中のエラー（無視可能）: {e}")
            finally:
                self.remote = None

    async def start_pairing(self) -> None:
        """ペアリングプロセスを開始します。
        
        テレビの画面上に6桁のPINコードが表示されます。
        
        Raises:
            CannotConnect: ペアリング用のポート（通常6467）に接続できない場合。
        """
        self.disconnect()

        logger.info(f"ペアリング開始試行中: {self.ip}")
        self.remote = AndroidTVRemote(
            client_name=self.client_name,
            certfile=self.certfile,
            keyfile=self.keyfile,
            host=self.ip
        )

        await self.remote.async_generate_cert_if_missing()
        await self.remote.async_start_pairing()
        self._is_pairing = True
        logger.info("ペアリング要求を送信しました。テレビ画面のPINを確認してください。")

    async def send_pin(self, pin: str) -> None:
        """ユーザーが入力した6桁のPINコードを送信し、ペアリングを完了させます。
        
        ペアリング成功後、自動的にコマンド用の接続チャネルを確立します。
        
        Args:
            pin: テレビ画面に表示された6桁の文字列。
        """
        if not self.remote or not self._is_pairing:
            raise RuntimeError("ペアリングが開始されていません。先に start_pairing() を実行してください。")

        logger.info(f"PINコード送信中: {pin}")
        try:
            await self.remote.async_finish_pairing(pin)
            self._is_pairing = False
            logger.info("ペアリング認証成功")
            
            # ペアリング完了後はポート6467（ペアリング用）が切断されるため、
            # ポート6466（コマンド用）に再接続します。
            await self.connect()
        except InvalidAuth as e:
            logger.error("PINコードが正しくないか、タイムアウトしました。")
            raise e
        except Exception as e:
            logger.error(f"ペアリング完了処理中にエラーが発生しました: {e}")
            raise e

    async def send_key(self, key_code_name: str, direction: str = "SHORT") -> None:
        """キー入力をデバイスに送信します。
        
        Args:
            key_code_name: "UP", "DOWN", "LEFT", "RIGHT", "ENTER", "BACK", "HOME", 
                           "PLAY_PAUSE", "VOLUME_UP", "VOLUME_DOWN", "MUTE" などのキー名。
            direction: 押下タイプ。"SHORT"（短押し）, "START_LONG"（長押し開始）, "END_LONG"（長押し終了）。
        """
        if not self.remote:
            raise RuntimeError("クライアントが接続されていません。")

        # 大文字に正規化
        key_upper = key_code_name.upper()
        mapped_key = KEY_MAP.get(key_upper, key_upper)

        # 押下方向 (direction) の設定
        dir_upper = direction.upper() if isinstance(direction, str) else direction
        if dir_upper == "LONG":
            dir_upper = "START_LONG"
        if dir_upper not in ("SHORT", "START_LONG", "END_LONG"):
            raise ValueError(f"無効な direction です: {direction} (SHORT, START_LONG, END_LONG のいずれかを指定してください)")

        logger.debug(f"キー送信: {mapped_key} ({dir_upper})")
        # send_key_command は非ブロッキングでバッファリング送信されます
        self.remote.send_key_command(mapped_key, dir_upper)


    async def send_text(self, text: str) -> None:
        """指定されたテキストを Android TV の入力フィールドに送信します。
        
        Args:
            text: 送信する文字列。
        """
        if not self.remote:
            raise RuntimeError("クライアントが接続されていません。")
        logger.info(f"テキスト送信: {text}")
        self.remote.send_text(text)

    async def launch_app(self, app_link: str) -> None:
        """ディープリンク（またはパッケージ名）を使用してアプリを起動します。
        
        Args:
            app_link: 起動したいアプリのディープリンク（例: "https://www.youtube.com"）
                      またはアプリID。
        """
        if not self.remote:
            raise RuntimeError("クライアントが接続されていません。")

        logger.info(f"アプリ起動コマンド送信: {app_link}")
        self.remote.send_launch_app_command(app_link)

    async def update_ip_and_reconnect(self, new_ip: str) -> None:
        """IPアドレスを更新し、新しいIPに対して接続を再試行します（手動再接続用）。
        
        mDNSデバイス追跡などによりデバイスのIPアドレス変更を検出した際に呼び出されます。
        
        Args:
            new_ip: 新しいIPアドレス。
        """
        if self.ip == new_ip and self.is_connected:
            logger.debug("同じIPアドレスで既に接続されているため再接続をスキップします。")
            return

        logger.info(f"IPアドレス変更による再接続: {self.ip} -> {new_ip}")
        self.ip = new_ip
        await self.connect()

    @property
    def is_connected(self) -> bool:
        """現在接続状態である（接続ロスFutureが完了していない）かどうかを判定します。"""
        if not self.remote:
            return False
        # 内部プロトコルの有無と、その切断フューチャーが未完了かチェック
        proto = getattr(self.remote, "_remote_message_protocol", None)
        if not proto:
            return False
        return not proto.on_con_lost.done()

    def _on_invalid_auth(self) -> None:
        """自動再接続ループ内で認証無効が発生した際のコールバック。"""
        logger.error("自動再接続中に認証情報が無効になりました。再ペアリングが必要です。")
        self.disconnect()
