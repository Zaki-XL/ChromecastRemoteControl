import flet as ft

def get_border_all(width: float, color: str) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)

def main(page: ft.Page):
    page.title = "Hover Test 3"

    # Test 1: Container(on_hover) Wrapping GestureDetector
    status1 = ft.Text("Test 1 (Container > GestureDetector): Hover False")
    box1 = ft.Container(
        width=140, height=60, bgcolor="#1C1C24",
        border=get_border_all(1, "white"),
        content=ft.Text("Btn 1 (GD inside)", color="white"),
        alignment=ft.alignment.Alignment.CENTER,
        border_radius=10
    )
    
    def hover1(e):
        print(f"Hover1 Event: {e.data}")
        status1.value = f"Test 1 Hover: {e.data}"
        if e.data == "true":
            box1.border = get_border_all(4, "cyan")
        else:
            box1.border = get_border_all(1, "white")
        page.update()
        
    gd1 = ft.GestureDetector(
        content=box1,
        on_tap_down=lambda e: print("down1"),
        on_tap_up=lambda e: print("up1")
    )
    wrap1 = ft.Container(content=gd1, on_hover=hover1)

    # Test 2: Container direct on_hover and on_click
    status2 = ft.Text("Test 2 (Container direct): Hover False")
    box2 = ft.Container(
        width=140, height=60, bgcolor="#1C1C24",
        border=get_border_all(1, "white"),
        content=ft.Text("Btn 2 (Direct)", color="white"),
        alignment=ft.alignment.Alignment.CENTER,
        border_radius=10,
        on_click=lambda e: print("click2"),
        on_hover=lambda e: hover2(e)
    )
    def hover2(e):
        print(f"Hover2 Event: {e.data}")
        status2.value = f"Test 2 Hover: {e.data}"
        if e.data == "true":
            box2.border = get_border_all(4, "cyan")
        else:
            box2.border = get_border_all(1, "white")
        page.update()

    page.add(
        ft.Column([
            wrap1, status1,
            ft.Divider(),
            box2, status2
        ])
    )

ft.app(target=main)
