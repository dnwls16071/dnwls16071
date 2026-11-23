import argparse
import re
import subprocess
from html import escape
from pathlib import Path, PurePosixPath
from urllib.parse import quote

DOCS_URL = "https://github.com/dnwls16071/backend-engineering-handbook/blob/main/"
LIMIT = 5
START = "<!-- RECENT_HANDBOOK_DOCS:START -->"
END = "<!-- RECENT_HANDBOOK_DOCS:END -->"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args]).decode("utf-8")


def document_title(repo, path):
    contents = git(repo, "show", f"HEAD:{path}")
    heading = re.search(r"^# +(.+)$", contents, re.MULTILINE)
    title = heading[1].strip() if heading else PurePosixPath(path).stem
    return re.sub(r"([\\\[\]`*_])", r"\\\1", escape(title, quote=False))


def recent_documents(repo):
    current_paths = set(git(repo, "ls-tree", "-r", "--name-only", "-z", "HEAD").split("\0"))
    changed_paths = git(
        repo, "log", "--first-parent", "--diff-merges=first-parent",
        "--no-renames", "--name-only", "--diff-filter=AM", "--format=", "-z",
        "HEAD", "--", ":(glob)**/*.md",
    )
    seen = set()
    rows = []
    for path in changed_paths.split("\0"):
        if path in seen or path not in current_paths:
            continue
        document = PurePosixPath(path)
        if len(document.parts) < 2 or document.parts[0] in {"wiki", ".github"}:
            continue
        if document.name.upper() in {"README.MD", "AGENTS.MD"}:
            continue

        seen.add(path)
        title = document_title(repo, path)
        rows.append(f"- [{title}]({DOCS_URL}{quote(path)})")
        if len(rows) == LIMIT:
            break
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("handbook", type=Path)
    parser.add_argument("readme", type=Path)
    args = parser.parse_args()

    original = args.readme.read_text(encoding="utf-8")
    before, _, remaining = original.partition(START + "\n")
    _, separator, after = remaining.partition(END)
    if original.count(START) != 1 or original.count(END) != 1 or not separator:
        parser.error("Expected one ordered pair of handbook markers in the README.")

    rows = recent_documents(args.handbook)
    if not rows:
        parser.error("No handbook documents found. The README was kept as-is.")
    updated = f"{before}{START}\n" + "\n".join(rows) + f"\n{END}{after}"
    if updated != original:
        args.readme.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
