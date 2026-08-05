import inspect
from pychromecast.controllers.media import MediaController

print("=== set_playback_rate signature & doc ===")
print(inspect.signature(MediaController.set_playback_rate))
print(inspect.getsource(MediaController.set_playback_rate))

print("\n=== enable_subtitle signature & doc ===")
print(inspect.signature(MediaController.enable_subtitle))
print(inspect.getsource(MediaController.enable_subtitle))

print("\n=== disable_subtitle signature & doc ===")
print(inspect.signature(MediaController.disable_subtitle))
print(inspect.getsource(MediaController.disable_subtitle))

print("\n=== seek signature & doc ===")
print(inspect.signature(MediaController.seek))
print(inspect.getsource(MediaController.seek))
