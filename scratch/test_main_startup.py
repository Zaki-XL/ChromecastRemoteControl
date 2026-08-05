import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

print("Testing direct import and main.py symbol checks...")
try:
    import main
    print("SUCCESS: main.py imported with no NameError or SyntaxError!")
    assert hasattr(main, 'subprocess'), "subprocess module not imported in main!"
    assert hasattr(main, 'run_supervisor_mode'), "run_supervisor_mode missing!"
    print("SUCCESS: All supervisor symbols and imports verified!")
except Exception as ex:
    print(f"FAILED: {ex}")
    import traceback
    traceback.print_exc()
