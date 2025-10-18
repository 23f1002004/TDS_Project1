# Triggering Hugging Face Docker build
import os
import base64
import json
from datetime import datetime
import requests
from flask import Flask, request, jsonify
from llm_builder import generate_app_from_brief
from github_deployer import create_and_push_repo, MIT_LICENSE_TEXT, GITHUB_USER, GITHUB_TOKEN
from github_updater import update_repo_via_api
from notifier import notify_evaluation_url

app = Flask(__name__)

EXPECTED_SECRET = "2546@#$yutiop!2890"
ATTACHMENT_DIR = "attachments"
os.makedirs(ATTACHMENT_DIR, exist_ok=True)
REPO_STORE_FILE = "repo_store.json"

if os.path.exists(REPO_STORE_FILE):
    with open(REPO_STORE_FILE, "r", encoding="utf-8") as f:
        REPO_STORE = json.load(f)
else:
    REPO_STORE = {}

def save_repo_store(store):
    with open(REPO_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def fetch_existing_code_from_github(repo_full_name, github_token):
    """
    Recursively fetch all files from GitHub repo.
    Returns: {filename: content}
    """
    headers = {"Authorization": f"token {github_token}"}
    existing_code = {}

    def fetch_dir(path=""):
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"[WARN] Failed to fetch {path}: {resp.status_code}")
            return
        for item in resp.json():
            if item["type"] == "file":
                file_resp = requests.get(item["download_url"])
                if file_resp.status_code == 200:
                    existing_code[item["name"]] = file_resp.text
            elif item["type"] == "dir":
                fetch_dir(item["path"])

    fetch_dir()
    return existing_code


@app.route("/app-creator", methods=["POST"])
def receive_request():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    required = ["email", "secret", "task", "round", "nonce", "brief", "checks", "evaluation_url"]
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if data["secret"] != EXPECTED_SECRET:
        return jsonify({"error": "Invalid secret"}), 403

    attachments = []
    for attachment in data.get("attachments", []):
        name = attachment.get("name")
        url = attachment.get("url")
        if not (name and url and url.startswith("data:")):
            continue
        try:
            header, encoded = url.split(",", 1)
            binary_data = base64.b64decode(encoded)
            filepath = os.path.join(ATTACHMENT_DIR, name)
            with open(filepath, "wb") as f:
                f.write(binary_data)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            attachments.append({"name": name, "content": content})
        except Exception as e:
            print(f"[ERROR] Failed to decode {name}: {e}")

    print(f" Saved {len(attachments)} attachment(s)")

    task = data["task"]
    brief = data["brief"]
    round_index = data["round"]

    if round_index == 1:
        generated_code = generate_app_from_brief(brief, attachments)
        repo_info = create_and_push_repo(task, generated_code, brief)

        REPO_STORE[task] = {
            "repo_url": repo_info["repo_url"],
            "pages_url": repo_info["pages_url"],
            "commit_sha": "main",
            "repo_full_name": f"{GITHUB_USER}/{task}-app"
        }
        save_repo_store(REPO_STORE)
        print(f"Round 1 repo created for task '{task}'")

    elif round_index == 2:
        if task not in REPO_STORE:
            return jsonify({"error": f"No previous repo found for task {task}"}), 400

        stored_info = REPO_STORE[task]
        repo_full_name = stored_info.get("repo_full_name")
        if not repo_full_name:
            return jsonify({"error": f"'repo_full_name' missing for task {task}"}), 500

        existing_code = fetch_existing_code_from_github(repo_full_name, GITHUB_TOKEN)
        print(f"Fetched {len(existing_code)} existing files for Round 2 LLM input")

        updated_code = generate_app_from_brief(brief, attachments, existing_code)

        for path in updated_code:
            if path.endswith((".html", ".css", ".js")):
                updated_code[path] += f"\n<!-- updated: {datetime.utcnow().isoformat()} -->"


        print(f"--- Round 2 LLM output keys ---")
        for k in updated_code.keys():
            print(f"  {k}")

        files_to_update = updated_code.copy()
        files_to_update.setdefault("LICENSE", MIT_LICENSE_TEXT)
        files_to_update.setdefault("README.md", "# README missing")

        print(f"Pushing {len(files_to_update)} files to {repo_full_name} via GitHub API...")
        final_repo_info = update_repo_via_api(
            repo_full_name=repo_full_name,
            files_to_update=files_to_update,
            github_token=GITHUB_TOKEN
        )

        REPO_STORE[task].update(final_repo_info)
        save_repo_store(REPO_STORE)
        print(f" Round 2 repo updated for task '{task}'")

    else:
        return jsonify({"error": f"Unsupported round {round_index}"}), 400

    notify_success = notify_evaluation_url(
        email=data["email"],
        task=task,
        round_index=round_index,
        nonce=data["nonce"],
        repo_url=REPO_STORE[task]["repo_url"],
        commit_sha=REPO_STORE[task]["commit_sha"],
        pages_url=REPO_STORE[task]["pages_url"],
        evaluation_url=data["evaluation_url"]
    )

    status_msg = "Notified evaluation server successfully" if notify_success else "Failed to notify evaluation server"

    return jsonify({
        "status": "ok",
        "message": f"Round {round_index} processed. {status_msg}",
        "task": task,
        "round": round_index,
        "repo_url": REPO_STORE[task]["repo_url"],
        "pages_url": REPO_STORE[task]["pages_url"]
    }), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=7860)