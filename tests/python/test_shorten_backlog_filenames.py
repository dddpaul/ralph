"""Tests for ``scripts/shorten-backlog-filenames.py`` (TASK-231, TASK-236).

The script is a hyphenated PEP 723 file, so it is loaded by path rather than
imported. Unit tests cover the pure layer; the integration tests drive the CLI
end to end over throwaway git repositories with a stubbed ``claude`` on PATH --
one repository for the single-project case, a tree of them for the multi-project
sweep, which renames and then commits each project on its own.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "shorten-backlog-filenames.py"
GUARD = REPO_ROOT / ".claude" / "hooks" / "filename-length-guard.sh"


def _load_script():
    spec = importlib.util.spec_from_file_location("shorten_backlog_filenames", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sbf = _load_script()

LIMIT = sbf.DEFAULT_LIMIT

# A slug long enough that `task-<id> - <slug>.md` blows the 125-byte cap.
LONG_SLUG = (
    "Verify-and-reconcile-the-ralph-stop-graceful-drain-guarantee"
    "-against-the-step-5-signal-path-in-devcontainer-mode-really-long-tail"
)
STUB_SLUG = "ralph-stop-drain-guarantee"

# What the stub `claude` prints: deliberately padded and mixed-case so the
# integration run exercises the normalizer, not just the plumbing.
STUB_OUTPUT = "  Ralph Stop Drain Guarantee  "


# --------------------------------------------------------------------------
# basename_bytes — byte, not character, measurement
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("task-1 - a.md", 13),
        ("", 0),
        ("привет.md", 15),  # 6 Cyrillic chars x 2 bytes + ".md"
        ("emoji-🚀.md", 13),  # 6 + 4 + 3
    ],
)
def test_basename_bytes_counts_bytes(name: str, expected: int) -> None:
    assert sbf.basename_bytes(name) == expected


@pytest.mark.parametrize("name", ["ascii.md", "привет-мир.md", "emoji-🚀.md"])
def test_basename_bytes_matches_bash_lc_all_c(name: str) -> None:
    """The Python count must equal bash's ``${#name}`` under ``LC_ALL=C``."""
    proc = subprocess.run(
        ["bash", "-c", 'printf %s "${#1}"', "_", name],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    assert int(proc.stdout) == sbf.basename_bytes(name)


# --------------------------------------------------------------------------
# parse_prefix
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "prefix", "slug"),
    [
        ("task-231 - Add-a-script.md", "task-231 - ", "Add-a-script"),
        ("doc-1 - Ralph-Loop-Research.md", "doc-1 - ", "Ralph-Loop-Research"),
        ("decision-12 - Pick-uv.md", "decision-12 - ", "Pick-uv"),
        ("task-90.1 - Sub-task.md", "task-90.1 - ", "Sub-task"),
        ("task-7 - Name - with - dashes.md", "task-7 - ", "Name - with - dashes"),
    ],
)
def test_parse_prefix_accepts_backlog_names(name: str, prefix: str, slug: str) -> None:
    parsed = sbf.parse_prefix(name)
    assert parsed == sbf.ParsedName(prefix=prefix, slug=slug)


@pytest.mark.parametrize(
    "name",
    [
        "README.md",
        "task-231-No-space-dash.md",
        "task- - Missing-id.md",
        "Task-231 - Capitalised-kind.md",
        "task-231 - Not-markdown.txt",
        "task-231 - .md",
    ],
)
def test_parse_prefix_rejects_other_names(name: str) -> None:
    assert sbf.parse_prefix(name) is None


# --------------------------------------------------------------------------
# slug_budget — per-file, because prefixes differ in width
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("prefix", "limit", "expected"),
    [
        ("task-1 - ", 125, 113),
        ("task-231 - ", 125, 111),
        ("decision-9999 - ", 125, 106),
        ("task-90.1 - ", 125, 110),
        ("task-231 - ", 60, 46),
    ],
)
def test_slug_budget(prefix: str, limit: int, expected: int) -> None:
    assert sbf.slug_budget(prefix, limit) == expected


def test_slug_budget_leaves_room_for_a_full_basename() -> None:
    prefix = "decision-9999 - "
    budget = sbf.slug_budget(prefix, LIMIT)
    name = f"{prefix}{'a' * budget}.md"
    assert sbf.basename_bytes(name) == LIMIT


# --------------------------------------------------------------------------
# normalize_slug — claude output is untrusted
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("shorten-backlog-filenames", "shorten-backlog-filenames"),
        ("  Shorten Backlog Filenames  ", "shorten-backlog-filenames"),
        ("Shorten_Backlog/Filenames", "shorten-backlog-filenames"),
        ('"shorten-backlog-filenames"', "shorten-backlog-filenames"),
        ("`shorten-backlog-filenames`", "shorten-backlog-filenames"),
        ("shorten--backlog---filenames", "shorten-backlog-filenames"),
        ("---shorten-backlog-filenames---", "shorten-backlog-filenames"),
        ("Shorten: Backlog (Filenames)!", "shorten-backlog-filenames"),
        ("shorten-backlog-filenames.md", "shorten-backlog-filenamesmd"),
        (
            "\n\n  shorten-backlog-filenames\nand some prose\n",
            "shorten-backlog-filenames",
        ),
        ("```\nshorten-backlog-filenames\n```", "shorten-backlog-filenames"),
        ("Сократить-имена-файлов", ""),
        ("!!!", ""),
        ("", ""),
        ("   \n\t  ", ""),
    ],
)
def test_normalize_slug_table(raw: str, expected: str) -> None:
    assert sbf.normalize_slug(raw, 111) == expected


def test_normalize_slug_trims_at_a_hyphen_boundary() -> None:
    assert sbf.normalize_slug("alpha-beta-gamma", 12) == "alpha-beta"


def test_normalize_slug_hard_cuts_when_there_is_no_hyphen() -> None:
    assert sbf.normalize_slug("supercalifragilistic", 5) == "super"


def test_normalize_slug_never_exceeds_the_budget() -> None:
    # Kebab-case, i.e. what the prompt asks for: a spaced six-word phrase
    # would be rejected as prose and make every assertion below vacuous.
    for budget in range(1, 40):
        slug = sbf.normalize_slug("some-rather-long-proposed-slug-here", budget)
        assert slug, f"budget {budget} produced no slug at all"
        assert sbf.basename_bytes(slug) <= budget


def test_normalize_slug_does_not_split_a_multibyte_character() -> None:
    # A raw byte cut at 5 would land inside the third character.
    assert sbf.trim_to_budget("ααα", 5) == "αα"


# --------------------------------------------------------------------------
# pick_slug_line — prose is not a slug proposal (TASK-232 finding 1)
# --------------------------------------------------------------------------


PREAMBLE = "Here is the slug you asked for:"


@pytest.mark.parametrize(
    "raw",
    [
        PREAMBLE,
        "Sure! Here is a short kebab-case slug for that artifact.",
        "I cannot propose a slug because the content is empty.",
    ],
)
def test_normalize_slug_rejects_a_prose_line(raw: str) -> None:
    """Prose clears MIN_SLUG_BYTES, so only a "" here forces the retry."""
    assert sbf.normalize_slug(raw, 111) == ""


@pytest.mark.parametrize(
    "raw",
    [
        "ralph-stop-drain",
        "  ralph-stop-drain  ",
        "Ralph Stop Drain",
        "Ralph Stop Drain Guarantee",  # exactly MAX_SLUG_WORDS
    ],
)
def test_normalize_slug_still_accepts_a_short_proposal(raw: str) -> None:
    assert sbf.normalize_slug(raw, 111).startswith("ralph-stop-drain")


def test_normalize_slug_prefers_a_clean_line_under_a_preamble() -> None:
    """The slug on its own line wins over the prose that introduces it."""
    assert sbf.normalize_slug(f"{PREAMBLE}\nralph-stop-drain\n", 111) == (
        "ralph-stop-drain"
    )


def test_normalize_slug_prefers_a_clean_line_over_a_leading_bullet() -> None:
    raw = "Options:\n- first idea\nralph-stop-drain\nHope that helps!\n"
    assert sbf.normalize_slug(raw, 111) == "ralph-stop-drain"


def test_pick_slug_line_skips_a_clean_line_below_the_minimum() -> None:
    """A two-byte token is not a slug; the next candidate is considered."""
    assert sbf.pick_slug_line("ok\nralph-stop-drain\n") == "ralph-stop-drain"


def test_pick_slug_line_returns_empty_for_no_candidate() -> None:
    assert sbf.pick_slug_line("```\n```\n") == ""


# --------------------------------------------------------------------------
# pick_slug_line — a short refusal is not a proposal either (TASK-234)
# --------------------------------------------------------------------------


# Refusals that fit inside the word cap, i.e. exactly the ones MAX_SLUG_WORDS
# cannot catch. `I cannot help` is the shape TASK-232 left open.
SHORT_REFUSALS = [
    "I cannot help",
    "I'm unable to",
    "I\u2019m unable to",  # the curly apostrophe a model actually emits
    "Sorry, cannot comply",
    "Unfortunately no",
    "Cannot propose a slug",
]

# Long enough that the word cap rejects it on its own; kept as an AC shape.
LONG_REFUSAL = "Sorry, I am unable to do that"


@pytest.mark.parametrize("raw", SHORT_REFUSALS)
def test_short_refusals_sit_within_the_word_cap(raw: str) -> None:
    """Pins that the opener signal, not MAX_SLUG_WORDS, is what rejects them.

    Without this the refusal cases below would pass for the old reason and
    silently stop testing the new one.
    """
    assert len(raw.split()) <= sbf.MAX_SLUG_WORDS


@pytest.mark.parametrize("raw", [*SHORT_REFUSALS, LONG_REFUSAL])
def test_pick_slug_line_rejects_a_refusal(raw: str) -> None:
    assert sbf.pick_slug_line(raw) == ""


@pytest.mark.parametrize("raw", [*SHORT_REFUSALS, LONG_REFUSAL])
def test_normalize_slug_rejects_a_refusal(raw: str) -> None:
    """`I cannot help` clears MIN_SLUG_BYTES as `i-cannot-help` otherwise."""
    assert sbf.normalize_slug(raw, 111) == ""


@pytest.mark.parametrize(
    "raw",
    [
        "Shorten Backlog Filenames",  # three words, like `I cannot help`
        "i18n Support Matrix",  # `i18n` must not fold onto the `i` opener
        "Ideal Retry Budget",  # a stop word is a token, not a prefix
    ],
)
def test_pick_slug_line_still_accepts_a_short_proposal(raw: str) -> None:
    assert sbf.pick_slug_line(raw) == raw


@pytest.mark.parametrize(
    "raw",
    [
        "cannot-reproduce-the-hang",
        "unable-to-parse-frontmatter",
        "sorry",
        "i18n",
    ],
)
def test_pick_slug_line_never_rejects_a_conforming_line(raw: str) -> None:
    """A line that already obeys the prompt never reaches the stop-list."""
    assert sbf.CLEAN_SLUG_RE.match(raw)
    assert sbf.pick_slug_line(raw) == raw


def test_pick_slug_line_prefers_a_clean_line_under_a_refusal() -> None:
    assert sbf.pick_slug_line("I cannot help\nralph-stop-drain\n") == (
        "ralph-stop-drain"
    )


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("I cannot help", "i"),
        ("I'm sorry", "im"),
        ("I\u2019ve stopped", "ive"),  # curly apostrophe, folded like a straight one
        ("Sorry, no.", "sorry"),
        ("**Cannot** do it", "cannot"),
        ("i18n Support Matrix", "i18n"),
        ("Ideal Retry Budget", "ideal"),
        ("", ""),
        ("   ", ""),
        ("Сократить имена", ""),  # nothing in [a-z0-9] survives
    ],
)
def test_opening_token_folds_a_word_for_comparison(line: str, expected: str) -> None:
    assert sbf.opening_token(line) == expected


# --------------------------------------------------------------------------
# dedupe_target — collision suffixing with a re-trim
# --------------------------------------------------------------------------


def test_dedupe_target_returns_the_plain_name_when_free() -> None:
    assert sbf.dedupe_target("task-1 - ", "alpha", 113, set()) == "task-1 - alpha.md"


def test_dedupe_target_suffixes_until_free() -> None:
    taken = {"task-1 - alpha.md", "task-1 - alpha-2.md"}
    assert sbf.dedupe_target("task-1 - ", "alpha", 113, taken) == "task-1 - alpha-3.md"


def test_dedupe_target_retrims_so_the_basename_stays_within_the_limit() -> None:
    prefix = "task-231 - "
    budget = sbf.slug_budget(prefix, LIMIT)
    slug = "a" * budget  # a slug that exactly fills the budget
    plain = f"{prefix}{slug}.md"
    assert sbf.basename_bytes(plain) == LIMIT
    suffixed = sbf.dedupe_target(prefix, slug, budget, {plain})
    # The `-2` is paid for out of the slug, not added on top of the limit.
    assert suffixed == f"{prefix}{'a' * (budget - 2)}-2.md"
    assert sbf.basename_bytes(suffixed) == LIMIT


def test_dedupe_target_retrim_keeps_hyphen_boundaries() -> None:
    prefix = "task-231 - "
    budget = sbf.slug_budget(prefix, LIMIT)
    slug = sbf.normalize_slug("alpha beta " * 20, budget)
    plain = f"{prefix}{slug}.md"
    suffixed = sbf.dedupe_target(prefix, slug, budget, {plain})
    assert suffixed.endswith("-2.md")
    assert "--" not in suffixed
    assert sbf.basename_bytes(suffixed) <= LIMIT


def test_dedupe_target_raises_when_every_suffix_is_taken() -> None:
    taken = {"task-1 - a.md"} | {f"task-1 - a-{n}.md" for n in range(2, 100)}
    with pytest.raises(RuntimeError):
        sbf.dedupe_target("task-1 - ", "a", 113, taken)


# --------------------------------------------------------------------------
# content_slice
# --------------------------------------------------------------------------


def test_content_slice_extracts_the_title_and_bounds_the_body() -> None:
    text = "---\nid: task-1\ntitle: A Long Title\nstatus: To Do\n---\n\n" + "x" * 9000
    title, body = sbf.content_slice(text)
    assert title == "A Long Title"
    assert len(body) == sbf.CONTENT_CAP


def test_content_slice_tolerates_a_missing_frontmatter() -> None:
    assert sbf.content_slice("just a body") == ("", "just a body")


# --------------------------------------------------------------------------
# Integration — throwaway git repo, stubbed claude on PATH
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "LC_ALL": "C"},
    )


def _write_stub(bin_dir: Path, body: str) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "claude"
    stub.write_text(f"#!/bin/bash\n{body}\n")
    stub.chmod(0o755)


# The shape `backlog init` leaves behind. config.yml is half of the two-signal
# backlog-root test, so a fixture without one is not a project at all.
CONFIG_YML = """\
project_name: "{name}"
default_status: "To Do"
statuses: ["To Do", "In Progress", "Done"]
"""


def _write_backlog(backlog: Path, names: list[str], project_name: str) -> Path:
    """Create one backlog root: a config.yml and ``names`` under tasks/."""
    tasks = backlog / "tasks"
    tasks.mkdir(parents=True)
    (backlog / "config.yml").write_text(CONFIG_YML.format(name=project_name))
    for index, name in enumerate(names):
        (tasks / name).write_text(
            f"---\nid: task-{index}\ntitle: {name}\n---\n\nBody of {name}.\n"
        )
    return backlog


def _init_repo(repo: Path) -> Path:
    """Turn ``repo`` into a git repository with everything in it committed."""
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixtures")
    return repo


def _make_repo(
    base: Path,
    names: list[str],
    *,
    at: str = "repo",
    project_name: str = "fixture",
) -> Path:
    """A committed git repository holding one backlog root."""
    repo = base / at
    _write_backlog(repo / "backlog", names, project_name)
    return _init_repo(repo)


def _install_hook(repo: Path, body: str) -> None:
    """Install ``body`` as ``repo``'s pre-commit hook."""
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f"#!/bin/bash\n{body}\n")
    hook.chmod(0o755)


def _subjects(repo: Path) -> list[str]:
    """Commit subjects, newest first."""
    return _git(repo, "log", "--format=%s").stdout.splitlines()


def _head_changes(repo: Path) -> list[str]:
    """``<status>\t<path>`` for every path in HEAD, renames left as add+delete.

    ``--no-renames`` on purpose: the point of the assertion is *which* paths
    the commit carries, and a rename pair collapsed into one R row hides the
    old path the commit is supposed to contain.
    """
    out = _git(repo, "show", "--name-status", "--no-renames", "--format=", "HEAD")
    return sorted(line for line in out.stdout.splitlines() if line)


def _shortened(count: int) -> str:
    """The fixed housekeeping commit message the sweep writes."""
    return f"chore(backlog): shorten {count} over-limit filename(s) for ecryptfs sync"


def _run_script(
    repo: Path, bin_dir: Path, *args: str, path: str = "backlog", **env_extra: str
):
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--path", path, *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


LONG_101 = f"task-101 - {LONG_SLUG}.md"
LONG_102 = f"task-102 - {LONG_SLUG}.md"
SHORT_103 = "task-103 - Already-short.md"
UNPARSEABLE = f"Notes-{LONG_SLUG}.md"
# Occupies task-101's proposed target, forcing the collision branch.
DECOY_101 = f"task-101 - {STUB_SLUG}.md"
FIXTURES = [LONG_101, LONG_102, SHORT_103, UNPARSEABLE, DECOY_101]


def test_fixture_names_straddle_the_limit() -> None:
    assert sbf.basename_bytes(LONG_101) > LIMIT
    assert sbf.basename_bytes(LONG_102) > LIMIT
    assert sbf.basename_bytes(UNPARSEABLE) > LIMIT
    assert sbf.basename_bytes(SHORT_103) <= LIMIT
    assert sbf.basename_bytes(DECOY_101) <= LIMIT


def test_plan_renames_never_maps_two_sources_to_one_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two files whose proposed slugs coincide must not collide in one run."""
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    # Same prefix, so an identical slug would yield an identical basename.
    first = tasks / f"task-101 - {LONG_SLUG}-one.md"
    second = tasks / f"task-101 - {LONG_SLUG}-two.md"
    for path in (first, second):
        path.write_text("---\nid: task-101\n---\n\nBody.\n")
    monkeypatch.setattr(sbf, "ask_claude", lambda *_args, **_kw: STUB_OUTPUT)

    plans, counters = sbf.plan_renames([first, second], sbf.Options())

    assert counters.over_limit == 2
    assert counters.fallbacks == 0
    assert counters.collisions == 1
    names = [plan.new_name for plan in plans]
    assert names == [
        f"task-101 - {STUB_SLUG}.md",
        f"task-101 - {STUB_SLUG}-2.md",
    ]
    assert len(set(names)) == len(names)


def test_plan_renames_leaves_already_short_files_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    short = tasks / SHORT_103
    short.write_text("---\nid: task-103\n---\n\nBody.\n")

    def _fail(*_args: object, **_kw: object) -> str:
        raise AssertionError("claude must not be consulted for a short name")

    monkeypatch.setattr(sbf, "ask_claude", _fail)

    plans, counters = sbf.plan_renames([short], sbf.Options())

    assert plans == []
    assert counters == sbf.Counters(scanned=1)


@pytest.fixture
def stubbed_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = _make_repo(tmp_path, FIXTURES)
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')
    return repo, bin_dir


def test_dry_run_reports_renames_and_changes_nothing(
    stubbed_repo: tuple[Path, Path],
) -> None:
    repo, bin_dir = stubbed_repo
    tasks = repo / "backlog" / "tasks"
    before = sorted(p.name for p in tasks.iterdir())

    proc = _run_script(repo, bin_dir)

    assert proc.returncode == 0, proc.stderr
    assert f"task-102 - {STUB_SLUG}.md  (" in proc.stdout
    assert "[OK]" in proc.stdout
    assert f"task-101 - {STUB_SLUG}-2.md  (" in proc.stdout
    assert "[COLLISION]" in proc.stdout
    assert LONG_101 in proc.stdout and LONG_102 in proc.stdout
    assert SHORT_103 not in proc.stdout
    assert "WARNING: skipping" in proc.stderr and UNPARSEABLE in proc.stderr
    assert (
        "Summary: scanned=5 over-limit=3 renamed=0 fallbacks=0 "
        "collisions=1 skipped=1 errors=0 projects=1 committed=0 project-errors=0"
        in proc.stdout
    )
    assert "Dry run: nothing changed." in proc.stdout
    # A single backlog root is the one-project case of the same sweep.
    assert f"== fixture [{repo.resolve()}] ==" in proc.stdout
    assert f"Would commit 2 rename(s) in fixture [{repo.resolve()}]" in proc.stdout

    assert sorted(p.name for p in tasks.iterdir()) == before
    assert _git(repo, "status", "--porcelain").stdout == ""


def test_apply_renames_via_git_mv(stubbed_repo: tuple[Path, Path]) -> None:
    repo, bin_dir = stubbed_repo
    tasks = repo / "backlog" / "tasks"

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    assert "renamed=2" in proc.stdout
    assert "Dry run" not in proc.stdout

    names = sorted(p.name for p in tasks.iterdir())
    assert names == sorted(
        [
            f"task-101 - {STUB_SLUG}-2.md",
            f"task-102 - {STUB_SLUG}.md",
            SHORT_103,
            UNPARSEABLE,
            DECOY_101,
        ]
    )
    # git mv stages the rename, the project commit lands it, and the body
    # rides along untouched.
    assert _git(repo, "status", "--porcelain").stdout == ""
    assert _subjects(repo) == [_shortened(2), "fixtures"]
    assert _head_changes(repo) == sorted(
        [
            f"A\tbacklog/tasks/task-101 - {STUB_SLUG}-2.md",
            f"A\tbacklog/tasks/task-102 - {STUB_SLUG}.md",
            f"D\tbacklog/tasks/{LONG_101}",
            f"D\tbacklog/tasks/{LONG_102}",
        ]
    )
    moved = (tasks / f"task-102 - {STUB_SLUG}.md").read_text()
    assert f"Body of {LONG_102}." in moved


def test_apply_output_passes_the_filename_length_guard(
    stubbed_repo: tuple[Path, Path],
) -> None:
    """The renames must survive the real guard, run as a real hook."""
    repo, bin_dir = stubbed_repo
    if not GUARD.is_file():  # pragma: no cover - guard ships with the repo
        pytest.skip("filename-length-guard.sh not present")
    # The project commit respects hooks, so installing the shipped guard as
    # one puts it on the path this run has to clear. The marker keeps the
    # assertion honest: a guard that never ran would prove nothing.
    ran = repo / "hook-ran"
    _install_hook(repo, f'printf "ran\\n" >> "{ran}"\nexec bash "{GUARD}"')

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    assert ran.is_file()
    assert "committed=1" in proc.stdout
    for path in (repo / "backlog" / "tasks").iterdir():
        if path.name != UNPARSEABLE:  # skipped by design, still over-limit
            assert sbf.basename_bytes(path.name) <= LIMIT


def test_second_run_proposes_no_further_renames(
    stubbed_repo: tuple[Path, Path],
) -> None:
    repo, bin_dir = stubbed_repo
    assert _run_script(repo, bin_dir, "--apply").returncode == 0

    again = _run_script(repo, bin_dir)

    assert again.returncode == 0, again.stderr
    assert "  -> " not in again.stdout
    assert "over-limit=1 renamed=0" in again.stdout
    assert "skipped=1" in again.stdout


def test_claude_failure_retries_once_then_falls_back(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, [LONG_101])
    bin_dir = tmp_path / "bin"
    log = tmp_path / "calls.log"
    _write_stub(bin_dir, 'printf "call\\n" >> "$STUB_LOG"\nexit 1')

    proc = _run_script(repo, bin_dir, "--apply", STUB_LOG=str(log))

    assert proc.returncode == 0, proc.stderr
    assert "[FALLBACK]" in proc.stdout
    assert "fallbacks=1" in proc.stdout and "renamed=1" in proc.stdout
    # One call plus exactly one retry.
    assert log.read_text().count("call") == 2

    renamed = [p.name for p in (repo / "backlog" / "tasks").iterdir()]
    assert renamed != [LONG_101]
    assert sbf.basename_bytes(renamed[0]) <= LIMIT
    # The fallback truncates the existing slug rather than inventing one.
    assert renamed[0].startswith("task-101 - Verify-and-reconcile-the-ralph-stop")


def test_empty_claude_output_falls_back(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, [LONG_101])
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, 'printf "\\n"')

    proc = _run_script(repo, bin_dir)

    assert proc.returncode == 0, proc.stderr
    assert "[FALLBACK]" in proc.stdout
    assert "over-limit=1" in proc.stdout and "fallbacks=1" in proc.stdout


def test_archive_is_excluded_unless_requested(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, [SHORT_103])
    archive = repo / "backlog" / "archive" / "tasks"
    archive.mkdir(parents=True)
    (archive / LONG_101).write_text("---\nid: task-101\n---\n\nArchived.\n")
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    default_run = _run_script(repo, bin_dir)
    assert "over-limit=0" in default_run.stdout

    with_archive = _run_script(repo, bin_dir, "--include-archive")
    assert "over-limit=1" in with_archive.stdout
    assert f"task-101 - {STUB_SLUG}.md" in with_archive.stdout


def test_a_prose_preamble_falls_back_instead_of_becoming_the_filename(
    tmp_path: Path,
) -> None:
    """A stub that only ever answers in prose must not name the file."""
    repo = _make_repo(tmp_path, [LONG_101])
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, 'printf "Here is the slug you asked for:\\n"')

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    assert "[FALLBACK]" in proc.stdout
    assert "fallbacks=1" in proc.stdout and "renamed=1" in proc.stdout
    budget = sbf.slug_budget("task-101 - ", LIMIT)
    truncated = sbf.trim_to_budget(LONG_SLUG, budget)
    renamed = [p.name for p in (repo / "backlog" / "tasks").iterdir()]
    assert renamed == [f"task-101 - {truncated}.md"]
    assert "here-is-the-slug" not in renamed[0]


def test_a_refusing_stub_falls_back_instead_of_naming_the_file(
    tmp_path: Path,
) -> None:
    """A stub that only ever refuses must truncate, not name the file."""
    repo = _make_repo(tmp_path, [LONG_101])
    bin_dir = tmp_path / "bin"
    log = tmp_path / "calls.log"
    _write_stub(bin_dir, 'printf "call\\n" >> "$STUB_LOG"\nprintf "I cannot help\\n"')

    proc = _run_script(repo, bin_dir, "--apply", STUB_LOG=str(log))

    assert proc.returncode == 0, proc.stderr
    assert "[FALLBACK]" in proc.stdout
    assert "fallbacks=1" in proc.stdout and "renamed=1" in proc.stdout
    # The refusal is unusable output, so it costs the retry like any other.
    assert log.read_text().count("call") == 2
    budget = sbf.slug_budget("task-101 - ", LIMIT)
    truncated = sbf.trim_to_budget(LONG_SLUG, budget)
    renamed = [p.name for p in (repo / "backlog" / "tasks").iterdir()]
    assert renamed == [f"task-101 - {truncated}.md"]
    assert "cannot" not in renamed[0]


def test_a_preamble_above_a_clean_slug_still_yields_that_slug(
    tmp_path: Path,
) -> None:
    """The retry is for unusable output, not for a chatty wrapper."""
    repo = _make_repo(tmp_path, [LONG_101])
    bin_dir = tmp_path / "bin"
    _write_stub(
        bin_dir,
        f'printf "Here is the slug you asked for:\\n{STUB_SLUG}\\nHope that helps!\\n"',
    )

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    assert "[FALLBACK]" not in proc.stdout
    assert "fallbacks=0" in proc.stdout and "renamed=1" in proc.stdout
    names = [p.name for p in (repo / "backlog" / "tasks").iterdir()]
    assert names == [f"task-101 - {STUB_SLUG}.md"]


def test_apply_renames_an_untracked_file(tmp_path: Path) -> None:
    """The pre-commit guard rejects a long new name, so it stays untracked."""
    repo = _make_repo(tmp_path, [SHORT_103])
    untracked = repo / "backlog" / "tasks" / LONG_102
    untracked.write_text("---\nid: task-102\n---\n\nNever committed.\n")
    assert _git(repo, "status", "--porcelain").stdout.strip().startswith("??")
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    assert "renamed=1" in proc.stdout and "errors=0" in proc.stdout
    assert "NOTICE:" in proc.stderr and LONG_102 in proc.stderr
    assert "git add" in proc.stderr
    names = sorted(p.name for p in (repo / "backlog" / "tasks").iterdir())
    assert names == sorted([SHORT_103, f"task-102 - {STUB_SLUG}.md"])
    # Renamed, not staged: an untracked file has nothing in the index to move.
    porcelain = _git(repo, "status", "--porcelain").stdout
    assert porcelain.lstrip().startswith("??")
    assert STUB_SLUG in porcelain and "R  " not in porcelain
    # Nothing tracked changed, so the project has nothing to commit.
    assert "committed=0" in proc.stdout
    assert _subjects(repo) == ["fixtures"]


def test_untracked_rename_refuses_to_clobber_an_existing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale plan must cost an error, not a file."""
    repo = _make_repo(tmp_path, [SHORT_103])
    tasks = repo / "backlog" / "tasks"
    (tasks / LONG_102).write_text("---\nid: task-102\n---\n\nSource.\n")
    monkeypatch.setattr(sbf, "ask_claude", lambda *_args, **_kw: STUB_OUTPUT)
    target = tasks / f"task-102 - {STUB_SLUG}.md"

    plans, counters = sbf.plan_renames([tasks / LONG_102], sbf.Options())
    assert [plan.new_name for plan in plans] == [target.name]
    target.write_text("Squatter.\n")  # appears only after the plan is built

    staged = sbf.apply_renames(plans, repo, counters)

    assert staged == []
    assert counters.errors == 1 and counters.renamed == 0
    assert target.read_text() == "Squatter.\n"
    assert (tasks / LONG_102).is_file()


# `git` pretends the repository belongs to someone else, which is the state
# that makes safe.directory load-bearing. Supported since git 2.36.
DUBIOUS = {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}


def _dubious_ownership_is_simulable(repo: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        env={**os.environ, **DUBIOUS, "LC_ALL": "C"},
    )
    return proc.returncode != 0 and "dubious ownership" in proc.stderr


def test_git_repo_root_resolves_under_dubious_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """safe.directory must name the top-level, which discovery starts below."""
    repo = _make_repo(tmp_path, [SHORT_103])
    if not _dubious_ownership_is_simulable(repo):  # pragma: no cover
        pytest.skip("this git does not honour GIT_TEST_ASSUME_DIFFERENT_OWNER")
    for key, value in DUBIOUS.items():
        monkeypatch.setenv(key, value)

    # The script is pointed at backlog/, a subdirectory: trusting only that
    # is a no-op, so the ancestor chain is what makes this resolve.
    root, reason = sbf.git_repo_root(repo / "backlog")

    assert reason == ""
    assert root is not None and root.resolve() == repo.resolve()


def test_apply_renames_under_dubious_ownership(tmp_path: Path) -> None:
    """The whole --apply path, not just discovery, survives the state."""
    repo = _make_repo(tmp_path, [LONG_101])
    if not _dubious_ownership_is_simulable(repo):  # pragma: no cover
        pytest.skip("this git does not honour GIT_TEST_ASSUME_DIFFERENT_OWNER")
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    proc = _run_script(repo, bin_dir, "--apply", **DUBIOUS)

    assert proc.returncode == 0, proc.stderr
    assert "renamed=1" in proc.stdout and "errors=0" in proc.stdout
    assert "dubious ownership" not in proc.stderr
    names = [p.name for p in (repo / "backlog" / "tasks").iterdir()]
    assert names == [f"task-101 - {STUB_SLUG}.md"]


def test_git_repo_root_reports_gits_own_reason(tmp_path: Path) -> None:
    """Not a repository at all still has to say so, and say why."""
    plain = tmp_path / "plain"
    (plain / "backlog").mkdir(parents=True)

    root, reason = sbf.git_repo_root(plain / "backlog")

    assert root is None
    assert "not a git repository" in reason


def test_git_tracked_reads_only_exit_1_as_untracked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken git must not be mistaken for a clean 'not in the index'."""
    repo = _make_repo(tmp_path, [SHORT_103])
    tracked = repo / "backlog" / "tasks" / SHORT_103
    assert sbf.git_tracked(repo, tracked) is True

    untracked = repo / "backlog" / "tasks" / "task-104 - Fresh.md"
    untracked.write_text("---\nid: task-104\n---\n\nBody.\n")
    assert sbf.git_tracked(repo, untracked) is False

    monkeypatch.setattr(
        sbf,
        "run_git",
        lambda *_a, **_kw: subprocess.CompletedProcess([], 128, "", "boom"),
    )
    assert sbf.git_tracked(repo, untracked) is True


def test_plain_rename_refuses_a_dangling_symlink_target(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("keep me\n")
    target = tmp_path / "target.md"
    target.symlink_to(tmp_path / "gone.md")  # points at nothing

    reason = sbf.plain_rename(source, target)

    assert reason is not None and "already exists" in reason
    assert source.read_text() == "keep me\n"
    assert target.is_symlink()


def test_plan_renames_survives_an_unnameable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file with no free name is skipped, not allowed to abort the run."""
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    doomed = tasks / LONG_101
    survivor = tasks / LONG_102
    for path in (doomed, survivor):
        path.write_text("---\nid: task-0\n---\n\nBody.\n")
    monkeypatch.setattr(sbf, "ask_claude", lambda *_a, **_kw: STUB_OUTPUT)
    real_dedupe = sbf.dedupe_target

    def _raise_for_the_first(prefix: str, *args: object) -> str:
        if prefix == "task-101 - ":
            raise RuntimeError("could not find a free name")
        return real_dedupe(prefix, *args)  # type: ignore[arg-type]

    monkeypatch.setattr(sbf, "dedupe_target", _raise_for_the_first)

    plans, counters = sbf.plan_renames([doomed, survivor], sbf.Options())

    assert counters.over_limit == 2 and counters.skipped == 1
    assert [plan.new_name for plan in plans] == [f"task-102 - {STUB_SLUG}.md"]


def test_milestones_are_scanned(tmp_path: Path) -> None:
    """`backlog init` creates milestones/ and its names can clear the cap."""
    repo = _make_repo(tmp_path, [SHORT_103])
    milestones = repo / "backlog" / "milestones"
    milestones.mkdir(parents=True)
    long_milestone = f"m-0 - {LONG_SLUG}.md"
    assert sbf.basename_bytes(long_milestone) > LIMIT
    (milestones / long_milestone).write_text("---\nid: m-0\n---\n\nMilestone.\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "milestone")
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    assert "over-limit=1" in proc.stdout and "renamed=1" in proc.stdout
    assert [p.name for p in milestones.iterdir()] == [f"m-0 - {STUB_SLUG}.md"]


def test_missing_path_is_an_error(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, "exit 1")
    repo = _make_repo(tmp_path, [SHORT_103])
    proc = _run_script(repo, bin_dir, "--path", "nope")
    assert proc.returncode == 2
    assert "is not a directory" in proc.stderr


# --------------------------------------------------------------------------
# Multi-project sweep — discovery, grouping, per-project commit (TASK-236)
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A parent directory holding two projects and three things that are not."""
    root = tmp_path / "tree"
    _make_repo(root, [LONG_101], at="alpha", project_name="alpha")
    _make_repo(root, [LONG_102], at="beta", project_name="beta")
    # A vendored copy of somebody else's backlog: pruned, never swept.
    _write_backlog(root / "alpha" / "node_modules" / "pkg" / "backlog", [], "vendored")
    # config.yml with no artifact directory beside it: one signal is not enough.
    (root / "decoy").mkdir()
    (root / "decoy" / "config.yml").write_text('project_name: "decoy"\n')
    # A backlog root inside a backlog root: a backlog holds artifacts, not
    # projects, so the walk must stop at the outer one.
    _write_backlog(root / "alpha" / "backlog" / "archive", [], "nested")
    # A backlog in no repository at all: nothing to commit to.
    _write_backlog(root / "loose" / "backlog", [LONG_101], "loose")
    return root


@pytest.fixture
def swept(tree: Path, tmp_path: Path) -> tuple[Path, Path]:
    """``tree`` plus a stubbed claude, ready for a CLI sweep."""
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')
    return tree, bin_dir


def test_find_backlog_roots_takes_two_signals_and_prunes(tree: Path) -> None:
    roots = sbf.find_backlog_roots(tree)

    assert roots == [
        tree / "alpha" / "backlog",
        tree / "beta" / "backlog",
        tree / "loose" / "backlog",
    ]


@pytest.mark.parametrize("pruned", sorted(sbf.PRUNE_DIRS))
def test_find_backlog_roots_prunes_every_listed_directory(
    tmp_path: Path, pruned: str
) -> None:
    """A backlog under any pruned directory belongs to somebody else."""
    root = tmp_path / "tree"
    _write_backlog(root / pruned / "vendored" / "backlog", [], "vendored")
    _write_backlog(root / "mine" / "backlog", [], "mine")

    assert sbf.find_backlog_roots(root) == [root / "mine" / "backlog"]


def test_is_backlog_root_needs_config_and_an_artifact_directory(
    tmp_path: Path,
) -> None:
    both = _write_backlog(tmp_path / "both", [], "both")
    assert sbf.is_backlog_root(both) is True

    config_only = tmp_path / "config-only"
    config_only.mkdir()
    (config_only / "config.yml").write_text('project_name: "x"\n')
    assert sbf.is_backlog_root(config_only) is False

    tasks_only = tmp_path / "tasks-only"
    (tasks_only / "tasks").mkdir(parents=True)
    assert sbf.is_backlog_root(tasks_only) is False


def test_discover_projects_groups_by_repo_and_skips_a_root_outside_git(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    projects = sbf.discover_projects(tree)

    assert [project.name for project in projects] == ["alpha", "beta"]
    assert [project.repo_root for project in projects] == [
        (tree / "alpha").resolve(),
        (tree / "beta").resolve(),
    ]
    assert [project.backlog_roots for project in projects] == [
        [tree / "alpha" / "backlog"],
        [tree / "beta" / "backlog"],
    ]
    err = capsys.readouterr().err
    assert f"WARNING: skipping {tree / 'loose' / 'backlog'}" in err
    assert "not in a git repository" in err


def test_discover_projects_folds_a_monorepo_into_one_project(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, [LONG_101], project_name="mono")
    _write_backlog(repo / "sub" / "backlog", [LONG_102], "second-name-ignored")

    projects = sbf.discover_projects(repo)

    assert len(projects) == 1
    assert projects[0].name == "mono"
    assert projects[0].repo_root == repo.resolve()
    assert projects[0].backlog_roots == [repo / "backlog", repo / "sub" / "backlog"]


def test_read_project_name_falls_back_to_the_repository_directory(
    tmp_path: Path,
) -> None:
    backlog = _write_backlog(tmp_path / "anon", [], "unused")
    (backlog / "config.yml").write_text('default_status: "To Do"\n')

    assert sbf.read_project_name(backlog, "anon") == "anon"
    assert sbf.read_project_name(tmp_path / "gone", "anon") == "anon"


def test_dry_run_reports_every_project_and_changes_nothing(
    swept: tuple[Path, Path],
) -> None:
    tree, bin_dir = swept

    proc = _run_script(tree, bin_dir, path=".")

    assert proc.returncode == 0, proc.stderr
    for name in ("alpha", "beta"):
        repo = (tree / name).resolve()
        assert f"== {name} [{repo}] ==" in proc.stdout
        assert f"Would commit 1 rename(s) in {name} [{repo}]" in proc.stdout
    assert f"  -> task-101 - {STUB_SLUG}.md" in proc.stdout
    assert f"  -> task-102 - {STUB_SLUG}.md" in proc.stdout
    assert "projects=2 committed=0 project-errors=0" in proc.stdout
    assert "Dry run: nothing changed." in proc.stdout
    for name, long_name in (("alpha", LONG_101), ("beta", LONG_102)):
        # -uno: the tree fixture plants untracked decoys inside alpha, and
        # what this asserts is that no *tracked* path moved.
        assert _git(tree / name, "status", "--porcelain", "-uno").stdout == ""
        assert _subjects(tree / name) == ["fixtures"]
        assert (tree / name / "backlog" / "tasks" / long_name).is_file()


def test_dry_run_does_not_count_an_untracked_file_as_committable(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path, [LONG_101])
    (repo / "backlog" / "tasks" / LONG_102).write_text("---\nid: task-102\n---\n")
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    proc = _run_script(repo, bin_dir)

    assert proc.returncode == 0, proc.stderr
    assert "over-limit=2" in proc.stdout
    assert f"Would commit 1 rename(s) in fixture [{repo.resolve()}]" in proc.stdout


def test_apply_commits_each_project_on_its_own(swept: tuple[Path, Path]) -> None:
    tree, bin_dir = swept

    proc = _run_script(tree, bin_dir, "--apply", path=".")

    assert proc.returncode == 0, proc.stderr
    assert "renamed=2" in proc.stdout
    assert "projects=2 committed=2 project-errors=0" in proc.stdout
    for name, ident, long_name in (
        ("alpha", "101", LONG_101),
        ("beta", "102", LONG_102),
    ):
        repo = tree / name
        assert f"Committed 1 rename(s) in {name}" in proc.stdout
        assert _subjects(repo) == [_shortened(1), "fixtures"]
        assert _head_changes(repo) == sorted(
            [
                f"A\tbacklog/tasks/task-{ident} - {STUB_SLUG}.md",
                f"D\tbacklog/tasks/{long_name}",
            ]
        )
        # -uno: alpha carries the fixture's untracked decoys either way.
        assert _git(repo, "status", "--porcelain", "-uno").stdout == ""
    # The unversioned backlog is warned about, never touched.
    assert (tree / "loose" / "backlog" / "tasks" / LONG_101).is_file()


def test_a_monorepo_takes_one_commit_for_both_backlogs(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, [LONG_101], project_name="mono")
    _write_backlog(repo / "sub" / "backlog", [LONG_102], "mono")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "second backlog")
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    proc = _run_script(repo, bin_dir, "--apply", path=".")

    assert proc.returncode == 0, proc.stderr
    assert "projects=1 committed=1 project-errors=0" in proc.stdout
    assert _subjects(repo)[0] == _shortened(2)
    assert _head_changes(repo) == sorted(
        [
            f"A\tbacklog/tasks/task-101 - {STUB_SLUG}.md",
            f"D\tbacklog/tasks/{LONG_101}",
            f"A\tsub/backlog/tasks/task-102 - {STUB_SLUG}.md",
            f"D\tsub/backlog/tasks/{LONG_102}",
        ]
    )


def test_the_commit_leaves_a_pre_existing_staged_change_alone(
    tmp_path: Path,
) -> None:
    """A sweep runs over repositories nobody has inspected first."""
    repo = _make_repo(tmp_path, [LONG_101, SHORT_103])
    (repo / "backlog" / "tasks" / SHORT_103).write_text(
        "---\nid: task-103\n---\n\nEdited by the operator.\n"
    )
    _git(repo, "add", "--", f"backlog/tasks/{SHORT_103}")
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    assert _subjects(repo) == [_shortened(1), "fixtures"]
    assert _head_changes(repo) == sorted(
        [
            f"A\tbacklog/tasks/task-101 - {STUB_SLUG}.md",
            f"D\tbacklog/tasks/{LONG_101}",
        ]
    )
    # The operator's edit is still staged, and still uncommitted.
    porcelain = _git(repo, "status", "--porcelain").stdout
    assert porcelain.startswith("M  ")
    assert SHORT_103 in porcelain
    assert "Edited by the operator." not in _git(repo, "show", "HEAD").stdout


def test_an_untracked_rename_stays_out_of_the_project_commit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, [LONG_101])
    (repo / "backlog" / "tasks" / LONG_102).write_text(
        "---\nid: task-102\n---\n\nNever committed.\n"
    )
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    proc = _run_script(repo, bin_dir, "--apply")

    assert proc.returncode == 0, proc.stderr
    # Two files renamed, one of them committed: the untracked one is not.
    assert "renamed=2" in proc.stdout
    assert "committed=1" in proc.stdout
    assert _subjects(repo) == [_shortened(1), "fixtures"]
    assert _head_changes(repo) == sorted(
        [
            f"A\tbacklog/tasks/task-101 - {STUB_SLUG}.md",
            f"D\tbacklog/tasks/{LONG_101}",
        ]
    )
    porcelain = _git(repo, "status", "--porcelain").stdout
    assert porcelain.startswith("??")
    assert f"task-102 - {STUB_SLUG}.md" in porcelain


def test_a_failing_hook_blocks_the_commit_and_no_verify_bypasses_it(
    tmp_path: Path,
) -> None:
    """Another project's commit guard is an answer, not an obstacle."""
    repo = _make_repo(tmp_path, [LONG_101])
    _install_hook(repo, 'printf "BLOCKED: not your commit\\n" >&2\nexit 1')
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, f'printf "%s\\n" "{STUB_OUTPUT}"')

    blocked = _run_script(repo, bin_dir, "--apply")

    assert blocked.returncode == 1
    assert "ERROR: commit failed in fixture" in blocked.stderr
    assert "BLOCKED: not your commit" in blocked.stderr
    assert "committed=0 project-errors=1" in blocked.stdout
    assert _subjects(repo) == ["fixtures"]
    # The rename happened and is staged; only the commit was refused.
    assert "R  " in _git(repo, "status", "--porcelain").stdout

    _git(repo, "reset", "--hard", "-q")
    bypassed = _run_script(repo, bin_dir, "--apply", "--no-verify")

    assert bypassed.returncode == 0, bypassed.stderr
    assert "committed=1 project-errors=0" in bypassed.stdout
    assert _subjects(repo) == [_shortened(1), "fixtures"]
    assert _git(repo, "status", "--porcelain").stdout == ""


def test_a_blocked_project_does_not_strand_the_rest_of_the_sweep(
    swept: tuple[Path, Path],
) -> None:
    tree, bin_dir = swept
    _install_hook(tree / "alpha", "exit 1")

    proc = _run_script(tree, bin_dir, "--apply", path=".")

    assert proc.returncode == 1
    assert "ERROR: commit failed in alpha" in proc.stderr
    assert "projects=2 committed=1 project-errors=1" in proc.stdout
    assert _subjects(tree / "alpha") == ["fixtures"]
    assert _subjects(tree / "beta") == [_shortened(1), "fixtures"]


def test_a_rename_failure_does_not_strand_the_rest_of_the_sweep(
    tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second project is swept even when the first cannot rename at all."""
    monkeypatch.setattr(sbf, "ask_claude", lambda *_a, **_kw: STUB_OUTPUT)
    real_git_mv = sbf.git_mv

    def _fail_in_alpha(repo_root: Path, source: Path, target: Path) -> str | None:
        if repo_root == (tree / "alpha").resolve():
            return "fatal: destination exists"
        return real_git_mv(repo_root, source, target)

    monkeypatch.setattr(sbf, "git_mv", _fail_in_alpha)

    code = sbf.main(["--path", str(tree), "--apply"])

    assert code == 1
    assert (tree / "alpha" / "backlog" / "tasks" / LONG_101).is_file()
    assert _subjects(tree / "alpha") == ["fixtures"]
    assert _subjects(tree / "beta") == [_shortened(1), "fixtures"]


def test_an_unexpected_failure_in_one_project_does_not_stop_the_sweep(
    tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Anything a repository can raise is that project's problem alone."""
    monkeypatch.setattr(sbf, "ask_claude", lambda *_a, **_kw: STUB_OUTPUT)
    real_sweep = sbf.sweep_project

    def _boom(project: sbf.Project, opts: sbf.Options, **kwargs: bool):
        if project.name == "alpha":
            raise OSError("Input/output error")
        return real_sweep(project, opts, **kwargs)

    monkeypatch.setattr(sbf, "sweep_project", _boom)

    code = sbf.main(["--path", str(tree), "--apply"])

    assert code == 1
    assert "ERROR: alpha" in capsys.readouterr().err
    assert _subjects(tree / "alpha") == ["fixtures"]
    assert _subjects(tree / "beta") == [_shortened(1), "fixtures"]


def test_a_tree_with_no_backlog_at_all_says_so(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    (empty / "src").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    _write_stub(bin_dir, "exit 1")

    proc = _run_script(empty, bin_dir, path=".")

    assert proc.returncode == 0
    assert "WARNING: no backlog project found" in proc.stderr
    assert "projects=0 committed=0 project-errors=0" in proc.stdout
