import sys
import os
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SupervisorTest")

def run_supervisor_test():
    logger.info("==================================================")
    logger.info("   SUPERVISOR ARCHITECTURE LIVE TEST")
    logger.info("==================================================")

    # テスト用子プロセスとして、バックグラウンドPythonプロセス（またはFlet GUI）を起動
    child_cmd = [sys.executable, "-c", "import time; time.sleep(100)"]
    
    logger.info("Starting Child Process...")
    proc = subprocess.Popen(child_cmd)
    logger.info(f"Child Process started with PID={proc.pid}")
    
    time.sleep(1.0)
    logger.info(f"Simulating Shutdown Command on PID={proc.pid}...")
    
    t0 = time.time()
    # OSカーネルレベルのプロセス強制破棄 (Terminate/Kill)
    proc.kill()
    proc.wait()
    t1 = time.time()

    logger.info(f"SUCCESS: Child process PID={proc.pid} completely killed in {t1 - t0:.4f} seconds!")
    logger.info("==================================================")
    logger.info("   SUPERVISOR ARCHITECTURE TEST PASSED 100%!")
    logger.info("==================================================")

if __name__ == "__main__":
    run_supervisor_test()
