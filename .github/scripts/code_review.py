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
import json

from openai import OpenAI


def main():
    # Read environment variables
    repo_name = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    openrouter_api_key = os.getenv("OPENROUTER_AI_API_KEY")
    client = OpenAI(openrouter_api_key)
    github_token = os.getenv("GITHUB_TOKEN")

    if not repo_name or not pr_number or not openrouter_api_key or not github_token:
        print("Missing environment variables. Please set GITHUB_REPOSITORY, PR_NUMBER, GITHUB_TOKEN, and OPENROUTER_API_KEY.")
        return 1

    try:
        pr_number = int(pr_number)
    except ValueError:
        print("PR_NUMBER must be an integer.")
        return 1

    # Initialize GitHub client
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Initialize OpenAI client (OpenRouter)
    client = OpenAI(api_key=openrouter_api_key)

    files = pr.get_files()
    issues_found = False
    comments = []

    for file in files:
        filename = file.filename
        patch = file.patch  # diff data

        if not patch:
            continue

        # Get full file content at PR HEAD commit
        file_contents = repo.get_contents(filename, ref=pr.head.ref)
        content_str = file_contents.decoded_content.decode()

        # Prepare prompt for the code review model
        prompt = f"""
You are a code review assistant. Review the following Java code for bad practices or issues.
Give me a list of line numbers and messages for required changes.

Code:
{content_str}

Only reply in JSON format as a list of objects with "line" and "message" fields.
"""

        try:
            response = client.chat.completions.create(
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

        # Add comments based on feedback
        for issue in feedback:
            issues_found = True
            comments.append({
                "path": filename,
                "line": issue["line"],
                "side": "RIGHT",
                "body": issue["message"]
            })

    # Create PR review
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

