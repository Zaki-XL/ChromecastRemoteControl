import os
import sys
import configparser
from typing import Tuple

# 実行環境がPyInstallerによってパッケージ化されているかどうかに応じて、
# 適切なベースディレクトリを決定します。
if getattr(sys, 'frozen', False):
    # PyInstallerでパッケージ化された実行ファイルの場合
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 通常のPythonスクリプト実行の場合（src/ の親フォルダー＝プロジェクトルート）
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 設定ファイルおよび証明書ディレクトリのパスを設定します
CONFIG_PATH = os.path.join(BASE_DIR, 'config.ini')
CERTS_DIR = os.path.join(BASE_DIR, 'certs')

class ConfigManager:
    """設定情報 (config.ini) および SSL 証明書のパスを管理するクラス。
    
    Android TV Remote接続に必要な設定のロード、セーブ、初期化、
    および証明書のディレクトリ管理機能を提供します。
    """
    
    SECTION_DEVICE = 'Device'
    SECTION_WINDOW = 'Window'
    SECTION_SERVER = 'Server'
    SECTION_MEDIA = 'Media'

    # デフォルト設定値の一元管理定義（重複定義の防止）
    DEFAULT_CONFIG = {
        'Device': {
            'last_device_id': '',
            'last_device_name': '',
            'last_device_ip': ''
        },
        'Window': {
            'width': '420',
            'height': '750',
            'opacity': '1.0',
            'enable_logging': 'false'
        },
        'Server': {
            'lock_port': '64660'
        },
        'Media': {
            'preferred_language': 'ja'
        }
    }
    
    def __init__(self) -> None:
        """ConfigManager を初期化し、必要なディレクトリの作成と設定のロードを行います。"""
        self.config = configparser.ConfigParser()
        self._ensure_certs_dir()
        self.load()

    def _ensure_certs_dir(self) -> None:
        """SSL証明書用のディレクトリ 'certs/' が存在しない場合は作成します。"""
        os.makedirs(CERTS_DIR, exist_ok=True)

    def get_cert_paths(self) -> Tuple[str, str]:
        """androidtvremote2 に渡すための SSL 証明書(cert.pem)と秘密鍵(key.pem)の絶対パスを返します。
        
        Returns:
            Tuple[str, str]: (cert_pemの絶対パス, key_pemの絶対パス)
        """
        cert_path = os.path.abspath(os.path.join(CERTS_DIR, 'cert.pem'))
        key_path = os.path.abspath(os.path.join(CERTS_DIR, 'key.pem'))
        return cert_path, key_path

    def load(self) -> None:
        """config.ini から設定をロードします。
        
        ファイルが存在しない場合や破損している場合は、デフォルト値で初期設定ファイルを生成します。
        """
        if not os.path.exists(CONFIG_PATH):
            self.initialize_default()
            return

        try:
            self.config.read(CONFIG_PATH, encoding='utf-8')
            
            # 必要なセクションが存在しない場合は作成します
            for section in self.DEFAULT_CONFIG:
                if not self.config.has_section(section):
                    self.config.add_section(section)
            
            # 必要なキーが存在するかチェックし、存在しない場合はデフォルト値で補完します
            updated = False
            for section, defaults in self.DEFAULT_CONFIG.items():
                for key, val in defaults.items():
                    if not self.config.has_option(section, key):
                        self.config.set(section, key, val)
                        updated = True
            
            # 不足していた設定項目を追加した場合は保存します
            if updated:
                self.save()
        except Exception as e:
            # 読み込みエラーが発生した場合は堅牢性のためにデフォルト値で初期化します
            print(f"[Warning] 設定ファイルのロード中にエラーが発生したため初期化します: {e}", file=sys.stderr)
            self.initialize_default()

    def save(self) -> None:
        """現在のメモリ上の設定を config.ini ファイルへ保存します。"""
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"[Error] 設定ファイルの保存に失敗しました: {e}", file=sys.stderr)

    def initialize_default(self) -> None:
        """設定を初期デフォルト状態にし、config.ini に書き込みます。"""
        self.config.clear()
        for section, defaults in self.DEFAULT_CONFIG.items():
            self.config.add_section(section)
            for key, val in defaults.items():
                self.config.set(section, key, val)
        self.save()

    @property
    def last_device_id(self) -> str:
        """最後に接続に成功したデバイスのIDを取得します。"""
        return self.config.get(self.SECTION_DEVICE, 'last_device_id', fallback='')

    @last_device_id.setter
    def last_device_id(self, val: str) -> None:
        """最後に接続に成功したデバイスのIDを設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_DEVICE, 'last_device_id', val)
        self.save()

    @property
    def last_device_name(self) -> str:
        """最後に接続に成功したデバイスのフレンドリー名を取得します。"""
        return self.config.get(self.SECTION_DEVICE, 'last_device_name', fallback='')

    @last_device_name.setter
    def last_device_name(self, val: str) -> None:
        """最後に接続に成功したデバイスのフレンドリー名を設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_DEVICE, 'last_device_name', val)
        self.save()

    @property
    def last_device_ip(self) -> str:
        """最後に接続に成功したデバイスのIPアドレスを取得します。"""
        return self.config.get(self.SECTION_DEVICE, 'last_device_ip', fallback='')

    @last_device_ip.setter
    def last_device_ip(self, val: str) -> None:
        """最後に接続に成功したデバイスのIPアドレスを設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_DEVICE, 'last_device_ip', val)
        self.save()

    # --- Window セクション ---

    @property
    def window_width(self) -> int:
        """ウィンドウ幅を取得します。"""
        try:
            return int(self.config.get(self.SECTION_WINDOW, 'width', fallback='420'))
        except ValueError:
            return 420

    @window_width.setter
    def window_width(self, val: int) -> None:
        """ウィンドウ幅を設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_WINDOW, 'width', str(val))
        self.save()

    @property
    def window_height(self) -> int:
        """ウィンドウ高さを取得します。"""
        try:
            return int(self.config.get(self.SECTION_WINDOW, 'height', fallback='750'))
        except ValueError:
            return 750

    @window_height.setter
    def window_height(self, val: int) -> None:
        """ウィンドウ高さを設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_WINDOW, 'height', str(val))
        self.save()

    @property
    def window_opacity(self) -> float:
        """ウィンドウ透明度を取得します（0.0〜1.0）。"""
        try:
            v = float(self.config.get(self.SECTION_WINDOW, 'opacity', fallback='1.0'))
            return max(0.2, min(1.0, v))
        except ValueError:
            return 1.0

    @window_opacity.setter
    def window_opacity(self, val: float) -> None:
        """ウィンドウ透明度を設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_WINDOW, 'opacity', f'{val:.2f}')
        self.save()

    @property
    def enable_logging(self) -> bool:
        """デバッグログファイルへの出力有効状態を取得します（デフォルト: False）。"""
        return self.config.getboolean(self.SECTION_WINDOW, 'enable_logging', fallback=False)

    @enable_logging.setter
    def enable_logging(self, val: bool) -> None:
        """デバッグログファイルへの出力有効状態を設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_WINDOW, 'enable_logging', 'true' if val else 'false')
        self.save()

    # --- Server セクション ---

    @property
    def lock_port(self) -> int:
        """多重起動防止用のロックポート番号を取得します。"""
        try:
            return int(self.config.get(self.SECTION_SERVER, 'lock_port', fallback='64660'))
        except ValueError:
            return 64660

    @lock_port.setter
    def lock_port(self, val: int) -> None:
        """多重起動防止用のロックポート番号を設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_SERVER, 'lock_port', str(val))
        self.save()

    # --- Media セクション ---

    @property
    def preferred_language(self) -> str:
        """優先言語コード（例: 'ja', 'en'）を取得します。"""
        return self.config.get(self.SECTION_MEDIA, 'preferred_language', fallback='ja')

    @preferred_language.setter
    def preferred_language(self, val: str) -> None:
        """優先言語コードを設定し、即座にファイルに保存します。"""
        self.config.set(self.SECTION_MEDIA, 'preferred_language', val)
        self.save()
