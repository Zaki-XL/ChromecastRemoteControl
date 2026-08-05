import asyncio
import logging
import threading
from typing import Any, Callable, Dict, Optional

import pychromecast
from pychromecast.controllers.media import MediaStatus, MediaStatusListener

# ロガーのセットアップ
logger = logging.getLogger(__name__)

class ChromecastMediaListener(MediaStatusListener):
    """Chromecastのメディア再生状態の変更を監視し、コールバック関数を起動するリスナークラス。"""

    def __init__(self, callback: Callable[[MediaStatus], None]) -> None:
        """ChromecastMediaListener を初期化します。
        
        Args:
            callback: メディアステータス更新時に実行される内部コールバック。
        """
        self.callback = callback

    def new_media_status(self, status: MediaStatus) -> None:
        """新しいメディアステータスを受け取った際に呼び出されます。"""
        self.callback(status)

    def load_media_failed(self, queue_item_id: Any, error_code: int) -> None:
        """メディアのロード要求が失敗した際に呼び出されます。"""
        logger.error(f"メディアロードに失敗しました。 item_id={queue_item_id}, error_code={error_code}")


class ChromecastCastClient:
    """pychromecast をラッピングし、メディア再生制御およびステータス監視を提供するクラス。
    
    Flet GUI (asyncio) と pychromecast (独自Socketスレッド) の異なるスレッドモデル間で
    安全に状態同期を行えるよう設計されています。
    """

    def __init__(
        self,
        ip: str,
        on_status_changed: Optional[Callable[[Dict[str, Any]], None]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """ChromecastCastClient を初期化します。
        
        Args:
            ip: ChromecastデバイスのIPアドレス。
            on_status_changed: ステータス変更時に呼び出されるコールバック関数。
                               UI表示用に変換された辞書形式のステータスデータを受け取ります。
            loop: Flet GUIなどの asyncio 非同期イベントループ。省略された場合は現在の実行ループを使用します。
        """
        self.ip = ip
        self.on_status_changed = on_status_changed
        self.cast: Optional[pychromecast.Chromecast] = None
        self.listener: Optional[ChromecastMediaListener] = None
        
        # UI更新用のイベントループをキャプチャします
        try:
            self.loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """非同期コールバック実行に使用するイベントループを設定します。
        
        インスタンスが非同期コンテキストの外で初期化された場合等に、明示的にループを指定するために使用します。
        """
        self.loop = loop

    def connect(self, force: bool = False) -> None:
        # 既に同じIPに正常にソケット接続されている場合は重複接続を避けて既存の接続を維持（force=True時はバイパス）
        if not force and self.cast and self.ip:
            sc = getattr(self.cast, "socket_client", None)
            if sc and hasattr(sc, "is_connected") and sc.is_connected:
                host_ip = getattr(self.cast.cast_info, 'host', None) if hasattr(self.cast, 'cast_info') else None
                if host_ip == self.ip:
                    logger.info(f"既に Chromecast ({self.ip}) に接続されています。既存の接続を維持します。")
                    try:
                        if hasattr(self.cast.media_controller, "update_status"):
                            self.cast.media_controller.update_status()
                    except Exception:
                        pass
                    return

        self.disconnect()

        logger.info(f"Chromecast への接続を試みます (CastInfo直接構築): IP={self.ip}")
        try:
            self.cast = None
            if not self.ip:
                raise RuntimeError("接続先IPアドレスが指定されていません。")

            from pychromecast.models import CastInfo, HostServiceInfo
            
            # 手動で CastInfo オブジェクトを構築してIP直指定で直接接続 (mDNSの遅延を回避)
            cast_info = CastInfo(
                services={HostServiceInfo(self.ip, 8009)},
                uuid=None,
                model_name="Chromecast",
                friendly_name="Bedroom Cast",
                host=self.ip,
                port=8009,
                cast_type="cast",
                manufacturer="Google Inc."
            )
            
            self.cast = pychromecast.Chromecast(cast_info=cast_info)

            # ソケット接続の完了を待機 (タイムアウト5秒)
            self.cast.wait(timeout=5.0)
            
            # ソケットの生存状態を厳格チェック
            sc = getattr(self.cast, "socket_client", None)
            if not (sc and hasattr(sc, "is_connected") and sc.is_connected):
                raise RuntimeError(f"Chromecast ソケット接続が失敗しました: IP={self.ip}")

            logger.info(f"Chromecast 接続完了: {self.cast.name} ({self.cast.model_name})")
        except Exception as e:
            logger.error(f"Chromecast 接続処理中にエラーが発生しました: {e}")
            self.cast = None
            raise RuntimeError(f"Chromecast 接続失敗: {e}") from e

        # メディアステータスリスナーの登録
        self.listener = ChromecastMediaListener(self._handle_media_status_change)
        self.cast.media_controller.register_status_listener(self.listener)

        # 現在すでに取得済みのステータスがあれば、即座にUIへ即時同期 (ブロッキング通信を回避)
        try:
            if self.cast.media_controller.status:
                self._handle_media_status_change(self.cast.media_controller.status)
        except Exception as ex:
            logger.warning(f"初期メディアステータス同期中にエラー: {ex}")

    def disconnect(self) -> None:
        """現在の接続を切断し、リスナー等の登録を解除してクリーンアップします。"""
        if self.cast:
            logger.info("既存の Chromecast 接続を完全にクリーンアップします。")
            try:
                # 1. リスナーのクリーンアップ
                if self.listener and hasattr(self.cast, 'media_controller'):
                    mc = self.cast.media_controller
                    if hasattr(mc, '_status_listeners') and self.listener in mc._status_listeners:
                        try:
                            mc._status_listeners.remove(self.listener)
                        except Exception:
                            pass
                
                # 2. ソケットの強制的なクローズと同期スレッドの join
                sc = getattr(self.cast, "socket_client", None)
                if sc:
                    # ソケットスレッドの停止をリクエスト
                    if hasattr(sc, "stop"):
                        try:
                            sc.stop()
                        except Exception:
                            pass
                    # TCPソケットを直ちに強制close (ブロッキング状態を強制解放)
                    raw_socket = getattr(sc, "socket", None)
                    if raw_socket:
                        try:
                            raw_socket.close()
                        except Exception:
                            pass
                    # スレッド自体の完全終了を同期的に待機 (ゾンビ化の防止)
                    if isinstance(sc, threading.Thread):
                        try:
                            sc.join(timeout=1.0)
                        except Exception as e:
                            logger.debug(f"ソケットスレッドのjoin待機エラー: {e}")
                
                # 3. pychromecast公式の切断命令
                try:
                    self.cast.disconnect()
                except Exception:
                    pass
                logger.info("Chromecast 接続を切断しました。")
            except Exception as e:
                logger.error(f"切断処理中にエラーが発生しました: {e}")
            finally:
                self.cast = None
                self.listener = None

    def play(self) -> None:
        """メディアの再生を開始します。"""
        if self.cast and self.cast.media_controller:
            self.cast.media_controller.play()

    def pause(self) -> None:
        """メディアの再生を一時停止します。"""
        if self.cast and self.cast.media_controller:
            self.cast.media_controller.pause()

    def toggle_play_pause(self) -> None:
        """メディアの再生・一時停止をトグル切り替えします。"""
        if self.cast and self.cast.media_controller:
            status = self.cast.media_controller.status
            if status and status.player_state == "PLAYING":
                self.cast.media_controller.pause()
            else:
                self.cast.media_controller.play()

    def prev(self) -> None:
        """前のトラックへ戻る（または巻き戻し）コマンドを送信します。"""
        if self.cast and self.cast.media_controller:
            self.cast.media_controller.rewind()

    def next(self) -> None:
        """次のトラックへ進む（スキップ）コマンドを送信します。"""
        if self.cast and self.cast.media_controller:
            self.cast.media_controller.skip()

    def volume_up(self) -> None:
        """端末全体のボリュームを上げます。"""
        if self.cast:
            self.cast.volume_up()

    def volume_down(self) -> None:
        """端末全体のボリュームを下げます。"""
        if self.cast:
            self.cast.volume_down()

    def mute(self, status: bool) -> None:
        """端末全体の消音（ミュート）状態を設定します。
        
        Args:
            status: True でミュートON、False でミュート解除。
        """
        if self.cast:
            self.cast.set_volume_muted(status)

    def _run_in_thread(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """pychromecastのWaitResponse等によるブロッキングを回避するため、安全に別スレッドで実行します。"""
        def worker():
            try:
                func(*args, **kwargs)
            except Exception as ex:
                logger.error(f"Cast command execution error ({func.__name__}): {ex}")

        threading.Thread(target=worker, daemon=True).start()



    def toggle_subtitles(self, enable: Optional[bool] = None, language: str = "ja") -> bool:
        """字幕の表示・非表示を切り替えます。
        
        Args:
            enable: TrueでON、FalseでOFF、Noneでトグル切り替え。
            language: 有効化時に優先指定する言語コード。
            
        Returns:
            bool: 変更後の字幕ON状態 (True: ON, False: OFF)
        """
        if not (self.cast and self.cast.media_controller):
            return False

        mc = self.cast.media_controller
        status = mc.status
        active_ids = getattr(status, 'current_subtitle_tracks', []) or getattr(status, 'active_track_ids', []) or []
        is_active = bool(active_ids)
        target_state = (not is_active) if enable is None else enable

        try:
            if target_state:
                tracks = getattr(status, 'subtitle_tracks', []) or []
                match_id = None
                if tracks:
                    for t in tracks:
                        t_type = t.get('type') if isinstance(t, dict) else getattr(t, 'type', '')
                        t_lang = t.get('language') if isinstance(t, dict) else getattr(t, 'language', '')
                        t_id = t.get('trackId') if isinstance(t, dict) else getattr(t, 'track_id', None)

                        if str(t_type).upper() == "TEXT":
                            if language and language.lower() in str(t_lang).lower():
                                match_id = t_id
                                break
                            if match_id is None:
                                match_id = t_id

                if match_id is None:
                    match_id = 1

                logger.info(f"字幕ONコマンドを非同期スレッドで送信します (track_id: {match_id})")
                self._run_in_thread(mc.enable_subtitle, int(match_id))
                return True
            else:
                logger.info("字幕OFFコマンドを非同期スレッドで送信します")
                self._run_in_thread(mc.disable_subtitle)
                return False
        except Exception as ex:
            logger.error(f"字幕設定エラー: {ex}")
            return is_active

    def seek_relative(self, delta_seconds: float) -> Optional[float]:
        """現在の再生位置から指定秒数（例: +10, -10）のシークを安全に実行します。
        
        Returns:
            Optional[float]: 計算された最終目標シーク位置（秒）
        """
        try:
            if self.cast and self.cast.media_controller:
                mc = self.cast.media_controller
                status = mc.status
                current = getattr(status, 'current_time', 0) or 0
                duration = getattr(status, 'duration', 0) or 0

                target = max(0.0, current + delta_seconds)
                if duration > 0:
                    target = min(duration, target)

                logger.info(f"キャスト相対シーク実行: current={current:.1f}s -> target={target:.1f}s (delta={delta_seconds}s)")
                self._run_in_thread(mc.seek, target)
                return target
        except Exception as ex:
            logger.error(f"相対シーク実行エラー: {ex}")
        return None


    def apply_preferred_language(self, language_code: str) -> None:
        """優先言語の設定に従い、字幕またはトラックを適用します。"""
        if not language_code or language_code.lower() in ("off", "none", "auto"):
            return
        logger.info(f"キャスト開始時の優先言語を適用します: {language_code}")
        self.toggle_subtitles(enable=True, language=language_code)

    def stop(self) -> None:
        """メディアの再生を停止（STOP）します。"""
        if self.cast and self.cast.media_controller:
            logger.info("メディア停止(STOP)コマンドを非同期スレッドで送信します")
            self._run_in_thread(self.cast.media_controller.stop)

    def _handle_media_status_change(self, status: MediaStatus) -> None:
        """SocketClientの受信スレッドから呼び出され、受信した生ステータスを
        UI表示用のシンプルな辞書データに整形してコールバックを実行します。
        
        asyncio-friendly な設計に基づき、スレッドセーフにイベントループへタスクをスケジュールします。
        """
        try:
            if not status:
                return

            # アルバムアートURLの取得
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

            # IDLE / STOPPED 時の安全な状態クリア
            if player_state in ("IDLE", "STOPPED", "UNKNOWN"):
                playback_rate = 1.0

            # GUIが必要とする拡張メタデータスキーマに整形
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

            logger.debug(f"メディアステータス変化を受信: {status_data}")

            if self.on_status_changed:
                if self.loop and self.loop.is_running():
                    if asyncio.iscoroutinefunction(self.on_status_changed):
                        asyncio.run_coroutine_threadsafe(self.on_status_changed(status_data), self.loop)
                    else:
                        self.loop.call_soon_threadsafe(self.on_status_changed, status_data)
                else:
                    try:
                        if asyncio.iscoroutinefunction(self.on_status_changed):
                            asyncio.run(self.on_status_changed(status_data))
                        else:
                            self.on_status_changed(status_data)
                    except Exception as e:
                        logger.error(f"フォールバックコールバックの実行エラー: {e}")
        except Exception as ex:
            logger.exception(f"[_handle_media_status_change] メディアステータス変化処理中に例外が発生しました: {ex}")

