import flet as ft

def get_border_all(width: float, color: str) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)

def main(page: ft.Page):
    page.title = "Stack Hover Investigation"

    status_hover = ft.Text("Hover Status: False", size=14, color="yellow")
    status_click = ft.Text("Click Status: None", size=14, color="green")

    # 下層：見た目担当 (on_hover)
    visual_box = ft.Container(
        width=120,
        height=60,
        bgcolor="#1C1C24",
        border=get_border_all(1, "white"),
        content=ft.Text("Stack Test", color="white"),
        alignment=ft.alignment.Alignment.CENTER,
        border_radius=30
    )

    def on_hover_fn(e):
        print(f"[LOG] Hover Event: {e.data}")
        status_hover.value = f"Hover Status: {e.data}"
        if e.data == "true":
            visual_box.border = get_border_all(3, "cyan")
            visual_box.shadow = ft.BoxShadow(spread_radius=2, blur_radius=10, color="#6600D2FF")
        else:
            visual_box.border = get_border_all(1, "white")
            visual_box.shadow = None
        page.update()

    visual_layer = ft.Container(
        content=visual_box,
        on_hover=on_hover_fn
    )

    # 上層：透明操作担当 (on_click)
    def on_click_fn(e):
        print("[LOG] Click Event Fired!")
        status_click.value = "Click Status: CLICKED!"
        page.update()

    touch_layer = ft.Container(
        width=120,
        height=60,
        bgcolor="transparent",
        on_click=on_click_fn
    )

    stack_btn = ft.Stack(
        [
            visual_layer,
            touch_layer
        ],
        width=120,
        height=60
    )

    page.add(
        ft.Column([
            stack_btn,
            status_hover,
            status_click
        ], spacing=20)
    )

ft.app(target=main)
