import flet as ft
import inspect

print("Checking ft.GestureDetector properties:")
gd = ft.GestureDetector()
props = [p for p in dir(gd) if 'long_press' in p or 'tap' in p]
print("GestureDetector callbacks:", props)
