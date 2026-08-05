import flet as ft

def get_border_all(width: float, color: str) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)

def main(page: ft.Page):
    page.title = "GD Hover Test"

    status = ft.Text("Status: Idle")

    box = ft.Container(
        width=120,
        height=60,
        bgcolor="#1C1C24",
        border=get_border_all(1, "white"),
        content=ft.Text("GD Hover Direct", color="white"),
        alignment=ft.alignment.Alignment.CENTER,
        border_radius=30
    )

    def on_hover(e):
        print(f"GD Hover event: {e.data}")
        status.value = f"GD Hover: {e.data}"
        if e.data == "true":
            box.border = get_border_all(3, "cyan")
            box.shadow = ft.BoxShadow(spread_radius=2, blur_radius=10, color="#6600D2FF")
        else:
            box.border = get_border_all(1, "white")
            box.shadow = None
        page.update()

    def on_down(e):
        print("GD Down")
        status.value = "GD Down!"
        box.bgcolor = "#8A2BE2"
        box.border = get_border_all(3, "#A855F7")
        page.update()

    def on_up(e):
        print("GD Up")
        status.value = "GD Up!"
        box.bgcolor = "#1C1C24"
        box.border = get_border_all(3, "cyan")
        page.update()

    def on_cancel(e):
        print("GD Cancel")
        status.value = "GD Cancel!"
        box.bgcolor = "#1C1C24"
        box.border = get_border_all(1, "white")
        box.shadow = None
        page.update()

    gd = ft.GestureDetector(
        content=box,
        on_tap_down=on_down,
        on_tap_up=on_up,
        on_tap_cancel=on_cancel,
        on_hover=on_hover
    )

    page.add(gd, status)

ft.app(target=main)
