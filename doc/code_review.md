# コードレビューレポート — ChromecastRemoteControl

> **日時**: 2026-08-02 23:25  
> **対象ファイル**: `main.py` (1044行), `cast_client.py` (220行), `remote_client.py` (230行), `device_tracker.py` (199行), `config_manager.py` (192行), `build_app.ps1` (67行)  
> **総行数**: 約 1,952 行

---

## サマリ

| 重大度 | 件数 |
|--------|------|
| 🔴 CRITICAL（実行時クラッシュ/データ破損） | 2 |
| 🟠 HIGH（機能不全/潜在バグ） | 5 |
| 🟡 MEDIUM（保守性/設計上の問題） | 7 |
| 🔵 LOW（スタイル/軽微な改善） | 6 |

---

## 🔴 CRITICAL

### C-1. ミュートのトグルで `AttributeError` 発生  
**ファイル**: [main.py#L338](file:///e:/Project/ChromecastRemoteControl/main.py#L338)

```python
status = cast_client.cast.volume_control.status  # ← AttributeError
is_muted = status.muted if status else False
```

`pychromecast.Chromecast` に `.volume_control` プロパティは**存在しません**。正しくは `cast_client.cast.status` でキャストデバイスのステータスオブジェクトを取得し、`.volume_muted` で現在のミュート状態を参照します。

**修正案**:
```python
is_muted = cast_client.cast.status.volume_muted if cast_client.cast.status else False
cast_client.mute(not is_muted)
```

---

### C-2. `get_chromecasts()` の非推奨呼び出しがスキャンを無期限ブロックする可能性  
**ファイル**: [cast_client.py#L83](file:///e:/Project/ChromecastRemoteControl/cast_client.py#L83)

```python
casts, browser = pychromecast.get_chromecasts()
```

`get_chromecasts()` はデフォルトでネットワーク上のすべてのデバイスを見つけるまで **最大30秒間ブロック**します。加えて、ログに以下の警告が出ています:
```
discover_chromecasts is deprecated and will be removed in June 2024, update to use CastBrowser instead.
```

バックグラウンドスレッドで呼ばれるため UI フリーズは起きませんが、接続完了まで30秒掛かる可能性があります。

**修正案**: `pychromecast.get_listed_chromecasts(friendly_names=[...])` もしくは `CastBrowser` API に移行し、タイムアウト付きで特定IPのデバイスのみを検索:
```python
from pychromecast.discovery import CastBrowser, SimpleCastListener
listener = SimpleCastListener()
browser = CastBrowser(listener, zeroconf_instance)
browser.start_discovery()
time.sleep(5)  # 5秒のスキャン
browser.stop_discovery()
```

---

## 🟠 HIGH

### H-1. `on_size_change` でスライダー操作のたびに INI ファイルに書き込み  
**ファイル**: [main.py#L927-L936](file:///e:/Project/ChromecastRemoteControl/main.py#L927-L936)

スライダーの `on_change` はドラッグ中にフレーム毎に発火します。20ステップのスライダーでは1回のドラッグで**数十回のディスクI/O**が走り、SSD寿命に影響し得ます。`on_opacity_change` も同様。

**修正案**: デバウンス処理を導入し、操作完了後（500ms 静止後）に1回だけ保存する。あるいは `on_change_end` イベント（存在する場合）を使用:
```python
_save_timer = None
def on_size_change(e):
    # ... UI更新 ...
    nonlocal _save_timer
    if _save_timer:
        _save_timer.cancel()
    _save_timer = threading.Timer(0.5, lambda: (config.save()))
    _save_timer.start()
```

---

### H-2. `format_time` がコールバック呼び出しごとに再定義される  
**ファイル**: [main.py#L819-L821](file:///e:/Project/ChromecastRemoteControl/main.py#L819-L821)

```python
if duration > 0:
    progress_bar.value = current_time / duration
    def format_time(sec: float) -> str:  # ← 毎回再定義
```

メディアステータスは数秒おきにコールバックされるため、毎回関数オブジェクトが再生成されます。機能的に致命的ではないが、無駄なGC圧を生みます。

**修正案**: `on_media_status_changed` の外に一度だけ定義する。

---

### H-3. `build_app.ps1` にビルド前の `taskkill` が組み込まれていない  
**ファイル**: [build_app.ps1#L36](file:///e:/Project/ChromecastRemoteControl/build_app.ps1#L36)

本セッションで**毎回ビルド後にファイルロックで `Copy-Item` が失敗**しました。ビルドスクリプト冒頭でプロセスを終了するのが合理的です。

**修正案**:
```powershell
# ビルド前に既存プロセスを停止
taskkill /F /IM GoogleTVRemote.exe 2>$null
Start-Sleep -Seconds 1
```

---

### H-4. スライダー操作時にスケーリングで UI 要素が歪む  
**ファイル**: [main.py#L929-L930](file:///e:/Project/ChromecastRemoteControl/main.py#L929-L930)

```python
new_w = int(420 * scale)
new_h = int(750 * scale)
```

ウィンドウサイズだけが変わり、内部のUI要素（ボタンサイズ、フォントサイズ、spacing）は固定のため、**縮小時にボタンが収まらず見切れ**、**拡大時にスカスカ**になります。`page.window.resizable = False` で固定しているにも関わらず、スライダーでサイズ変更するのは設計が矛盾しています。

**修正案**: 
- 方法A: スライダーで `page.scale` を変更し、ウィンドウサイズは固定のまま中身をスケーリング
- 方法B: ウィンドウサイズの変更と連動してUI要素のサイズも動的に再計算

---

### H-5. `prev()` と `next()` メソッドが `cast_client.py` に未実装  
**ファイル**: [main.py#L645-L648](file:///e:/Project/ChromecastRemoteControl/main.py#L645-L648)

```python
elif action == "PREV":
    cast_client.prev()  # ← cast_client.py に prev() メソッドが存在しない
elif action == "NEXT":
    cast_client.next()  # ← 同上
```

`cast_client.py` には `play()`, `pause()`, `toggle_play_pause()`, `volume_up()`, `volume_down()`, `mute()` は実装されていますが、`prev()` と `next()` は**未実装**です。呼び出された場合 `AttributeError` でクラッシュします。

**修正案**: `cast_client.py` に以下を追加:
```python
def prev(self) -> None:
    if self.cast and self.cast.media_controller:
        self.cast.media_controller.rewind()

def next(self) -> None:
    if self.cast and self.cast.media_controller:
        self.cast.media_controller.skip()
```

---

## 🟡 MEDIUM

### M-1. グローバル変数の過剰使用  
**ファイル**: [main.py#L37-L47](file:///e:/Project/ChromecastRemoteControl/main.py#L37-L47)

`remote_client`, `cast_client`, `tracker`, `loop`, `held_keys`, `held_buttons` 等が**モジュールレベルのグローバル変数**として宣言され、`main()` 内で `global` 宣言で書き換えています。

**改善案**: `AppState` のようなデータクラスに集約し、`main()` 内でインスタンスを生成して依存性注入パターンに移行する。

---

### M-2. `main.py` の1ファイル肥大化（1,044行）  
**ファイル**: [main.py](file:///e:/Project/ChromecastRemoteControl/main.py)

UI定義、イベントハンドラ、接続ロジック、キーマッピング、スライダーが全て1ファイルに混在しています。

**改善案**: 以下のように分離する:
- `ui_components.py`: `DPadBtn`, `ActionBtn`, `GlassCard`, `AppBtn` 等のファクトリ
- `key_handler.py`: キーボード/ボタン長押し処理
- `connection_handler.py`: `connect_to_device`, `start_cast_connection`

---

### M-3. セクション番号の重複コメント  
**ファイル**: [main.py#L1005](file:///e:/Project/ChromecastRemoteControl/main.py#L1005) と [main.py#L1030](file:///e:/Project/ChromecastRemoteControl/main.py#L1030)

```python
# 10. クローズハンドラでの資源解放    ← L1005
# 10. セッション維持とクリーンアップ処理の保証  ← L1030
```

セクション番号 `10` が2回使われています。

---

### M-4. `tracker.stop()` の二重呼び出し  
**ファイル**: [main.py#L1012](file:///e:/Project/ChromecastRemoteControl/main.py#L1012) と [main.py#L1038](file:///e:/Project/ChromecastRemoteControl/main.py#L1038)

`on_window_disconnect` と `finally` ブロックの両方で `tracker.stop()` が呼ばれます。`stop()` は冪等なので即座には壊れませんが、設計意図が不明瞭です。

---

### M-5. `cast_client._handle_media_status_change` に残るデッドコード  
**ファイル**: [cast_client.py#L204-L219](file:///e:/Project/ChromecastRemoteControl/cast_client.py#L204-L219)

`on_media_status_changed` を同期関数に変更済みなので、以下の分岐は到達しません:
```python
if asyncio.iscoroutinefunction(self.on_status_changed):
    asyncio.run_coroutine_threadsafe(...)
```

**改善案**: 同期コールバック前提に簡略化するか、型ヒントで `Callable` の同期を明示する。

---

### M-6. PINコード入力のバリデーション文言のバグ  
**ファイル**: [main.py#L265](file:///e:/Project/ChromecastRemoteControl/main.py#L265)

```python
show_error("正しい6桁 of PINを入力してください。")
```

日英混合の文言になっています。「正しい6桁のPINコードを入力してください。」に修正すべきです。

---

### M-7. `bottom_media_panel` の固定幅 `width=370`  
**ファイル**: [main.py#L704](file:///e:/Project/ChromecastRemoteControl/main.py#L704)

ウィンドウ幅が420だとパディング15×2=30で実質390ですが、スライダーで幅を変更可能にした今、`width=370` は**縮小時にはみ出し、拡大時に左寄り**になります。

**修正案**: `expand=True` に変更するか、`width` を削除してレスポンシブに対応する。

---

## 🔵 LOW

### L-1. `ft.app()` の非推奨警告  
**ファイル**: [main.py#L1043](file:///e:/Project/ChromecastRemoteControl/main.py#L1043)

```
DeprecationWarning: app() is deprecated since version 0.80.0. Use run() instead.
```

**修正案**: `ft.app(target=main)` → `ft.app(target=main)` を `ft.run(main)` に変更（Flet 0.80+ API）。ただし、バージョン互換性を検証の上で。

---

### L-2. `Alignment` の参照方法が不統一  
**ファイル**: [main.py#L51](file:///e:/Project/ChromecastRemoteControl/main.py#L51) vs [main.py#L435](file:///e:/Project/ChromecastRemoteControl/main.py#L435)

```python
# L51: 冗長な書式
ft.alignment.Alignment.TOP_LEFT

# L435: 短縮書式
ft.alignment.top_left
```

**修正案**: どちらかに統一する。

---

### L-3. `AppBtn` の引数 `color` が未使用  
**ファイル**: [main.py#L562](file:///e:/Project/ChromecastRemoteControl/main.py#L562)

```python
def AppBtn(name: str, symbol: str, color: str, app_link: str):
```

`color` 引数は関数内で一度も参照されていません。

---

### L-4. `held_buttons_lock` と `held_keys_lock` の型ヒント不足  
**ファイル**: [main.py#L44-L47](file:///e:/Project/ChromecastRemoteControl/main.py#L44-L47)

`threading.Lock` オブジェクトに型アノテーションがありません。

---

### L-5. `build_app.ps1` のパスがハードコーディング  
**ファイル**: [build_app.ps1#L46](file:///e:/Project/ChromecastRemoteControl/build_app.ps1#L46)

```powershell
$exePath = "E:\Project\ChromecastRemoteControl\dist\GoogleTVRemote.exe"
```

`$PSScriptRoot` を使って相対パスにすべきです。

---

### L-6. `config.ini` にコメント（説明文）がない  
**ファイル**: [config.ini](file:///e:/Project/ChromecastRemoteControl/config.ini)

ユーザーが手動で `lock_port` や `opacity` を編集する際の説明がありません。`configparser` は `;` や `#` でコメントをサポートしています。

---

## 総合評価

| 観点 | 評価 |
|------|------|
| **機能性** | ⭐⭐⭐⭐☆ — リモコン・キャスト連携・自動再接続・ペアリングなど主要機能は揃っている |
| **堅牢性** | ⭐⭐⭐☆☆ — C-1, H-5 で未発覚の `AttributeError` クラッシュパスが残っている |
| **保守性** | ⭐⭐☆☆☆ — 1044行の単一ファイル、グローバル変数過多、責務分離が弱い |
| **パフォーマンス** | ⭐⭐⭐⭐☆ — H-1 以外は特に問題なし |
| **コード品質** | ⭐⭐⭐☆☆ — docstring・型ヒントは丁寧、ただしデッドコードや不統一がある |

> [!IMPORTANT]
> **優先対応推奨**: C-1（ミュートクラッシュ）と H-5（prev/nextクラッシュ）は**ユーザーがボタンを押した瞬間にクラッシュ**するため、最優先で修正すべきです。
