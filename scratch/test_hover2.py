import flet as ft

def main(page: ft.Page):
    page.title = "Hover Test 2"

    # Test 1: Container inside GestureDetector vs GestureDetector inside Container
    # Can GestureDetector hover be emulated or captured?
    
    # What if Container has on_hover AND GestureDetector is inside?
    # What if GestureDetector mouse_cursor / event handling?
    
    label1 = ft.Text("Test 1: Container(on_hover) > GestureDetector")
    status1 = ft.Text("Hover: False")
    
    box1 = ft.Container(
        width=120, height=60, bgcolor="#1C1C24",
        border=ft.border.all(1, "white"),
        content=ft.Text("Btn 1", color="white"),
        alignment=ft.alignment.center,
        border_radius=10
    )
    
    def hover1(e):
        status1.value = f"Hover: {e.data}"
        if e.data == "true":
            box1.border = ft.border.all(4, "cyan")
        else:
            box1.border = ft.border.all(1, "white")
        page.update()
        
    gd1 = ft.GestureDetector(
        content=box1,
        on_tap_down=lambda e: print("down1"),
        on_tap_up=lambda e: print("up1")
    )
    
    wrap1 = ft.Container(content=gd1, on_hover=hover1)

    # Test 2: GestureDetector with transparent stack or Container with on_hover on TOP?
    label2 = ft.Text("Test 2: Stack(GestureDetector, Container(on_hover))")
    status2 = ft.Text("Hover 2: False")
    
    box2 = ft.Container(
        width=120, height=60, bgcolor="#1C1C24",
        border=ft.border.all(1, "white"),
        content=ft.Text("Btn 2", color="white"),
        alignment=ft.alignment.center,
        border_radius=10
    )
    
    def hover2(e):
        status2.value = f"Hover 2: {e.data}"
        if e.data == "true":
            box2.border = ft.border.all(4, "cyan")
        else:
            box2.border = ft.border.all(1, "white")
        page.update()
        
    overlay_hover = ft.Container(
        width=120, height=60,
        bgcolor="transparent",
        on_hover=hover2
    )

    stack2 = ft.Stack([
        ft.GestureDetector(
            content=box2,
            on_tap_down=lambda e: print("down2"),
            on_tap_up=lambda e: print("up2")
        ),
        # Note: overlay on top might block GestureDetector clicks if not ignore_transports
    ])

    # Test 3: Standard Container with on_hover and on_click only
    label3 = ft.Text("Test 3: Container(on_click, on_hover)")
    status3 = ft.Text("Hover 3: False")
    box3 = ft.Container(
        width=120, height=60, bgcolor="#1C1C24",
        border=ft.border.all(1, "white"),
        content=ft.Text("Btn 3", color="white"),
        alignment=ft.alignment.center,
        border_radius=10,
        on_hover=lambda e: hover3(e),
        on_click=lambda e: print("click3")
    )
    def hover3(e):
        status3.value = f"Hover 3: {e.data}"
        if e.data == "true":
            box3.border = ft.border.all(4, "cyan")
        else:
            box3.border = ft.border.all(1, "white")
        page.update()

    page.add(
        ft.Column([
            label1, wrap1, status1,
            ft.Divider(),
            label3, box3, status3
        ])
    )

ft.app(target=main)
