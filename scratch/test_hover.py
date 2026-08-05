import flet as ft

def main(page: ft.Page):
    page.title = "Hover Test"
    
    # 方式A: Container (on_hover) -> GestureDetector
    log_a = ft.Text("A: Hover status unknown")
    box_a = ft.Container(
        width=100, height=100, bgcolor="red",
        content=ft.Text("A")
    )
    
    def on_hover_a(e):
        log_a.value = f"A Hover: {e.data}"
        box_a.bgcolor = "cyan" if e.data == "true" else "red"
        page.update()
        
    def on_click_a(e):
        log_a.value = "A Clicked!"
        page.update()
        
    gd_a = ft.GestureDetector(
        content=box_a,
        on_tap_down=lambda e: print("A tap down"),
        on_tap_up=lambda e: print("A tap up")
    )
    wrapper_a = ft.Container(content=gd_a, on_hover=on_hover_a)

    # 方式B: GestureDetector (on_hover?)
    # 方式C: Container (on_hover, on_click)
    log_c = ft.Text("C: Hover status unknown")
    box_c = ft.Container(
        width=100, height=100, bgcolor="blue",
        content=ft.Text("C"),
        on_click=lambda e: print("C clicked"),
        on_hover=lambda e: set_c_hover(e)
    )
    def set_c_hover(e):
        log_c.value = f"C Hover: {e.data}"
        box_c.bgcolor = "cyan" if e.data == "true" else "blue"
        page.update()

    page.add(
        ft.Row([wrapper_a, box_c]),
        log_a,
        log_c
    )

ft.app(target=main)
