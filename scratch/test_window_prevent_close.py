import flet as ft
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestPreventClose")

def main(page: ft.Page):
    page.title = "Prevent Close Test"
    page.window.prevent_close = True

    def window_event(e):
        if e.data == "close":
            logger.info("Close intercepted! Exiting instantly...")
            os._exit(0)

    page.window.on_event = window_event

    def on_btn_click(e):
        window_event(ft.ControlEvent(target="", name="close", data="close", control=e.control, page=page))

    page.add(
        ft.Text("Click close button or window X"),
        ft.ElevatedButton("Close App Instantly", on_click=on_btn_click)
    )

if __name__ == "__main__":
    print("Testing prevent_close pattern...")
    ft.app(target=main)
