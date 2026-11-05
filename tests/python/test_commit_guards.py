"""PreToolUse commit guards deny only real commits (TASK-281).

``commit-msg-guard.sh`` and ``commit-prefix-guard.sh`` are registered with
``if: Bash(git *)`` / ``if: Bash(gh pr create *)`` (``git *`` because
``git -c k=v commit`` misses a literal ``git commit *``), and that filter is
best-effort too: Claude Code runs the hook anyway for commands it cannot fully
parse (unquoted ``$VAR``, ``$(...)``, backticks). Each guard therefore gates
itself on a real commit at a command position, and the prefix guard extracts
the message without a line-bound ``sed`` so multi-line messages parse.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

HOOKS = REPO_ROOT / "plugins/ralph/hooks"
LIVE = REPO_ROOT / ".claude/hooks"
GUARDS = ["commit-msg-guard.sh", "commit-prefix-guard.sh"]
COMMIT = "git" + " commit"
TRAILER = "Co-Authored-" + "By: someone <x@y>"


def run_guard(name: str, command: str, cwd: Path | None = None) -> str:
    """Run a plugin guard with ``command`` as tool_input and return stdout."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    result = subprocess.run(
        ["bash", str(HOOKS / name)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=True,
    )
    return result.stdout


@pytest.fixture
def task_repo(tmp_path: Path) -> Path:
    """A git repo with one commit, checked out on branch ``task-99-feature``."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    identity = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            *identity,
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "init",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-q", "-b", "task-99-feature"],
        check=True,
    )
    return tmp_path


def is_deny(output: str) -> bool:
    """True when ``output`` is the PreToolUse deny JSON."""
    return (
        bool(output)
        and json.loads(output)["hookSpecificOutput"]["permissionDecision"] == "deny"
    )


# --- commit-msg-guard -------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        f'backlog task create "Ban trailers" -d "Forbid {TRAILER} and Generated with Claude Code"',
        f'backlog task edit 5 --append-notes "Policy: no {TRAILER}; see {COMMIT} hook" $(date)',
        f"python3 - <<'EOF'\nprint('{TRAILER}')\nprint('## Test plan')\nEOF",
        f'echo "{COMMIT} -m x {TRAILER}"',
    ],
)
def test_msg_guard_ignores_non_commit(command: str) -> None:
    assert run_guard("commit-msg-guard.sh", command) == ""


@pytest.mark.parametrize(
    "command",
    [
        f'{COMMIT} -m "fix: stuff\n\n{TRAILER}"',
        f'{COMMIT} -m "fix: stuff\n\n## Test plan\n- step"',
        f"cd /tmp && {COMMIT} -m \"$(cat <<'EOF'\nfix\n\n{TRAILER}\nEOF\n)\"",
        f'gh pr create --title "fix" --body "stuff\n{TRAILER}"',
        'git -C /tmp commit -m "x\nGenerated with Claude Code"',
    ],
)
def test_msg_guard_denies_real_commit(command: str) -> None:
    assert is_deny(run_guard("commit-msg-guard.sh", command))


def test_msg_guard_allows_clean_commit() -> None:
    assert run_guard("commit-msg-guard.sh", f'{COMMIT} -m "task-42: fix"') == ""


# --- commit-prefix-guard ----------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        f'{COMMIT} -m "task-99: subject\n\nbody line one\nbody line two"',
        f"{COMMIT} -m 'task-99: subject\n\nbody'",
        f'{COMMIT} -am "task-99: subject"',
        f'{COMMIT} --message="task-99: subject\n\nbody"',
        f"{COMMIT} -F - <<'EOF'\ntask-99: subject\n\nbody\nEOF",
        f'{COMMIT} -m "$(cat <<\'EOF\'\ntask-99: subject\n\nbody with "quotes"\nEOF\n)"',
        f"{COMMIT} <<EOF\n  task-99: subject\nEOF",
        f'{COMMIT} -m "Merge branch master into task-99"',
    ],
)
def test_prefix_guard_allows_prefixed(task_repo: Path, command: str) -> None:
    assert run_guard("commit-prefix-guard.sh", command, task_repo) == ""


@pytest.mark.parametrize("prefix", ["", "task-12: "])
@pytest.mark.parametrize(
    "template",
    [
        '{c} -m "{p}subject"',
        '{c} -m "{p}subject\n\nbody\nmore"',
        "{c} -m '{p}subject\n\nbody'",
        '{c} --message="{p}subject\n\nbody"',
        "{c} -F - <<'EOF'\n{p}subject\nbody\nEOF",
        "{c} --message={p}subject",
    ],
)
def test_prefix_guard_denies_bad_prefix(
    task_repo: Path, template: str, prefix: str
) -> None:
    output = run_guard(
        "commit-prefix-guard.sh", template.format(c=COMMIT, p=prefix), task_repo
    )
    assert is_deny(output)
    assert "task-99" in output


@pytest.mark.parametrize(
    ("content", "denied"), [("task-99: subject\n\nbody\n", False), ("subject\n", True)]
)
@pytest.mark.parametrize("flag", ["-F {f}", "--file={f}", "--file {f}"])
def test_prefix_guard_reads_message_file(
    task_repo: Path, content: str, denied: bool, flag: str
) -> None:
    (task_repo / "msg.txt").write_text(content)
    command = f"{COMMIT} " + flag.format(f="msg.txt")
    assert is_deny(run_guard("commit-prefix-guard.sh", command, task_repo)) is denied


@pytest.mark.parametrize(
    "command",
    [
        f"backlog task edit 5 --append-notes \"Use {COMMIT} -m 'task-N: subject'\"",
        f'backlog task edit 5 --append-notes "ran: cd x && {COMMIT} -m foo" $(date)',
        f"python3 - <<'EOF'\nimport os\nos.system('{COMMIT} -m foo')\nEOF",
        "kill 1",
    ],
)
def test_prefix_guard_ignores_mentions(task_repo: Path, command: str) -> None:
    assert run_guard("commit-prefix-guard.sh", command, task_repo) == ""


@pytest.mark.parametrize(
    "command",
    [
        f"{COMMIT}",
        f"{COMMIT} --amend --no-edit",
        f'{COMMIT} -m "$MSG"',
        f"{COMMIT} -F missing.txt",
    ],
)
def test_prefix_guard_allows_unextractable(task_repo: Path, command: str) -> None:
    assert run_guard("commit-prefix-guard.sh", command, task_repo) == ""


def test_prefix_guard_ignores_master(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "master", str(tmp_path)], check=True)
    assert run_guard("commit-prefix-guard.sh", f'{COMMIT} -m "random"', tmp_path) == ""


@pytest.mark.parametrize("name", GUARDS)
def test_live_copy_matches_the_plugin(name: str) -> None:
    assert (LIVE / name).read_bytes() == (HOOKS / name).read_bytes()


# --- lexer edge cases (task-reviewer round 1) -------------------------------

BAD = f'{COMMIT} -m "bad\n\n{TRAILER}"'


@pytest.mark.parametrize(
    "prefix",
    [
        "if true; then ",
        "if false; then :; else ",
        "{ ",
        "! ",
        "time ",
        "FOO=1 ",
        "cat <<<abc; ",
        "echo $((1<<3)); ",
        "cat <<'END-MSG'\nhi\nEND-MSG\n",
        "\\",
        "cd /tmp &&\n",
    ],
)
def test_guards_see_commit_after_shell_syntax(task_repo: Path, prefix: str) -> None:
    command = prefix + BAD
    assert is_deny(run_guard("commit-msg-guard.sh", command, task_repo))
    assert is_deny(run_guard("commit-prefix-guard.sh", command, task_repo))


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        (f"{COMMIT} --author=\"A -mB <a@b>\" -m 'task-99: ok'", False),
        (f'{COMMIT} -C HEAD -m "task-99: ok"', False),
        (f'{COMMIT} -m "task-99: ok" 2>&1 && git log -m "x"', False),
        (f'{COMMIT} --no-edit && foo -m "x"', False),
        (f'{COMMIT} -m "task-99: a) b\n\nbody"', False),
        (f"{COMMIT} -m \"$(cat <<'EOF'\nwip (draft\nEOF\n)\"", True),
        (f"{COMMIT} -mwip", True),
        (f'{COMMIT} -m "" ', False),
    ],
)
def test_prefix_guard_option_parsing(
    task_repo: Path, command: str, denied: bool
) -> None:
    assert is_deny(run_guard("commit-prefix-guard.sh", command, task_repo)) is denied


# The two guards' shared lexer block is pinned identical by the bats case
# "commit-msg-guard and commit-prefix-guard share an identical lexer".


# --- git global options and the widened Bash(git *) filter (TASK-325) -------

GLOBAL_OPTS = [
    "git -c user.name=x -c user.email=y commit",
    "git -C . commit",
    "git --git-dir=.git commit",
    "git --work-tree=. commit",
]


@pytest.mark.parametrize("git_commit", GLOBAL_OPTS)
def test_guards_see_commit_after_git_global_options(
    task_repo: Path, git_commit: str
) -> None:
    assert is_deny(
        run_guard("commit-prefix-guard.sh", f'{git_commit} -m "no prefix"', task_repo)
    )
    assert (
        run_guard("commit-prefix-guard.sh", f'{git_commit} -m "task-99: ok"', task_repo)
        == ""
    )
    bad = f'{git_commit} -m "task-99: ok\n\n{TRAILER}"'
    assert is_deny(run_guard("commit-msg-guard.sh", bad, task_repo))


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        (f"{COMMIT} -m $'no prefix\\n\\nbody'", True),
        (f"{COMMIT} -m $'task-99: ok\\n\\nbody'", False),
        (f'{COMMIT} -m "task-99: one" && {COMMIT} --allow-empty -m "two"', True),
        (
            f'{COMMIT} -m "task-99: one"; {COMMIT} --allow-empty -m "task-99: two"',
            False,
        ),
    ],
)
def test_prefix_guard_ansi_c_and_chained(
    task_repo: Path, command: str, denied: bool
) -> None:
    assert is_deny(run_guard("commit-prefix-guard.sh", command, task_repo)) is denied


@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "git log --oneline --grep commit",
        'git -c core.pager=cat log -m --format="%s commit"',
        "git checkout -b task-99-commit",
    ],
)
def test_guards_allow_non_commit_git(task_repo: Path, command: str) -> None:
    for name in GUARDS:
        assert run_guard(name, command, task_repo) == ""
