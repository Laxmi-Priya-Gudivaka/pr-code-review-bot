#!/usr/bin/env python3
"""
AI-powered PR code review (OpenRouter)

• Scans every changed .java file in the PR.
• Sends full file content to an OpenRouter model.
• Expects JSON list [{"line": int, "message": str}, …].
• Posts inline review comments and requests changes.
• Fails the workflow (exit 1) when issues are found.
"""

import os, sys, json
from github import Github
from openai import OpenAI   # ≥1.0 SDK

# ──────────────────────────────────────────────────────────────
def main() -> int:
    # required env vars
    repo_name = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    gh_token  = os.getenv("GITHUB_TOKEN")
    or_key    = os.getenv("OPENROUTER_AI_API_KEY")

    if not all([repo_name, pr_number, gh_token, or_key]):
        print("❌ Missing environment variables "
              "(GITHUB_REPOSITORY, PR_NUMBER, GITHUB_TOKEN, OPENROUTER_AI_API_KEY)")
        return 1

    pr_number = int(pr_number)

    # GitHub client
    gh   = Github(gh_token)
    repo = gh.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    # OpenRouter client via new openai SDK
    client = OpenAI(
        api_key = or_key,
        base_url = "https://openrouter.ai/api/v1"
    )

    comments, issues_found = [], False

    # iterate changed files
    for f in pr.get_files():
        if not f.patch or not f.filename.endswith(".java"):
            continue

        file_content = repo.get_contents(f.filename, ref=pr.head.ref).decoded_content.decode()

        prompt = f"""
You are a strict Java code-review assistant. Review the code below and output
ONLY JSON — a list of objects: {{ "line": int, "message": str }} for every
issue you find. Return an empty list if there are no issues.

```java
{file_content}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages    = [ {"role":"user","content":prompt} ],
            max_tokens  = 512,
            temperature = 0,
        )
        # feedback = json.loads(resp.choices[0].message.content)
        raw_output = resp.choices[0].message.content
        if raw_output.startswith("```"):
            raw_output = "\n".join(raw_output.split("\n")[1:-1]).strip()

        print("Raw model output after cleaning:", raw_output)
        feedback = json.loads(raw_output)
        print("Raw model output:", raw_output)  # <-- add this line to debug
        feedback = json.loads(raw_output)
    except Exception as e:
        print(f"❌ OpenRouter call/parsing failed: {e}")
        return 1

    for issue in feedback:
        issues_found = True
        comments.append({
            "path" : f.filename,
            "line" : issue["line"],
            "side" : "RIGHT",
            "body" : issue["message"]
        })

    # create PR review
    if issues_found:
        pr.create_review(
            body    = "Automated review found issues – please fix before merging.",
            event   = "REQUEST_CHANGES",
            comments= comments
        )
        print("🔴 Requested changes posted.")
        return 1          # fail workflow
    else:
        pr.create_review(body="✅ Automated review: no issues.", event="APPROVE")
        print("🟢 No issues found.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
