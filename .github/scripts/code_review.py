import os
from github import Github

def get_pr_number():
    # GITHUB_REF looks like: refs/pull/1/merge or refs/pull/1/head
    ref = os.getenv("GITHUB_REF", "")
    parts = ref.split('/')
    if len(parts) >= 3 and parts[1] == 'pull':
        pr_num = parts[2]
        if pr_num.isdigit():
            return int(pr_num)
    raise ValueError("Could not parse PR number from GITHUB_REF")

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not found in environment")
        return 1

    repo_name = os.getenv("GITHUB_REPOSITORY")
    if not repo_name:
        print("GITHUB_REPOSITORY not found in environment")
        return 1

    pr_number = get_pr_number()

    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    print(f"Reviewing PR #{pr_number}")

    comments = []

    for file in pr.get_files():
        if file.filename.endswith(".java"):
            patch = file.patch
            if patch and "System.out.println" in patch:
                # Find position of offending line in the patch
                lines = patch.split('\n')
                position = None
                for i, line in enumerate(lines):
                    if "System.out.println" in line:
                        position = i + 1  # GitHub API positions start at 1
                        break

                if position is not None:
                    comments.append({
                        "path": file.filename,
                        "position": position,
                        "body": "Avoid using System.out.println; use a logger instead."
                    })
                    print(f"Issue found in {file.filename}")

    if comments:
        pr.create_review(
            body="Automated review found issues. Please fix before merging.",
            event="REQUEST_CHANGES",
            comments=comments
        )
        print("Requested changes in review. Blocking merge.")
        return 1
    else:
        pr.create_review(
            body="Automated review: No issues found. Approved.",
            event="APPROVE"
        )
        print("No issues found. Approved.")
        return 0

if __name__ == "__main__":
    exit(main())
