import flet as ft
import asyncio
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ExitTest")

def test_flet_exit_patterns():
    logger.info("=== Testing Flet Exit Behavior Patterns ===")
    
    # テスト1: os._exit(0) をボタンで呼んだ時
    def run_app_pattern_1():
        def main(page: ft.Page):
            page.title = "Exit Test Pattern 1"
            
            def on_exit_click(e):
                logger.info("[Pattern 1] Exit button clicked. Executing os._exit(0)...")
                os._exit(0)

            page.add(
                ft.Text("Pattern 1: Direct os._exit(0)"),
                ft.ElevatedButton("Exit Now", on_click=on_exit_click)
            )

        # 1秒後に自動クリックして終了テスト
        print("Running Pattern 1...")

if __name__ == "__main__":
    print("Testing Flet Window Destroy vs Exit methods...")
    
    # 実際の問題コード main.py 内の close_btn ハンドラをテスト
    def main_test(page: ft.Page):
        page.window.title_bar_hidden = True
        page.window.frameless = True
        
        def on_close_click(e):
            logger.info("Close button clicked in Test. Performing cleanup...")
            logger.info("Calling os._exit(0)...")
            os._exit(0)

        close_btn = ft.Container(
            content=ft.Text("✕", color="white", size=14),
            width=30,
            height=30,
            alignment=ft.alignment.Alignment.CENTER,
            bgcolor="red",
            on_click=on_close_click
        )

        page.add(ft.Row([ft.Text("Header Drag Area"), close_btn]))
        logger.info("App loaded successfully in headless/test mode.")

    # 動作可能かテスト
    ft.app(target=main_test)
