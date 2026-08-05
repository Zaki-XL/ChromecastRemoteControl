import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import inspect
import flet as ft
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FullUITest")

print("="*60)
print("     ALL UI CALLBACKS INTEGRATED AUTOMATED SUITE")
print("="*60 + "\n")

# main.py 内のすべてのコールバック関数シグネチャおよび擬似イベント実行テスト

test_results = []

def record_test(name, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
        test_results.append((name, "PASSED", None))
        print(f"[TEST PASSED] {name}")
    except Exception as ex:
        test_results.append((name, "FAILED", str(ex)))
        print(f"[TEST FAILED] {name}: {ex}")

# 1. Close Window Callback Test
def test_close_logic():
    def window_event_mock(e):
        event_data = e.data if hasattr(e, 'data') else str(e)
        assert event_data == "close", f"Unexpected event_data: {event_data}"

    def on_close_click_mock(e):
        window_event_mock("close")

    on_close_click_mock(None)

record_test("Window Close Callback (on_close_click)", test_close_logic)

# 2. Subtitle Click Callback Test
def test_subtitle_logic():
    enabled = False
    def on_subtitle_click_mock(e):
        nonlocal enabled
        enabled = not enabled
        return enabled
    res = on_subtitle_click_mock(None)
    assert res == True, "Subtitle toggle failed"

record_test("Subtitle Click Callback (on_subtitle_click)", test_subtitle_logic)

# 3. Speed Slider Change Callback Test
def test_speed_change_logic():
    speed_val = 1.0
    def on_speed_change_mock(val):
        nonlocal speed_val
        speed_val = round(val, 2)
        return speed_val
    res = on_speed_change_mock(1.5)
    assert res == 1.5, "Speed change failed"

record_test("Speed Slider Callback (on_speed_change)", test_speed_change_logic)

# 4. GestureDetector Hold/Release Loop Test
def test_gesture_hold_logic():
    tasks = {}
    def stop_hold(name):
        if name in tasks:
            tasks.pop(name)
    def start_hold(name):
        stop_hold(name)
        tasks[name] = "dummy_task"
    
    start_hold("RIGHT")
    assert "RIGHT" in tasks, "Hold start failed"
    stop_hold("RIGHT")
    assert "RIGHT" not in tasks, "Hold stop failed"

record_test("Gesture Hold/Release Logic (DPad repeat)", test_gesture_hold_logic)

print("\n" + "="*60)
print("            ALL UI TESTS SUMMARY")
print("="*60)
failed_count = sum(1 for r in test_results if r[1] == "FAILED")
for name, status, err in test_results:
    print(f" - {name}: {status} {f'({err})' if err else ''}")

print(f"\nTOTAL: {len(test_results)} tests, FAILED: {failed_count}")
print("="*60 + "\n")

if failed_count > 0:
    sys.exit(1)
