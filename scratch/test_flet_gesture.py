import flet as ft
import asyncio

async def main(page: ft.Page):
    page.title = "Gesture Test"
    
    is_seeking = False
    seek_task = None
    log_text = ft.Text("Press and hold the button below...", size=20)
    
    async def seek_loop(direction):
        nonlocal is_seeking
        count = 0
        while is_seeking:
            count += 1
            log_text.value = f"SEEKING ({direction}): count={count}"
            page.update()
            await asyncio.sleep(0.15)

    def on_long_start(e, direction):
        nonlocal is_seeking, seek_task
        is_seeking = True
        log_text.value = f"Long Press Started ({direction})"
        page.update()
        seek_task = asyncio.create_task(seek_loop(direction))

    def on_long_end(e):
        nonlocal is_seeking, seek_task
        is_seeking = False
        if seek_task:
            seek_task.cancel()
        log_text.value = "Long Press Ended!"
        page.update()

    def on_tap(e, direction):
        if not is_seeking:
            log_text.value = f"Single Tap ({direction})"
            page.update()

    btn_right = ft.GestureDetector(
        content=ft.Container(
            content=ft.Text("▶▶ RIGHT", color="white", size=18),
            bgcolor="#8A2BE2",
            padding=20,
            border_radius=10
        ),
        on_tap=lambda e: on_tap(e, "RIGHT"),
        on_long_press_start=lambda e: on_long_start(e, "RIGHT"),
        on_long_press_end=on_long_end
    )
    
    page.add(log_text, btn_right)

if __name__ == "__main__":
    ft.app(target=main)
