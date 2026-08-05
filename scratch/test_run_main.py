import sys
import os
import asyncio
import traceback
from unittest.mock import MagicMock

sys.path.insert(0, os.getcwd())

import main

async def run_test():
    print("Testing async main.main(mock_page)...")
    mock_page = MagicMock()
    mock_page.window = MagicMock()
    mock_page.window.width = 420
    mock_page.window.height = 750
    mock_page.window.opacity = 1.0
    mock_page.overlay = []
    
    try:
        await main.main(mock_page)
        print("SUCCESS: async main.main completed without errors!")
    except Exception as e:
        print("CRITICAL EXCEPTION IN ASYNC MAIN:")
        traceback.print_exc()

asyncio.run(run_test())
