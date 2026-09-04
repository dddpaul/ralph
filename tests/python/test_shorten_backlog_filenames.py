"""Tests for ``scripts/shorten-backlog-filenames.py`` (TASK-231).

The script is a hyphenated PEP 723 file, so it is loaded by path rather than
imported. Unit tests cover the pure layer; the integration tests drive the CLI
end to end over a throwaway git repository with a stubbed ``claude`` on PATH.
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


def _make_repo(tmp_path: Path, names: list[str]) -> Path:
    repo = tmp_path / "repo"
    tasks = repo / "backlog" / "tasks"
    tasks.mkdir(parents=True)
    for index, name in enumerate(names):
        (tasks / name).write_text(
            f"---\nid: task-{index}\ntitle: {name}\n---\n\nBody of {name}.\n"
        )
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixtures")
    return repo


def _run_script(repo: Path, bin_dir: Path, *args: str, **env_extra: str):
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--path", "backlog", *args],
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
        "collisions=1 skipped=1 errors=0" in proc.stdout
    )
    assert "Dry run: nothing changed." in proc.stdout

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
    # git mv stages the rename and preserves the body.
    staged = _git(repo, "status", "--porcelain").stdout
    assert staged.count("R  ") == 2
    assert f"task-102 - {STUB_SLUG}.md" in staged
    moved = (tasks / f"task-102 - {STUB_SLUG}.md").read_text()
    assert f"Body of {LONG_102}." in moved


def test_apply_output_passes_the_filename_length_guard(
    stubbed_repo: tuple[Path, Path],
) -> None:
    repo, bin_dir = stubbed_repo
    assert _run_script(repo, bin_dir, "--apply").returncode == 0
    for path in (repo / "backlog" / "tasks").iterdir():
        if path.name != UNPARSEABLE:  # skipped by design, still over-limit
            assert sbf.basename_bytes(path.name) <= LIMIT
    if not GUARD.is_file():  # pragma: no cover - guard ships with the repo
        pytest.skip("filename-length-guard.sh not present")
    # `git mv` leaves the renames staged; run the real pre-commit guard on them.
    guard = subprocess.run(
        ["bash", str(GUARD)], cwd=repo, capture_output=True, text=True
    )
    assert guard.returncode == 0, guard.stderr


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

    sbf.apply_renames(plans, repo / "backlog", counters)

    assert counters.errors == 1 and counters.renamed == 0
    assert target.read_text() == "Squatter.\n"
    assert (tasks / LONG_102).is_file()


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
