import pychromecast
import zeroconf
from pychromecast.models import CastInfo
from pychromecast.discovery import MDNSServiceInfo

print("Testing direct Chromecast connection with Zeroconf...")
zconf = zeroconf.Zeroconf()
try:
    cast_info = CastInfo(
        services={MDNSServiceInfo("Chromecast-direct._googlecast._tcp.local.")},
        uuid=None,
        model_name="Chromecast",
        friendly_name="Google TV Device",
        host="192.168.1.136",
        port=8009,
        cast_type="cast",
        manufacturer="Google Inc."
    )

    c = pychromecast.Chromecast(cast_info=cast_info, zconf=zconf)
    c.start()
    print("Waiting for connection...")
    c.wait(timeout=3.0)
    print(f"Direct connection SUCCESSFUL! Friendly Name: {c.name}, App: {c.app_display_name}")
    mc = c.media_controller
    print(f"Player State: {mc.status.player_state}")
    c.disconnect()
finally:
    zconf.close()
