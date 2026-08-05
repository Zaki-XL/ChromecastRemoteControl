import inspect
import pychromecast
from pychromecast.controllers.media import MediaController
import androidandroidtvremote2 = None
try:
    import androidtvremote2
except Exception:
    pass

print("=== PyChromecast MediaController Inspection ===")
print("MediaController methods and attributes:")
for attr in dir(MediaController):
    if not attr.startswith("_"):
        print("  -", attr)

print("\nMediaController status inspection:")
from pychromecast.controllers.media import MediaStatus
for attr in dir(MediaStatus):
    if not attr.startswith("_"):
        print("  - status attr:", attr)

print("\n=== AndroidTVRemote Inspection ===")
if hasattr(pychromecast, 'controllers'):
    print("pychromecast controllers:", dir(pychromecast.controllers))

try:
    from androidtvremote2.androidtv_remote import AndroidTVRemote
    print("AndroidTVRemote methods:")
    for attr in dir(AndroidTVRemote):
        if not attr.startswith("_"):
            print("  -", attr)
except Exception as ex:
    print("AndroidTVRemote error:", ex)
