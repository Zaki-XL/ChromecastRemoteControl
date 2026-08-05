# -*- coding: utf-8 -*-
import os
import subprocess
import sys

# 1. 親プロセスから引き継がれた不要な Git 環境変数を完全に削除
for var in ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR"]:
    if var in os.environ:
        print(f"Clearing env var: {var} (Value: {os.environ[var]})")
        del os.environ[var]

def run_cmd(args):
    print(f"\nRunning: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if res.returncode != 0:
        print(f"--> FAILED (Exit Code: {res.returncode})")
        print("Stdout:", res.stdout.strip())
        print("Stderr:", res.stderr.strip())
        return False
    else:
        print("--> SUCCESS")
        print("Stdout:", res.stdout.strip())
        return True

# 2. git init
if not run_cmd(["git", "init"]):
    sys.exit(1)

# 3. git config
run_cmd(["git", "config", "user.name", "AI Assistant"])
run_cmd(["git", "config", "user.email", "assistant@ai.local"])

# 4. git add .
if not run_cmd(["git", "add", "."]):
    sys.exit(1)

# 5. git commit
run_cmd(["git", "commit", "-m", "Initial commit: Chromecast Remote Control with logging rotation and socket fixes"])
