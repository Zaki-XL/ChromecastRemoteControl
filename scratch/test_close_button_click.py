import flet as ft

def dummy_window_event(e):
    data = e.data if hasattr(e, 'data') else str(e)
    print(f"window_event triggered with data='{data}'")

def on_close_click_fixed(e):
    dummy_window_event("close")

try:
    on_close_click_fixed(None)
    print("SUCCESS: Fixed on_close_click executed cleanly with no exceptions!")
except Exception as ex:
    print(f"FAILED: {ex}")
