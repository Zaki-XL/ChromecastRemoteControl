import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
import logging

logging.basicConfig(level=logging.INFO)
print("Testing imports...")
import remote_client
import cast_client
import config_manager

print("Testing ConfigManager...")
cfg = config_manager.ConfigManager()
print(f"Preferred Language: {cfg.preferred_language}")
print(f"Window Size: {cfg.window_width}x{cfg.window_height}")

print("Testing CastClient & RemoteClient instantiation...")
rc = remote_client.AndroidTVRemoteClient("127.0.0.1", "certs/cert.pem", "certs/key.pem")
cc = cast_client.ChromecastCastClient("127.0.0.1")

print("All module sanity checks PASSED!")
