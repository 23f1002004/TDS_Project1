import os
import base64
import requests
from datetime import date, datetime

GITHUB_API = "https://api.github.com"
GITHUB_USER = "23f1002004"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

MIT_LICENSE_TEXT = f"""MIT License

Copyright (c) {date.today().year} {GITHUB_USER}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
"""

def generate_readme(task, brief, repo_url):
    return f"""# {task}

## 📘 Overview
This repository contains an auto-generated minimal web app for:
> {brief}

## ⚙️ Setup
Clone the repo and open any HTML files in your browser.

```bash
git clone {repo_url}
cd {task}-app
```"""

def create_and_push_repo(task, generated_code, brief):
    """
    Creates a GitHub repo and uploads all generated files (HTML, CSS, JS, Vue, etc.)
    Returns repo_url, pages_url, and full_name for future updates
    """
    repo_name = f"{task}-app-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    resp = requests.post(
        f"{GITHUB_API}/user/repos",
        headers=headers,
        json={
            "name": repo_name,
            "description": f"Auto-generated app for task: {task}",
            "private": False
        }
    )

    if resp.status_code == 422:
        print(f"[INFO] Repo {repo_name} already exists, skipping creation.")
        repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}"
    elif resp.status_code in [200, 201]:
        repo_data = resp.json()
        repo_url = repo_data["html_url"]
    else:
        raise Exception(f"Repo creation failed: {resp.text}")

    files = generated_code.copy()
    files.setdefault("LICENSE", MIT_LICENSE_TEXT)
    files.setdefault("README.md", generate_readme(task, brief, repo_url))

    for path, content in files.items():
        if not isinstance(content, str):
            content = str(content)
        encoded = base64.b64encode(content.encode()).decode()
        put_resp = requests.put(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}/contents/{path}",
            headers=headers,
            json={
                "message": f"Add/update {path}",
                "content": encoded
            }
        )
        if put_resp.status_code not in [200, 201]:
            raise Exception(f"Failed to upload {path}: {put_resp.text}")

    pages_resp = requests.post(
        f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}/pages",
        headers=headers,
        json={"source": {"branch": "main", "path": "/"}}
    )
    if pages_resp.status_code not in [201, 202]:
        print(f"[WARN] Could not enable GitHub Pages: {pages_resp.text}")

    pages_url = f"https://{GITHUB_USER}.github.io/{repo_name}/"
    repo_full_name = f"{GITHUB_USER}/{repo_name}"

    return {"repo_url": repo_url, "pages_url": pages_url, "repo_full_name": repo_full_name}
