# #!/usr/bin/env python3
# """
# Simplest PR-review bot:
# • Scans Java diffs for 'System.out.println'.
# • Posts ONE top-level PR comment listing every offending file.
# • Exits 1 when it posts a warning, causing the job to fail.
# """

# import os, json, sys
# from github import Github

# token = os.environ["GITHUB_TOKEN"]
# gh = Github(token)

# # event JSON gives us repo + PR number
# with open(os.environ["GITHUB_EVENT_PATH"]) as f:
#     ev = json.load(f)

# repo = gh.get_repo(os.environ["GITHUB_REPOSITORY"])
# pr    = repo.get_pull(ev["pull_request"]["number"])

# violations = []

# for f in pr.get_files():
#     if f.filename.endswith(".java") and "System.out.println" in (f.patch or ""):
#         violations.append(f.filename)

# # post ONE comment if needed
# if violations:
#     body = (
#         "🔴 **Automated review:** `System.out.println` found in these files:\n"
#         + "\n".join(f"- `{v}`" for v in violations)
#         + "\n\nPlease replace with a proper logger."
#     )
#     pr.create_issue_comment(body)
#     print("Comment posted – failing job.")
#     sys.exit(1)

# print("No issues found.")

# .github/scripts/code_review.py

import os
import sys
from github import Github
import openai
import json

def main():
    # Read environment variables
    repo_name = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if not repo_name or not pr_number or not openrouter_api_key or not github_token:
        print("Missing environment variables. Please set GITHUB_REPOSITORY, PR_NUMBER, OPENROUTER_API_KEY, and GITHUB_TOKEN.")
        return 1

    try:
        pr_number = int(pr_number)
    except ValueError:
        print("PR_NUMBER environment variable must be an integer.")
        return 1

    # Initialize GitHub and OpenAI clients
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Read all changed files in the PR
    files = pr.get_files()
    issues_found = False
    comments = []

    # Initialize OpenAI with OpenRouter endpoint and key
    openai.api_base = "https://openrouter.ai/api/v1"
    openai.api_key = openrouter_api_key

    for file in files:
        filename = file.filename
        patch = file.patch  # This contains the diff

        if not patch:
            continue

        # For simplicity, check entire file content via the GitHub API
        file_contents = repo.get_contents(filename, ref=pr.head.ref)
        content_str = file_contents.decoded_content.decode()

        # Prepare prompt for code review
        prompt = f"""
You are a code review assistant. Review the following Java code for bad practices or issues.
Give me a list of line numbers and messages for required changes.

Code:
{content_str}

Only reply in JSON format as a list of objects with "line" and "message" fields.
"""

        try:
            response = openai.ChatCompletion.create(
                model="openrouter/ggml-wizard-v1-q4_0",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0,
            )
            review_output = response.choices[0].message.content
            feedback = json.loads(review_output)
        except Exception as e:
            print(f"Error during OpenAI call or parsing response: {e}")
            return 1

        # Add review comments based on feedback
        for issue in feedback:
            issues_found = True
            comments.append({
                "path": filename,
                "line": issue["line"],
                "side": "RIGHT",
                "body": issue["message"]
            })

    # Create review on PR
    if issues_found:
        pr.create_review(
            body="Automated review found issues. Please fix before merging.",
            event="REQUEST_CHANGES",
            comments=comments
        )
        print("Review with requested changes created.")
        return 1
    else:
        pr.create_review(
            body="Automated review found no issues.",
            event="APPROVE"
        )
        print("Review approved.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
