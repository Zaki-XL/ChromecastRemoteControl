import flet as ft

def get_border_all(width: float, color: str) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)

def main(page: ft.Page):
    page.title = "MouseRegion Test"

    status = ft.Text("Status: Idle")

    box = ft.Container(
        width=100,
        height=100,
        bgcolor="#1C1C24",
        border=get_border_all(1, "white"),
        content=ft.Text("Hover & Click"),
        alignment=ft.alignment.Alignment.CENTER,
        border_radius=50
    )

    def on_enter(e):
        status.value = "Hover ENTER!"
        box.border = get_border_all(3, "cyan")
        box.shadow = ft.BoxShadow(spread_radius=2, blur_radius=10, color="#6600D2FF")
        page.update()

    def on_exit(e):
        status.value = "Hover EXIT!"
        box.border = get_border_all(1, "white")
        box.shadow = None
        page.update()

    def on_down(e):
        status.value = "Pressed DOWN!"
        box.bgcolor = "#8A2BE2"
        box.border = get_border_all(3, "#A855F7")
        page.update()

    def on_up(e):
        status.value = "Released UP!"
        box.bgcolor = "#1C1C24"
        box.border = get_border_all(3, "cyan")
        page.update()

    def on_cancel(e):
        status.value = "Cancelled!"
        box.bgcolor = "#1C1C24"
        box.border = get_border_all(1, "white")
        box.shadow = None
        page.update()

    gd = ft.GestureDetector(
        content=box,
        on_tap_down=on_down,
        on_tap_up=on_up,
        on_tap_cancel=on_cancel
    )

    mr = ft.MouseRegion(
        content=gd,
        on_enter=on_enter,
        on_exit=on_exit
    )

    page.add(mr, status)

ft.app(target=main)
