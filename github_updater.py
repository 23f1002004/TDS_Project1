import os
import base64
import requests
from datetime import datetime

GITHUB_API = "https://api.github.com"

def clone_repo_locally(repo_url, local_dir="temp_repo"):
    if not os.path.exists(local_dir):
        os.system(f"git clone {repo_url} {local_dir}")
    return local_dir

def update_repo_via_api(repo_full_name, files_to_update, github_token, branch="main"):
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    commit_shas = {}
    for path, content in files_to_update.items():
        if not isinstance(content, str):
            content = str(content)

        url = f"{GITHUB_API}/repos/{repo_full_name}/contents/{path}?ref={branch}"

        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None

        data = {
            "message": f"Round 2 update — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}: update {path}",
            "content": base64.b64encode(content.encode()).decode(),
        }
        if sha:
            data["sha"] = sha
        data["branch"] = branch

        try:
            resp = requests.put(url, headers=headers, json=data)
            resp.raise_for_status()
            commit_shas[path] = resp.json().get("commit", {}).get("sha")
        except Exception as e:
            print(f"Failed to update {path}: {e}")

    pages_url = f"https://{repo_full_name.split('/')[0]}.github.io/{repo_full_name.split('/')[1]}"
    repo_url = f"https://github.com/{repo_full_name}"

    return {
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": branch,
        "commits": commit_shas
    }