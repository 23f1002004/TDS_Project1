import os
import google.generativeai as genai
import json
from datetime import datetime

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=api_key)


def generate_app_from_brief(brief: str, attachments: list, existing_code: dict = None) -> dict:
    model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")

    prompt_parts = [
        "You are an expert web developer.",
        f"Task brief: {brief}",
    ]

    if attachments:
        prompt_parts.append("Attachments (name + first 200 chars):")
        for att in attachments:
            name = att.get("name", "Unnamed")
            content = att.get("content", "")
            prompt_parts.append(f"- {name}: {content[:200]}")

    if existing_code:
        prompt_parts.append("Existing files (name + first 200 chars):")
        for fname, content in existing_code.items():
            prompt_parts.append(f"- {fname}: {content[:200]}")
        prompt_parts.append(
            "Update or refactor these files according to the new brief. "
            "Keep previous features unless explicitly told otherwise. "
            "**Add new functionality, scripts, pages, or styling if described in the brief.** "
            "Do not introduce unrelated content."
        )
    else:
        prompt_parts.append(
            "This is a fresh app. Generate all necessary files according to the brief."
        )

    prompt_parts.append(
        "Return only a single JSON object. Keys = filenames (like index.html, styles.css, script.js, README.md, LICENSE). "
        "Values = full file content as string. Ensure all keys exist even if empty."
    )

    prompt = "\n\n".join(prompt_parts)

    response = model.generate_content(prompt)
    text = response.text.strip()

    generated = {}
    try:
        generated = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            try:
                generated = json.loads(text[start:end])
            except Exception:
                pass

    essential_files = ["index.html", "styles.css", "script.js", "README.md", "LICENSE"]
    fallback = {
        "index.html": "<!DOCTYPE html>\n<html><body>Fallback HTML</body></html>",
        "styles.css": "/* fallback CSS */",
        "script.js": "// fallback JS",
        "README.md": "# README\nFallback readme",
        "LICENSE": "MIT License\nFallback license"
    }

    final_files = {}
    for f in essential_files:
        final_files[f] = str(generated.get(f, fallback[f])).strip() or fallback[f]

    for k, v in generated.items():
        if k not in final_files:
            final_files[str(k)] = str(v)

    ts = int(datetime.utcnow().timestamp())
    if "index.html" in final_files:
        html = final_files["index.html"]
        html = html.replace('href="styles.css"', f'href="styles.css?v={ts}"')
        html = html.replace('src="script.js"', f'src="script.js?v={ts}"')
        final_files["index.html"] = html

    return final_files