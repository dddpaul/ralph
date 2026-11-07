"""R-INFRA-6 merge provenance on master: plugins/ralph/scripts/master-provenance.sh (TASK-318).

Each fixture builds a scratch repository with a bare origin, lands one kind of
commit on master after origin/master, and runs the checker over
``origin/master..master``. Approved fixtures must print only ``ok`` lines and
exit 0; flagged ones must print a ``FLAG`` line for the commit and exit 1.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

SCRIPT = REPO_ROOT / "plugins/ralph/scripts/master-provenance.sh"
TASK_FILE = "backlog/tasks/task-5 - Add-feature.md"


class Repo:
    """A work clone with a bare origin, both under one scratch directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_") or key == "GIT_EXEC_PATH"
        }
        self.env.update(
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="t",
            GIT_AUTHOR_EMAIL="t@example.com",
            GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL="t@example.com",
        )
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "master", str(root / "origin.git")],
            check=True,
            env=self.env,
        )
        self.work = self.clone("work")

    def clone(self, name: str) -> Path:
        path = self.root / name
        subprocess.run(
            ["git", "clone", "-q", str(self.root / "origin.git"), str(path)],
            check=True,
            env=self.env,
        )
        return path

    def git(self, *args: str, cwd: Path | None = None, check: bool = True) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or self.work,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def commit(
        self, message: str, files: dict[str, str], cwd: Path | None = None
    ) -> str:
        base = cwd or self.work
        for rel, text in files.items():
            path = base / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, "utf-8")
            self.git("add", "--", rel, cwd=base)
        self.git("commit", "-q", "-m", message, cwd=base)
        return self.git("rev-parse", "HEAD", cwd=base)

    def note(self, text: str) -> str:
        """Append a line to TASK-5's notes in a task-file-only commit."""
        path = self.work / TASK_FILE
        return self.commit(
            "task-5: record review", {TASK_FILE: path.read_text("utf-8") + text + "\n"}
        )

    def check(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=self.work,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    r = Repo(tmp_path)
    r.commit(
        "init", {"app.py": "a = 1\nb = 2\nc = 3\n", TASK_FILE: "# TASK-5\n\n## Notes\n"}
    )
    r.git("push", "-q", "origin", "master")
    return r


def approved_task_branch(repo: Repo, change: str = "a = 10\nb = 2\nc = 3\n") -> str:
    """Create task-5 with one reviewed code commit plus its APPROVED note; return the reviewed SHA."""
    repo.git("checkout", "-q", "-b", "task-5")
    reviewed = repo.commit("task-5: add feature", {"app.py": change})
    repo.note(f"Review: APPROVED {reviewed}")
    return reviewed


def merge_task_branch(repo: Repo, subject: str = "Merge task-5: add feature") -> str:
    repo.git("checkout", "-q", "master")
    repo.git("merge", "-q", "--no-ff", "-m", subject, "task-5")
    repo.git("branch", "-q", "-D", "task-5")
    return repo.git("rev-parse", "HEAD")


def assert_approved(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout and "FLAG" not in result.stdout


def assert_flagged(
    result: subprocess.CompletedProcess[str], repo: Repo, sha: str, reason: str
) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"FLAG {repo.git('rev-parse', '--short', sha)} " in result.stdout
    assert reason in result.stdout


# --- approved ---------------------------------------------------------------


def test_approves_design_commit(repo: Repo) -> None:
    repo.commit("Sketch the design", {"design/feature-brainstorm.md": "idea\n"})
    result = repo.check()
    assert_approved(result)
    assert "master-branch guard allowlist" in result.stdout


def test_approves_task_file_commit(repo: Repo) -> None:
    repo.note("Status: Done")
    result = repo.check()
    assert_approved(result)
    assert "task-file commit" in result.stdout


def test_approves_reviewed_merge_whose_branch_was_deleted(repo: Repo) -> None:
    reviewed = approved_task_branch(repo)
    merge_task_branch(repo)
    assert repo.git("branch", "--list", "task-5") == ""
    result = repo.check()
    assert_approved(result)
    assert f"reviewed at {repo.git('rev-parse', '--short', reviewed)}" in result.stdout


def test_approves_reviewed_fast_forward(repo: Repo) -> None:
    approved_task_branch(repo)
    repo.git("checkout", "-q", "master")
    repo.git("merge", "-q", "--ff-only", "task-5")
    result = repo.check()
    assert_approved(result)
    assert "fast-forwarded TASK-5 work" in result.stdout
    assert "task-file commit" in result.stdout


def test_approves_clean_integration_merge(repo: Repo) -> None:
    other = repo.clone("other")
    repo.commit("task-6: other host work", {"lib.py": "x = 1\n"}, cwd=other)
    repo.git("push", "-q", "origin", "master", cwd=other)
    repo.commit("Sketch the design", {"design/d.md": "d\n"})
    repo.git("fetch", "-q", "origin")
    sha = repo.git("rev-parse", "origin/master")
    repo.git(
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "Merge origin/master into master",
        "-m",
        f"Integrated-Origin: {sha}",
        sha,
    )
    result = repo.check()
    assert_approved(result)
    assert "integration merge of origin/master" in result.stdout


def test_approves_hand_resolved_merge_with_integration_review(repo: Repo) -> None:
    approved_task_branch(repo)
    repo.git("checkout", "-q", "master")
    repo.commit("Tweak on master", {".claude/x.md": "x\n"})
    repo.git("merge", "-q", "--no-ff", "--no-commit", "task-5")
    (repo.work / "app.py").write_text("a = 10\nb = 20\nc = 3\n", "utf-8")
    repo.git("commit", "-q", "-am", "Merge task-5: add feature")
    merge = repo.git("rev-parse", "HEAD")
    repo.note(f"Integration review: APPROVED {merge}")
    result = repo.check()
    assert_approved(result)
    assert "hand-resolved with an integration review" in result.stdout


def test_approves_project_bookkeeping_paths_after_review(repo: Repo) -> None:
    approved_task_branch(repo)
    repo.commit(
        ".claude conf",
        {".claude/task-reviewer.conf": "master_bookkeeping_paths=VERSION\n"},
    )
    repo.commit("task-5: bump version", {"VERSION": "1.1\n"})
    merge_task_branch(repo)
    assert_approved(repo.check())


# --- flagged ----------------------------------------------------------------


def test_flags_clean_merge_from_unreviewed_task_branch(repo: Repo) -> None:
    repo.git("checkout", "-q", "-b", "task-5")
    repo.commit("task-5: add feature", {"app.py": "a = 10\nb = 2\nc = 3\n"})
    merge = merge_task_branch(repo)
    assert_flagged(repo.check(), repo, merge, "no Review: APPROVED note of TASK-5")


def test_flags_clean_merge_from_arbitrary_side_branch(repo: Repo) -> None:
    repo.git("checkout", "-q", "-b", "feature")
    repo.commit("Add feature", {"app.py": "a = 10\nb = 2\nc = 3\n"})
    repo.git("checkout", "-q", "master")
    repo.git("merge", "-q", "--no-ff", "-m", "Merge branch 'feature'", "feature")
    merge = repo.git("rev-parse", "HEAD")
    assert_flagged(
        repo.check(),
        repo,
        merge,
        "merge names no task and has no Integrated-Origin trailer",
    )


def test_flags_stale_verdict_merge(repo: Repo) -> None:
    approved_task_branch(repo)
    repo.commit(
        "task-5: more work after the review", {"app.py": "a = 10\nb = 2\nc = 30\n"}
    )
    merge = merge_task_branch(repo)
    assert_flagged(repo.check(), repo, merge, "no Review: APPROVED note of TASK-5")


def test_flags_stale_verdict_fast_forward(repo: Repo) -> None:
    approved_task_branch(repo)
    late = repo.commit(
        "task-5: more work after the review", {"app.py": "a = 10\nb = 2\nc = 30\n"}
    )
    repo.git("checkout", "-q", "master")
    repo.git("merge", "-q", "--ff-only", "task-5")
    assert_flagged(repo.check(), repo, late, "not covered by a Review: APPROVED note")


def test_flags_hand_edited_merge_without_integration_review(repo: Repo) -> None:
    approved_task_branch(repo)
    repo.git("checkout", "-q", "master")
    repo.git("merge", "-q", "--no-ff", "--no-commit", "task-5")
    (repo.work / "app.py").write_text("a = 10\nb = 2\nc = 3\nevil = 1\n", "utf-8")
    repo.git("commit", "-q", "-am", "Merge task-5: add feature")
    merge = repo.git("rev-parse", "HEAD")
    assert_flagged(
        repo.check(), repo, merge, "tree differs from git merge-tree of its parents"
    )


def test_flags_integration_trailer_not_on_origin(repo: Repo) -> None:
    repo.git("checkout", "-q", "-b", "side")
    side = repo.commit("Side work", {"lib.py": "x = 1\n"})
    repo.git("checkout", "-q", "master")
    repo.git(
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "Merge origin/master",
        "-m",
        f"Integrated-Origin: {side}",
        side,
    )
    merge = repo.git("rev-parse", "HEAD")
    assert_flagged(repo.check(), repo, merge, "is not reachable from origin/master")


def test_flags_integration_trailer_naming_another_commit(repo: Repo) -> None:
    base = repo.git("rev-parse", "HEAD")
    repo.git("checkout", "-q", "-b", "side")
    side = repo.commit("Side work", {"lib.py": "x = 1\n"})
    repo.git("checkout", "-q", "master")
    repo.git(
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "Merge origin/master",
        "-m",
        f"Integrated-Origin: {base}",
        side,
    )
    merge = repo.git("rev-parse", "HEAD")
    assert_flagged(repo.check(), repo, merge, "trailer does not name the second parent")


def test_flags_direct_code_commit(repo: Repo) -> None:
    sha = repo.commit("task-5: sneak in code", {"app.py": "a = 0\n"})
    assert_flagged(repo.check(), repo, sha, "direct commit outside the guard allowlist")


def test_flags_task_prefix_commit_mixing_code_and_task_file(repo: Repo) -> None:
    text = (repo.work / TASK_FILE).read_text("utf-8")
    sha = repo.commit(
        "task-5: mark Done", {TASK_FILE: text + "Done\n", "app.py": "a = 0\n"}
    )
    assert_flagged(repo.check(), repo, sha, "direct commit outside the guard allowlist")


def test_flags_task_file_commit_without_task_prefix(repo: Repo) -> None:
    text = (repo.work / TASK_FILE).read_text("utf-8")
    sha = repo.commit("Mark Done", {TASK_FILE: text + "Done\n"})
    assert_flagged(repo.check(), repo, sha, "direct commit outside the guard allowlist")


def test_unknown_range_is_a_usage_error(repo: Repo) -> None:
    result = repo.check("nope..master")
    assert result.returncode == 2
    assert "cannot resolve" in result.stderr


def test_since_setting_leaves_out_older_history(repo: Repo) -> None:
    old = repo.commit(
        "task-5: unreviewed code from before the convention", {"app.py": "a = 0\n"}
    )
    assert repo.check().returncode == 1
    repo.commit(
        "adopt", {".claude/task-reviewer.conf": f"master_provenance_since={old}\n"}
    )
    result = repo.check()
    assert_approved(result)
    assert repo.git("rev-parse", "--short", old) not in result.stdout


def test_explicit_range_ignores_since_setting(repo: Repo) -> None:
    old = repo.commit(
        "task-5: unreviewed code from before the convention", {"app.py": "a = 0\n"}
    )
    repo.commit(
        "adopt", {".claude/task-reviewer.conf": f"master_provenance_since={old}\n"}
    )
    assert_flagged(
        repo.check("origin/master..master"),
        repo,
        old,
        "direct commit outside the guard allowlist",
    )


def flat(text: str) -> str:
    return " ".join(text.split())


def test_r_infra_6_requires_the_checker_and_names_each_allowed_commit() -> None:
    text = flat(
        (
            REPO_ROOT
            / "plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md"
        ).read_text("utf-8")
    )
    body = text[text.index("## R-INFRA-6: ") : text.index("## R-INFRA-7: ")]
    for needle in (
        "`scripts/master-provenance.sh`",
        "Every `FLAG` line is a blocking R-INFRA-6 finding",
        "`backlog/{tasks,drafts,archive,completed}/`",
        "`Review: APPROVED <sha>`",
        "No branch ref needs to survive.",
        "A verdict recorded for an earlier SHA does not approve any other commit made after it",
        "`Integrated-Origin: <sha>`",
        "reachable from origin's base branch",
        "`git merge-tree --write-tree`",
        "it is not proof of approval",
        "`Integration review: APPROVED <merge-sha>`",
    ):
        assert needle in body, needle


@pytest.mark.parametrize(
    "path", ["CLAUDE.md", "plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md"]
)
def test_review_step_records_the_reviewed_sha(path: str) -> None:
    step = next(
        line
        for line in (REPO_ROOT / path).read_text("utf-8").splitlines()
        if line.startswith("4. **Review:**")
    )
    assert (
        '`backlog task edit <id> --append-notes "Review: APPROVED $(git rev-parse HEAD)"`'
        in step
    )
    assert "run on the task branch tip that was reviewed" in step


def test_flags_code_commit_made_on_master_before_a_reviewed_branch_forked(
    repo: Repo,
) -> None:
    sneak = repo.commit("task-5: sneak change on master", {"app.py": "a = 0\n"})
    approved_task_branch(repo, change="a = 0\nb = 1\n")
    merge_task_branch(repo)
    assert_flagged(repo.check(), repo, sneak, "not covered by a Review: APPROVED note")


def test_checks_all_of_master_without_a_remote_tracking_branch(repo: Repo) -> None:
    repo.git("update-ref", "-d", "refs/remotes/origin/master")
    result = repo.check()
    assert result.returncode == 1
    assert "no origin/master; checking all of master" in result.stderr
    assert "FLAG" in result.stdout


@pytest.mark.parametrize("flag", ["--remote", "--base"])
def test_option_without_value_is_a_usage_error(repo: Repo, flag: str) -> None:
    assert repo.check(flag).returncode == 2


# --- a project nested in a subdirectory of its repo (TASK-329) --------------

PROJECT = "proj"
NESTED_TASK_FILE = f"{PROJECT}/{TASK_FILE}"


def run_check(
    repo: Repo, cwd: Path, project_dir: Path | None = None, *args: str
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in repo.env.items() if k != "CLAUDE_PROJECT_DIR"}
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def check_nested(repo: Repo) -> subprocess.CompletedProcess[str]:
    result = run_check(repo, repo.work / PROJECT)
    assert "fatal:" not in result.stderr, result.stderr
    return result


def nested_note(repo: Repo, text: str) -> str:
    path = repo.work / NESTED_TASK_FILE
    return repo.commit(
        "task-5: record review",
        {NESTED_TASK_FILE: path.read_text("utf-8") + text + "\n"},
    )


def nested_reviewed_merge(repo: Repo, bookkeeping: dict[str, str] | None = None) -> str:
    """Merge a reviewed task-5 branch of the nested project; return the reviewed SHA."""
    repo.git("checkout", "-q", "-b", "task-5")
    reviewed = repo.commit("task-5: add feature", {f"{PROJECT}/app.py": "a = 10\n"})
    nested_note(repo, f"Review: APPROVED {reviewed}")
    if bookkeeping:
        repo.commit("task-5: bump version", bookkeeping)
    merge_task_branch(repo)
    return reviewed


@pytest.fixture
def nested(tmp_path: Path) -> Repo:
    r = Repo(tmp_path)
    r.commit(
        "init",
        {
            "dotfile": "x\n",
            # A repo-root conf the nested project must not read: its since
            # value cannot resolve and would end the run with exit 2.
            ".claude/task-reviewer.conf": "master_provenance_since=0000000\n",
            f"{PROJECT}/app.py": "a = 1\n",
            NESTED_TASK_FILE: "# TASK-5\n\n## Notes\n",
        },
    )
    r.git("push", "-q", "origin", "master")
    return r


def test_nested_project_reads_its_own_conf(nested: Repo) -> None:
    old = nested.commit(
        "task-5: unreviewed code from before the convention",
        {f"{PROJECT}/app.py": "a = 0\n"},
    )
    nested.commit(
        "adopt",
        {
            f"{PROJECT}/.claude/task-reviewer.conf": (
                f"master_provenance_since={old}\nmaster_bookkeeping_paths=VERSION\n"
            )
        },
    )
    nested_reviewed_merge(nested, {f"{PROJECT}/VERSION": "2\n"})
    result = check_nested(nested)
    assert_approved(result)
    assert nested.git("rev-parse", "--short", old) not in result.stdout


def test_nested_task_file_commit_and_reviewed_merge(nested: Repo) -> None:
    reviewed = nested_reviewed_merge(nested)
    nested_note(nested, "Status: Done")
    result = check_nested(nested)
    assert_approved(result)
    assert "task-file commit" in result.stdout
    assert (
        f"reviewed at {nested.git('rev-parse', '--short', reviewed)}" in result.stdout
    )


def test_nested_reviewed_fast_forward(nested: Repo) -> None:
    nested.git("checkout", "-q", "-b", "task-5")
    reviewed = nested.commit("task-5: add feature", {f"{PROJECT}/app.py": "a = 10\n"})
    nested_note(nested, f"Review: APPROVED {reviewed}")
    nested.git("checkout", "-q", "master")
    nested.git("merge", "-q", "--ff-only", "task-5")
    result = check_nested(nested)
    assert_approved(result)
    assert "fast-forwarded TASK-5 work" in result.stdout


def test_nested_skips_commits_outside_the_project(nested: Repo) -> None:
    outside = nested.commit(
        "tweak my shell", {"dotfile": "y\n", "other/tool.sh": "z\n"}
    )
    result = check_nested(nested)
    assert_approved(result)
    assert (
        f"ok {nested.git('rev-parse', '--short', outside)} outside the project"
        in result.stdout
    )


def test_nested_flags_unreviewed_commit_under_the_project(nested: Repo) -> None:
    sha = nested.commit("task-5: unreviewed", {f"{PROJECT}/app.py": "a = 2\n"})
    assert_flagged(
        check_nested(nested), nested, sha, "direct commit outside the guard allowlist"
    )


def test_nested_flags_task_file_at_the_repo_root(nested: Repo) -> None:
    sha = nested.commit(
        "task-5: root task file",
        {TASK_FILE: "# TASK-5\n", f"{PROJECT}/app.py": "a = 3\n"},
    )
    assert_flagged(
        check_nested(nested), nested, sha, "direct commit outside the guard allowlist"
    )


def test_nested_project_comes_from_claude_project_dir(nested: Repo) -> None:
    nested.commit("tweak my shell", {"dotfile": "y\n"})
    sha = nested.commit("task-5: unreviewed", {f"{PROJECT}/app.py": "a = 2\n"})
    from_env = run_check(nested, nested.work, nested.work / PROJECT)
    assert from_env.stdout == check_nested(nested).stdout
    assert_flagged(from_env, nested, sha, "direct commit outside the guard allowlist")


def test_root_project_from_a_subdirectory_with_claude_project_dir(repo: Repo) -> None:
    repo.commit("Sketch the design", {"design/feature-brainstorm.md": "idea\n"})
    reviewed = approved_task_branch(repo)
    merge_task_branch(repo)
    repo.commit("task-5: unreviewed", {"app.py": "a = 0\n"})
    root = run_check(repo, repo.work)
    sub = run_check(repo, repo.work / "design", repo.work)
    assert root.returncode == sub.returncode == 1
    assert (root.stdout, root.stderr) == (sub.stdout, sub.stderr)
    assert f"reviewed at {repo.git('rev-parse', '--short', reviewed)}" in sub.stdout


def test_r_infra_6_describes_nested_projects() -> None:
    text = flat(
        (
            REPO_ROOT
            / "plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md"
        ).read_text("utf-8")
    )
    body = text[text.index("## R-INFRA-6: ") : text.index("## R-INFRA-7: ")]
    for needle in ("`CLAUDE_PROJECT_DIR`", "nested project", "outside the project"):
        assert needle in body, needle
