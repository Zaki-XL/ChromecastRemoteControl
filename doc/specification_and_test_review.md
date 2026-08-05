# ChromecastRemoteControl - 実装仕様書 & テストレビュー報告書

## 1. 概要

本ドキュメントは、**ChromecastRemoteControl** アプリケーションの現時点における機能実装仕様を明確に定義し、それに対するテストの網羅性・妥当性を客観的に評価・レビューした報告書です。

---

## 2. 実装仕様書 (System Specification)

### 2.1 技術スタック & アーキテクチャ
- **ランタイム**: Python 3.12
- **UIフレームワーク**: Flet 0.86.5 (Flutterベース Desktop UI)
- **通信プロトコル**:
  - **リモコン制御**: Android TV Remote Protocol v2 (TLS, Protocol Buffers, mDNS `_androidtvremote2._tcp.local.`)
  - **メディアキャスト制御**: PyChromecast (Chromecast Cast Protocol)
- **ビルド・パッケージング**: PyInstaller (`--noconsole`, 単一実行ファイル `GoogleTVRemote.exe`)

---

### 2.2 UI構造 & インタラクティブ仕様

```
+-------------------------------------------------------------+
| 📺 Chromecast Remote              bedroom cast   [⚙️]     | <- Header
+-------------------------------------------------------------+
| ⚙️ Settings & Devices                                  (v)  | <- Accordion (Folded)
|  - Size / Opacity Sliders                                  |
|  - Discovered Device Chips & Refresh Button                 |
+-------------------------------------------------------------+
|                        ▲                                    |
|                   ◀   OK   ▶                                | <- Remote Panel
|                        ▼                                    | (D-Pad & Actions)
|     ⏻ POWER   ⏯ PLAY/PAUSE   ⏎ BACK   🏠 HOME  🔉 MUTE 🔊  |
+-------------------------------------------------------------+
| 🚀 Quick Launch Apps                                   (v)  | <- Accordion (Folded)
|  [YouTube]  [Netflix]  [Prime Video]  [Spotify]  [Google TV]|
+-------------------------------------------------------------+
| 🎵 Track Title - Artist Name                                | <- Bottom Media Panel
| [===================----------] 1:23 / 3:45                 | (Player Controls)
|                   ⏮   ▶   ⏭                                 |
+-------------------------------------------------------------+
```

#### A. ボタン状態遷移 (Button States & Interactions)
すべてのボタン要素（D-Pad, 決定, アクション, アプリ起動, デバイスチップ, メディア操作）は以下の3状態を持ちます：

1. **通常状態 (Idle State)**:
   - 背景色: ダークグレー (`#1C1C24` または `#1A1A24`)
   - 境界線 (Border): 1px 薄枠 (`#33ffffff`)
   - ドロップシャドウ: 無効
2. **ホバー状態 (Hover State - マウスカーソル進入時)**:
   - トリガー: `on_hover` イベント (`e.data == "true"`)
   - 境界線 (Border): **3px 太線ネオンシアン (`#00D2FF`)**
   - ドロップシャドウ: **青色ネオン発光 (`spread_radius=2, blur_radius=10, color="#6600D2FF"`)**
3. **押下状態 (Active / Pressed State - ボタンタップ時)**:
   - トリガー: `on_tap_down` / `on_down` (押下瞬間)
   - 背景色: **ネオンパープル (`#8A2BE2`)**
   - 境界線 (Border): **3px 明るいパープル (`#A855F7`)**
   - 復元: `on_tap_up` (離した時) または `on_tap_cancel` (範囲外リリース時) で即座に通常状態へ復元。

#### B. 画面サイズ & レスポンシブ仕様
- **基準解像度**: 420 × 750 px (スケール `current_scale = 1.0`)
- **自由枠ドラッグ可変**: OS枠線ドラッグ (`page.window.resizable = True`) および `page.on_resized` で幅に合わせて `current_scale` を動的再計算。
- **プロポーショナル表示**: `S(val)` 比例計算関数により、すべてのフォントサイズ・ボタン直径・パディング・間隔が動的拡縮。

---

### 2.3 通信 & 接続シーケンス
1. **起動時自動探索**: `AndroidTVTracker` が mDNS によりローカルネットワーク上のデバイスをバックグラウンド探索。
2. **前回接続自動復元**: `config.ini` の `last_device_id` / `ip` を読み込み、起動時に自動再接続を試行。
3. **ペアリング認証**: 未認証デバイスへの初回接続時、`PairingRequiredException` をキャッチし、テレビ画面の 6桁 PIN 入力 AlertDialog を表示。

---

## 3. テスト適合性 & 網羅性レビュー報告 (Test Coverage Review)

現在の開発チームで実施しているテスト・検証手法を、上記の仕様項目に対して評価・レビューしました。

### 3.1 仕様に対するテスト適合性マトリクス

| 仕様領域 | 仕様要件 | 現在のテスト方法 | 適合度判定 | 発見された課題・盲点 |
| :--- | :--- | :--- | :---: | :--- |
| **起動・例外ハンドリング** | アプリ起動時に構文エラーや例外が発生しないこと | バックグラウンド実行 (`python main.py`) ＆ ログ解析 (`task-xxxx.log`) | 🟢 **適合** (100%) | 例外ログのキャッチは完璧。 |
| **ネットワーク/mDNS** | デバイス発見や IP 変更時にUIが正しく更新されること | ログ出力監視 ＆ `AndroidTVTracker` イベントのシミュレーション | 🟢 **適合** (90%) | ネットワーク環境に依存するためモックの導入が望ましい。 |
| **ビルド・配布** | DOSコンソール非表示 (`--noconsole`) で単一 EXE が生成されること | PyInstaller 実行後の Exit Code ＆ Binary 存在チェック | 🟢 **適合** (100%) | 配布ファイルの整合性は確認済み。 |
| **ボタン押下状態 (Pressed)** | ボタンタップ時に色が紫に変わり、外離しで復元すること | `scratch/test_hover3.py` での `on_tap_down`/`up` イベントログ検証 | 🔴 **不十分** (40%) | ログ上のイベント受信は確認できたが、**「押下中の変色」と「ホバー時の枠線変化」が同一コントロールで同時に意図通り視認できるかの目視確認が不足**していた。 |
| **ボタンホバー状態 (Hover)** | マウスカーソルを乗せた瞬間に太線ネオンシアンが発光すること | `Container` / `GestureDetector` の `e.data` イベント確認 | 🟡 **要改善** (60%) | Flet の `GestureDetector` が Pointer イベントを遮断する Flutter 固有の現象により、組み合わせ時のホバー発火不全が見落とされていた。 |

---

### 3.2 レビュー結論 & 改善アクションプラン

#### 【問題の根本原因】
ログ監視やイベント発火コードの存在確認（静的・単体レベルのログチェック）に偏重しており、**「ホバー（Mouse Enter/Leave）」と「押下（Touch Down/Up）」が視覚的に正しく相互作用しているかの E2E（エンドツーエンド）描画確認が不足**していました。

#### 【今後の推奨テスト改善策】
1. **イベント統合コントロールの標準化**:
   `on_hover` と `on_tap_down` / `on_tap_up` を完全に両立させるため、`ft.Container` と `ft.GestureDetector` の組み合わせパターンをコンポーネントライブラリとしてカプセル化する。
2. **視覚的E2Eテスト（スナップショットテスト）の導入**:
   Flet の Web/Desktop クライアントに対し、Playwright または Visual Regression Test を導入し、通常時・ホバー時・押下時のスクリーンショット差分を自動検証する仕組みを構築する。

---
*報告作成日時: 2026-08-03*  
*作成者: Antigravity AI Team*
