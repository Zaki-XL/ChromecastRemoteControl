import logging
import socket
import threading
from typing import Callable, Dict, List, Optional
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo

# ロガーのセットアップ
logger = logging.getLogger(__name__)

class AndroidTVTracker(ServiceListener):
    """Zeroconfを使用してローカルネットワーク上のAndroid TVデバイスを探索・追跡するクラス。
    
    _androidtvremote2._tcp.local. サービスタイプを監視し、
    デバイスの追加、更新、削除を追跡します。また、IPアドレスが変更された場合に
    指定されたコールバック関数をトリガーします。
    """

    def __init__(
        self, 
        on_ip_changed: Optional[Callable[[str, str], None]] = None,
        on_device_discovered: Optional[Callable[[Dict], None]] = None
    ) -> None:
        """AndroidTVTracker を初期化します。
        
        Args:
            on_ip_changed: IPアドレスが変更されたときに呼び出されるコールバック関数。
                           引数は (device_id, new_ip) です。
            on_device_discovered: 新しいデバイスが検出されたときに呼び出されるコールバック関数。
                                  引数はデバイス情報の辞書です。
        """
        self.on_ip_changed = on_ip_changed
        self.on_device_discovered = on_device_discovered
        self.devices: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.zeroconf: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        self.service_type = "_androidtvremote2._tcp.local."

    def start(self) -> None:
        """デバイスの探索 (ServiceBrowser) を開始します。"""
        with self.lock:
            if self.zeroconf is None:
                self.zeroconf = Zeroconf()
            if self.browser is None:
                self.browser = ServiceBrowser(self.zeroconf, self.service_type, self)
                logger.info(f"Android TV 探索サービスを開始しました (タイプ: {self.service_type})")

    def stop(self) -> None:
        """デバイスの探索を停止し、Zeroconfの接続およびスレッドなどのリソースをクローズします。"""
        with self.lock:
            if self.browser:
                self.browser.cancel()
                self.browser = None
            if self.zeroconf:
                self.zeroconf.close()
                self.zeroconf = None
            logger.info("Android TV 探索サービスを停止しました。")

    def get_ip_by_id(self, device_id: str) -> Optional[str]:
        """デバイスID（ユニークなIDまたはサービス名）を指定して、現在のIPアドレスを取得します。
        
        Args:
            device_id: 追跡対象のデバイスID。
            
        Returns:
            str: 現在のIPアドレス（発見されていない場合は None）。
        """
        with self.lock:
            device = self.devices.get(device_id)
            return device.get('ip') if device else None

    def list_devices(self) -> List[Dict]:
        """現在検出されているすべての Android TV デバイスの情報をリスト形式で取得します。
        
        Returns:
            List[Dict]: デバイス情報の辞書のリスト。
                        各辞書には 'device_id', 'name', 'ip', 'port', 'friendly_name' 等が含まれます。
        """
        with self.lock:
            return list(self.devices.values())

    def _handle_service_event(self, zc: Zeroconf, type_: str, name: str, event_type: str) -> None:
        """サービスの追加・更新イベントを共通処理します。"""
        logger.debug(f"Service {event_type}: {name}")
        info = zc.get_service_info(type_, name)
        if info:
            self._process_service_info(name, info)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Zeroconfで新しいサービスが追加されたときに呼び出されます。"""
        self._handle_service_event(zc, type_, name, "added")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Zeroconfで既存のサービス情報が更新されたときに呼び出されます。"""
        self._handle_service_event(zc, type_, name, "updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Zeroconfでサービスが削除（オフライン）されたときに呼び出されます。"""
        logger.info(f"Service removed: {name}")
        with self.lock:
            # サービス名が一致するデバイスを検索して削除します
            target_id = None
            for dev_id, dev_info in self.devices.items():
                if dev_info.get('name') == name:
                    target_id = dev_id
                    break
            
            if target_id:
                del self.devices[target_id]
                logger.info(f"デバイスを追跡リストから削除しました: ID={target_id}")

    def _process_service_info(self, name: str, info: ServiceInfo) -> None:
        """ServiceInfo からデバイス情報を解析し、内部のデバイスリストを更新します。
        IPアドレスが変更された場合は、コールバックをトリガーします。
        """
        # IPアドレスの抽出（parsed_addresses 優先、古いzeroconf向けに addresses もサポート）
        ip = None
        if hasattr(info, 'parsed_addresses') and info.parsed_addresses():
            ip = info.parsed_addresses()[0]
        elif info.addresses:
            ip = socket.inet_ntoa(info.addresses[0])

        if not ip:
            logger.warning(f"サービス名 {name} のIPアドレスを解決できませんでした。")
            return

        # TXT レコードの解析 (キー・値ともに文字列に変換)
        properties = {}
        for k, v in info.properties.items():
            try:
                key_str = k.decode('utf-8', errors='ignore')
                val_str = v.decode('utf-8', errors='ignore') if v is not None else ""
                properties[key_str] = val_str
            except Exception as e:
                logger.debug(f"TXT レコードのデコードに失敗しました: {e}")

        # サービス名からプレフィックス部分を取り出し、デフォルトのIDや名称に使用する
        if name.endswith(self.service_type):
            name_fallback = name[:-len(self.service_type)].rstrip('.')
        else:
            name_fallback = name

        # デバイスIDの決定: TXTレコードの 'id' または 'bt' を優先し、無ければ fallback を使用
        device_id = properties.get('id') or properties.get('bt') or name_fallback
        friendly_name = properties.get('fn') or name_fallback
        port = info.port

        with self.lock:
            old_device = self.devices.get(device_id)
            
            # デバイス情報を更新
            self.devices[device_id] = {
                'device_id': device_id,
                'name': name,
                'ip': ip,
                'port': port,
                'friendly_name': friendly_name,
                'properties': properties
            }

            # すでに登録されているデバイスのIPアドレスが更新されたかチェック
            if old_device:
                old_ip = old_device.get('ip')
                if old_ip != ip:
                    logger.info(f"デバイス IP 変更検出: ID={device_id}, 旧={old_ip}, 新={ip}")
                    if self.on_ip_changed:
                        # 呼び出し元のメインスレッドや探索スレッドをブロックしないよう、
                        # コールバック処理はデーモンスレッド上で非同期実行します。
                        threading.Thread(
                            target=self._trigger_ip_changed_callback,
                            args=(device_id, ip),
                            daemon=True
                        ).start()
            else:
                logger.info(f"新しいデバイスを発見しました: ID={device_id}, IP={ip}, Name={friendly_name}")
                if self.on_device_discovered:
                    device_info = self.devices[device_id]
                    threading.Thread(
                        target=self._trigger_device_discovered_callback,
                        args=(device_info,),
                        daemon=True
                    ).start()

    def _trigger_ip_changed_callback(self, device_id: str, new_ip: str) -> None:
        """安全にコールバック関数を実行します。"""
        try:
            if self.on_ip_changed:
                self.on_ip_changed(device_id, new_ip)
        except Exception as e:
            logger.error(f"on_ip_changed コールバック実行中にエラーが発生しました: {e}", exc_info=True)

    def _trigger_device_discovered_callback(self, device_info: Dict) -> None:
        """安全にデバイス発見コールバック関数を実行します。"""
        try:
            if self.on_device_discovered:
                self.on_device_discovered(device_info)
        except Exception as e:
            logger.error(f"on_device_discovered コールバック実行中にエラーが発生しました: {e}", exc_info=True)
