import os
import requests
import json

def notify_evaluation_url(
    email: str,
    task: str,
    round_index: int,
    nonce: str,
    repo_url: str,
    commit_sha: str,
    pages_url: str,
    evaluation_url: str,
):
    payload = {
        "email": email,
        "task": task,
        "round": round_index,
        "nonce": nonce,
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url,
    }

    headers = {"Content-Type": "application/json"}
    delay = 1 
    max_attempts = 5

    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(evaluation_url, headers=headers, data=json.dumps(payload))
            if resp.status_code == 200:
                print(f"[SUCCESS] Notified evaluation URL on attempt {attempt}")
                return True
            else:
                print(f"[WARN] Status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[ERROR] Attempt {attempt} failed: {e}")

        print(f"[INFO] Retrying in {delay}s...")
        import time
        time.sleep(delay)
        delay *= 2

    print("[FAIL] Could not notify evaluation URL after multiple attempts.")
    return False