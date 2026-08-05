import asyncio
import logging
import sys
import os
import time
import subprocess

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath("e:/Project/ChromecastRemoteControl"))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("GUI_E2E_Test")

def run_gui_and_simulate_exit():
    logger.info("=== GUI E2E 終了シミュレーションテスト開始 ===")
    
    # 既存の app_debug.log を削除してクリーンな状態にする
    log_file = "e:/Project/ChromecastRemoteControl/app_debug.log"
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
            logger.info("古い app_debug.log を削除しました")
        except Exception as e:
            logger.warning(f"ログ削除エラー: {e}")

    # GoogleTVRemote.exe を起動
    exe_path = "e:/Project/ChromecastRemoteControl/GoogleTVRemote.exe"
    logger.info(f"Executable を起動します: {exe_path}")
    proc = subprocess.Popen([exe_path])
    
    # 起動を待つ (4秒)
    time.sleep(4)
    
    logger.info("アプリが起動しました。シミュレーション動作中...")
    time.sleep(2)
    
    # プロセスに終了（クローズ）を要求・タスクキルで終了動作をトリガー
    logger.info("プロセス終了を実行します...")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    logger.info("=== GUI E2E テスト終了 ===")

if __name__ == "__main__":
    run_gui_and_simulate_exit()
