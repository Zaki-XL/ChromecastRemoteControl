import inspect
import pychromecast

print("Chromecast.__init__ signature:")
print(inspect.signature(pychromecast.Chromecast.__init__))

from pychromecast.models import CastInfo
from pychromecast.discovery import MDNSServiceInfo

print("\nTrying get_chromecast_from_host with CastInfo...")
try:
    cast_info = CastInfo(
        services={MDNSServiceInfo("Chromecast-direct._googlecast._tcp.local.")},
        uuid=None,
        model_name="Chromecast",
        friendly_name="Chromecast",
        host="192.168.1.136",
        port=8009,
        cast_type="cast",
        manufacturer="Google Inc."
    )
    c = pychromecast.get_chromecast_from_cast_info(cast_info, pychromecast.discovery.SimpleCastListener(lambda cast: None))
    c.wait(timeout=5.0)
    print(f"Connection SUCCESS! Name: {c.name}, App: {c.app_display_name}")
    c.disconnect()
except Exception as ex:
    print(f"Failed: {ex}")
    import traceback
    traceback.print_exc()
