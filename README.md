# ChromecastRemoteControl

[English](README_EN.md) | 日本語

Chromecast with Google TV / Android TV デバイス向けの、軽量かつ高機能なデスクトップリモコン＆メディアコントローラーアプリケーションです。  
Python と [Flet](https://flet.dev/)（Flutter エンジン）をベースに構築されており、ネイティブライクなモダン UI と快適な操作性を提供します。

---

## 主な特徴

- **完全なリモコン操作 (Android TV Remote v2)**
  - 方向キー (D-Pad)、決定、戻る、ホーム、電源、音量、消音
  - キーボードショートカット操作対応（矢印キー、Enter、Esc、Space、音量キー等）
  - キーの長押し連続送信・短押しタップの正確な判定
  - 主要動画配信アプリ（YouTube, Netflix, Prime Video, U-NEXT, ABEMA, TVer 等）のワンクリック起動
- **Google Cast メディア連携 (pychromecast)**
  - 現在再生中のメディア情報（タイトル、アーティスト、アルバムアート、再生位置、総時間）のリアルタイム同期
  - 再生 / 一時停止、スキップ（次へ / 前へ）、シークバーによる任意位置へのシーク
  - 字幕（CC）のワンクリック有効化 / 無効化
  - 長いタイトルに対応する自動マーキースクロール表示
- **多言語対応 (Multilingual Support)**
  - **字幕優先言語の自動適用**: キャスト開始時に指定した優先言語コード（日本語 `ja`、英語 `en` 等）に一致する字幕トラックを自動検出して適用
  - **ワンクリック言語切り替え**: 設定パネルから優先言語を即時切り替え可能
  - **多言語ドキュメント**: 日本語 ([README.md](README.md)) および英語 ([README_EN.md](README_EN.md)) のバイリンガルドキュメントを提供
- **自動デバイス検出 & 自動再接続**
  - mDNS (Zeroconf) によるローカルネットワーク上の Android TV 自動探索
  - PC スリープ / 休止状態からの復帰を検知した自動切断クリーンアップ＆再接続
  - 起動時の前回接続デバイスへの自動接続
- **洗練されたデスクトップ UI/UX**
  - ネオングラデーションを基調としたダークサイバーパンク調デザイン
  - ウィンドウサイズに応じた動的スケーリング（フォント・ボタン寸法の自動追随）
  - ウィンドウ透明度（Opacity）スライダー調整
  - 軽量なメモリバッファリング付きデバッグロギング

---

## システム構成図

```mermaid
graph TD
    User["ユーザー操作 (GUI / Keyboard)"] --> FletUI["Flet GUI (Flutter UI Engine)"]
    FletUI --> RemoteClient["AndroidTVRemoteClient<br/>(Port 6466 / 6467 SSL)"]
    FletUI --> CastClient["ChromecastCastClient<br/>(Port 8009 Socket & Worker)"]
    FletUI --> Tracker["AndroidTVTracker<br/>(Zeroconf mDNS)"]
    
    RemoteClient --> AndroidTV["Google TV / Android TV"]
    CastClient --> AndroidTV
    Tracker --> AndroidTV
```

---

## 必要要件

- **OS**: Windows 10 / 11 (64-bit)
- **Python**: 3.10 以上 (Python 3.12 推奨)
- **対象デバイス**: Chromecast with Google TV または Android TV OS 搭載テレビ/端末（同一ローカルネットワーク内に接続）

---

## ダウンロード & 実行方法（推奨）

Python 環境の構築を行わずに、すぐに利用できるスタンドアロン版（EXE）を配布しています。

1. **ZIP パッケージのダウンロード**:  
   [GitHub Releases](https://github.com/Zaki-XL/ChromecastRemoteControl/releases) から最新バージョンの `GoogleTVRemote_vX.X.X_win64.zip` をダウンロードします。
2. **展開（解凍）**:  
   ダウンロードした ZIP ファイルを任意のフォルダー（例: ドキュメントフォルダーやデスクトップなど）に展開します。
3. **起動**:  
   展開したフォルダー内の `GoogleTVRemote.exe` をダブルクリックして実行します。

---

## アンインストール方法

本アプリケーションは、Windows のレジストリやシステムフォルダー（AppData 等）を変更しない**ポータブル（スタンドアロン）設計**となっています。

- 実行時に生成される設定ファイル（`config.ini`）やペアリング証明書（`certs/` フォルダ）は、すべて **`GoogleTVRemote.exe` と同じフォルダー内** にのみ保存されます。
- アンインストールしたい場合は、**解凍したフォルダー一式をそのまま削除（ゴミ箱へ移動）するだけ**で、PC に痕跡を残さず完全にアンインストールが完了します。

---

## セットアップ手順（ソースコードから実行する場合）

Python 開発環境から直接実行・カスタマイズする場合の手順です。

### 1. リポジトリのクローン
```bash
git clone https://github.com/Zaki-XL/ChromecastRemoteControl.git
cd ChromecastRemoteControl
```

### 2. 仮想環境の作成と依存ライブラリのインストール
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 初期設定
初回起動時に `config.ini` が自動生成されます。必要に応じて設定テンプレート `config.example.ini` を参考に手動設定することも可能です。

### 4. 起動
```bash
python main.py
```
起動用のバッチファイル `build.bat` または `run_app.bat` からも起動できます。

---

## 使い方・ペアリング方法

1. アプリを起動すると、ネットワーク上の Android TV / Chromecast デバイスが自動探索され、上部にチップとして表示されます。
2. 初回接続時、テレビ画面に **6桁のPINコード** が表示されます。
3. アプリの入力ダイアログにPINコードを入力して「送信」を押すと、SSLペアリングが完了します（証明書は `certs/` に保存され、次回以降自動接続されます）。
4. 画面上のリモコンボタンまたはキーボードでテレビを直感的に操作できます。

---

## 多言語・字幕優先設定

アプリ上部の設定アコーディオン（Settings & Devices）内に、**Preferred Language（優先言語）** 設定が用意されています。

- **対応言語**: 日本語 (`ja`)、英語 (`en`) など
- **動作仕様**:
  - メディアのキャスト開始時、動画側に設定した優先言語に一致する字幕トラックが存在する場合、自動的に字幕が ON になります。
  - 下部メディア操作パネルの「CC」ボタンを押すことで、手動での字幕 ON / OFF 切り替えも即座に行えます。

---

## キーボードショートカット

| キー | 操作内容 |
| :--- | :--- |
| `↑` `↓` `←` `→` | 方向キー移動 (D-Pad) |
| `Enter` | 決定 (OK) |
| `Backspace` / `Escape` | 戻る (BACK) |
| `Home` | ホーム画面 (HOME) |
| `Space` | メディア再生 / 一時停止 |
| `Page Up` / `+` | 音量アップ |
| `Page Down` / `-` | 音量ダウン |
| `M` | 消音 (MUTE) |

---

## EXE ビルド方法

PyInstaller を用いて単一のスタンドアロン実行可能ファイル (`GoogleTVRemote.exe`) を生成できます。

```powershell
powershell -ExecutionPolicy Bypass -File build_app.ps1
```
ビルド完了後、ルートディレクトリおよび `dist/` フォルダ配下に実行ファイルが生成されます。

---

## ファイル構成

```text
ChromecastRemoteControl/
├── main.py              # アプリケーションエントリーポイント & Flet GUI
├── cast_client.py       # pychromecast ラッパー（メディア同期・ワーカースレッド）
├── remote_client.py     # androidtvremote2 ラッパー（リモコン操作・SSL通信）
├── device_tracker.py    # Zeroconf による mDNS デバイス自動探索
├── config_manager.py    # config.ini 設定管理
├── requirements.txt     # 依存 Python パッケージ一覧
├── build_app.ps1        # PyInstaller ビルドスクリプト
├── build.bat            # 簡易ビルドバッチ
├── config.example.ini   # 設定ひな形テンプレート
├── README.md            # 日本語ドキュメント
├── README_EN.md         # 英語ドキュメント
└── LICENSE              # ライセンス表記 (MIT)
```

---

## ライセンス

本プロジェクトは [MIT License](LICENSE) の下で公開されています。
