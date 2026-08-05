import inspect
import pychromecast
from pychromecast.controllers.media import MediaController
try:
    import androidtvremote2
except Exception:
    androidtvremote2 = None

print("=== PyChromecast MediaController Inspection ===")
print("MediaController methods and attributes:")
for attr in dir(MediaController):
    if not attr.startswith("_"):
        print("  -", attr)

print("\n=== AndroidTVRemote Inspection ===")
if androidtvremote2:
    from androidtvremote2.androidtv_remote import AndroidTVRemote
    print("AndroidTVRemote methods:")
    for attr in dir(AndroidTVRemote):
        if not attr.startswith("_"):
            print("  -", attr)
