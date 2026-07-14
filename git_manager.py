#!/usr/bin/env python3
"""Recursively manage git repositories under a root path.

Subcommands:
  status <root>   Report repos that have local changes (uncommitted, staged,
                  untracked, or unpushed commits).
  update <root>   Checkout the default branch (main/master) and pull. Repos
                  with blocking local changes or git errors are skipped and
                  logged as failures.

Results are printed to the console and written to a timestamped log file in
the current working directory.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime


def run_git(repo, *args):
    """Run a git command in repo, returning (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def find_repos(root):
    """Yield every git repo under root, without descending into found repos."""
    root = os.path.abspath(root)
    for dirpath, dirnames, _ in os.walk(root):
        if ".git" in dirnames:
            yield dirpath
            # Don't descend further: a found repo is one project.
            dirnames[:] = []
        else:
            # Skip hidden directories to avoid noise (e.g. caches).
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]


def get_default_branch(repo):
    """Return the preferred default branch name, or None if undeterminable."""
    code, out, _ = run_git(repo, "branch", "--list", "--format=%(refname:short)")
    branches = out.splitlines() if code == 0 else []

    for preferred in ("main", "master"):
        if preferred in branches:
            return preferred

    # Fall back to the remote HEAD symbolic ref (e.g. origin/HEAD -> origin/dev).
    code, out, _ = run_git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if code == 0 and out:
        return out.rsplit("/", 1)[-1]

    return None


def get_status(repo):
    """Return a dict describing the local state of a repo."""
    info = {
        "uncommitted": False,
        "staged": False,
        "untracked": False,
        "unpushed": False,
        "branch": None,
        "details": [],
    }

    code, branch, _ = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    info["branch"] = branch if code == 0 else "?"

    # Refresh the index stat-cache so staged vs unstaged is reported
    # accurately; a stale cache can mislabel worktree changes as staged.
    run_git(repo, "update-index", "-q", "--refresh")

    code, out, _ = run_git(repo, "status", "--porcelain")
    if code == 0:
        for line in out.splitlines():
            index_status, worktree_status = line[0], line[1]
            if index_status == "?" and worktree_status == "?":
                info["untracked"] = True
            else:
                if index_status not in (" ", "?"):
                    info["staged"] = True
                if worktree_status not in (" ", "?"):
                    info["uncommitted"] = True

    # Unpushed commits: any local branch ahead of its upstream.
    code, out, _ = run_git(
        repo, "for-each-ref", "--format=%(refname:short) %(upstream:track)",
        "refs/heads",
    )
    if code == 0:
        for line in out.splitlines():
            if "ahead" in line:
                info["unpushed"] = True
                break

    labels = []
    if info["staged"]:
        labels.append("staged")
    if info["uncommitted"]:
        labels.append("uncommitted")
    if info["untracked"]:
        labels.append("untracked")
    if info["unpushed"]:
        labels.append("unpushed")
    info["details"] = labels
    return info


def has_blocking_changes(status):
    """Changes that would block a checkout/pull (untracked files are fine)."""
    return status["staged"] or status["uncommitted"]


def cmd_status(repos):
    """Return (summary_lines, log_lines) for the status subcommand."""
    summary = []
    log = []
    dirty = 0

    for repo in repos:
        status = get_status(repo)
        if status["details"]:
            dirty += 1
            labels = ", ".join(status["details"])
            line = f"[CHANGES] {repo} (on {status['branch']}): {labels}"
            summary.append(line)
            log.append(line)
        else:
            log.append(f"[clean]   {repo} (on {status['branch']})")

    header = f"Scanned {len(repos)} repo(s): {dirty} with local changes, " \
             f"{len(repos) - dirty} clean."
    summary.insert(0, header)
    log.insert(0, header)
    return summary, log


def cmd_update(repos):
    """Return (summary_lines, log_lines) for the update subcommand."""
    summary = []
    log = []
    updated = 0
    failures = []

    for repo in repos:
        ok, message = update_repo(repo)
        if ok:
            updated += 1
            log.append(f"[updated] {repo}: {message}")
        else:
            failures.append((repo, message))
            log.append(f"[FAILED]  {repo}: {message}")

    header = f"Processed {len(repos)} repo(s): {updated} updated, " \
             f"{len(failures)} failed."
    summary.append(header)
    if failures:
        summary.append("")
        summary.append("Failures (also in log file):")
        for repo, message in failures:
            summary.append(f"  {repo}: {message}")

    log.insert(0, header)
    return summary, log


def update_repo(repo):
    """Checkout the default branch and pull. Return (success, message)."""
    branch = get_default_branch(repo)
    if branch is None:
        return False, "could not determine default branch (main/master)"

    status = get_status(repo)
    if has_blocking_changes(status):
        labels = ", ".join(status["details"])
        return False, f"skipped, local changes present ({labels})"

    if status["branch"] != branch:
        code, _, err = run_git(repo, "checkout", branch)
        if code != 0:
            return False, f"checkout {branch} failed: {err or 'unknown error'}"

    code, out, err = run_git(repo, "pull", "--ff-only")
    if code != 0:
        return False, f"pull failed: {err or out or 'unknown error'}"

    return True, f"on {branch}, {out.splitlines()[0] if out else 'up to date'}"


def write_log(mode, log_lines):
    """Write log lines to a timestamped file, returning the path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.abspath(f"git_manager_{mode}_{timestamp}.log")
    with open(path, "w") as handle:
        handle.write(f"git_manager {mode} run at {datetime.now().isoformat()}\n")
        handle.write("\n".join(log_lines) + "\n")
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Recursively report or update git repositories.",
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    for name, help_text in (
        ("status", "Report repos with local changes."),
        ("update", "Checkout the default branch and pull each repo."),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("root", help="Root directory to scan.")

    args = parser.parse_args()

    if not os.path.isdir(args.root):
        parser.error(f"root path is not a directory: {args.root}")

    print(f"Scanning for git repositories under {os.path.abspath(args.root)} ...")
    repos = sorted(find_repos(args.root))
    if not repos:
        print("No git repositories found.")
        return 0

    if args.mode == "status":
        summary, log_lines = cmd_status(repos)
    else:
        summary, log_lines = cmd_update(repos)

    print("\n".join(summary))
    log_path = write_log(args.mode, log_lines)
    print(f"\nFull log written to: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
