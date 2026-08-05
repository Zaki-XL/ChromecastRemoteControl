
import flet as ft
import sys
import time

def child_main(page: ft.Page):
    page.title = "Child GUI Window"
    page.window.title_bar_hidden = True
    page.window.frameless = True
    page.bgcolor = "#121214"
    
    def on_close_click(e):
        print("SHUTDOWN_REQUEST", flush=True)
        time.sleep(0.05)
        
    close_btn = ft.Container(
        content=ft.Text("✕ Close App", color="white", size=14),
        bgcolor="red",
        padding=10,
        border_radius=5,
        on_click=on_close_click
    )
    
    page.add(ft.Text("Testing Child GUI Process...", size=18, color="white"), close_btn)

if __name__ == "__main__":
    ft.app(target=child_main)
