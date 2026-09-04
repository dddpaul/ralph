# /// script
# requires-python = ">=3.14"
# ///
"""Shorten over-limit backlog filenames using a ``claude -p`` semantic slug.

Retroactive counterpart to ``.claude/hooks/filename-length-guard.sh``
(TASK-227): the pre-commit guard blocks *new* paths whose name components
exceed the 125-byte cap the ecryptfs sync target imposes, while this script
repairs backlog artifacts that are *already* over it.

The rename is filename-only. The ``<type>-<id> - `` prefix and the ``.md``
suffix are preserved and only the slug is regenerated -- safe because
backlog.md addresses artifacts by their ``id:`` frontmatter, not by filename.
The ``title:`` frontmatter is left untouched as the historical record.

``claude -p`` output is treated as untrusted: the normalizer below, not the
prompt, is what guarantees a valid slug. When claude errors out or returns
nothing usable after one retry, the existing slug is truncated instead, so a
file is never left over the limit.

Dry-run by default; ``--apply`` performs the renames with ``git mv``, or
with a plain rename for a file git does not track yet.

Usage::

    uv run scripts/shorten-backlog-filenames.py            # dry run
    uv run scripts/shorten-backlog-filenames.py --apply
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# Byte cap shared with filename-length-guard.sh. Keep the two in sync: this
# script's output is designed to pass that guard by construction.
DEFAULT_LIMIT = 125
DEFAULT_MODEL = "haiku"
DEFAULT_PATH = "backlog"

# Live artifact directories, i.e. every one `backlog init` creates. Milestones
# belong here even though backlog.md caps their slug itself: it slices at 50
# UTF-16 code units, which is 150 bytes of CJK, so a milestone name can clear
# the byte cap. Archive/completed hold historical files and are opt-in via
# --include-archive; their walk recurses, so archived milestones come along.
SCAN_SUBDIRS = ("tasks", "docs", "decisions", "drafts", "milestones")
ARCHIVE_SUBDIRS = ("archive", "completed")

CLAUDE_TIMEOUT_S = 60.0
CONTENT_CAP = 2500
MIN_SLUG_BYTES = 3
ATTEMPTS = 2  # one call plus exactly one retry
MAX_COLLISION_SUFFIX = 99
# Whitespace-separated words tolerated on a line that is not already a bare
# kebab-case slug. Beyond this the line reads as prose, not a proposal.
MAX_SLUG_WORDS = 4

# `<type>-<id> - <slug>.md`, e.g. `task-231 - Add-a-script.md`. Ids stay
# strings: backlog subtasks carry dotted ids such as `task-90.1`.
NAME_RE = re.compile(
    r"^(?P<kind>[a-z][a-z0-9]*)-(?P<ident>\d+(?:\.\d+)*) - (?P<slug>.+)\.md$"
)
# A response that already obeys the prompt: one bare kebab-case token.
CLEAN_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<fm>.*?)\n---\n?(?P<body>.*)\Z", re.DOTALL)
TITLE_RE = re.compile(r"^title:[ \t]*(?P<title>.+?)[ \t]*$", re.MULTILINE)

PROMPT_TEMPLATE = """\
Propose a short filename slug for the backlog artifact below.

Rules:
- Output ONLY the slug, on a single line. No prose, no quotes, no code fence.
- Lowercase kebab-case: letters, digits and hyphens only.
- At most {budget} characters.
- 3-8 words naming the artifact's subject; drop filler words.

Current slug: {slug}
Title: {title}

Content:
{content}
"""


def warn(message: str) -> None:
    """Write ``message`` to stderr after flushing stdout.

    The plan rows go to stdout and the warnings here to stderr. Without the
    flush the two streams are buffered independently and a piped run
    interleaves them out of order, detaching a warning from the row it
    belongs next to.
    """
    sys.stdout.flush()
    print(message, file=sys.stderr, flush=True)


def basename_bytes(name: str) -> int:
    """Return the byte length of ``name``.

    This is the ``LC_ALL=C`` measurement: filename-length-guard.sh exports
    ``LC_ALL=C`` so bash's ``${#name}`` counts bytes rather than characters,
    because ecryptfs caps bytes and a UTF-8 locale under-counts multibyte
    names. ``os.fsencode`` yields exactly the bytes the filesystem stores.
    """
    return len(os.fsencode(name))


@dataclass(frozen=True)
class ParsedName:
    """A backlog basename split into its stable prefix and its slug."""

    prefix: str
    slug: str


def parse_prefix(name: str) -> ParsedName | None:
    """Split ``name`` into the ``<type>-<id> - `` prefix and the slug.

    Returns ``None`` for anything that is not a backlog artifact filename.
    """
    match = NAME_RE.match(name)
    if match is None:
        return None
    prefix = f"{match['kind']}-{match['ident']} - "
    return ParsedName(prefix=prefix, slug=match["slug"])


def slug_budget(prefix: str, limit: int) -> int:
    """Bytes available for the slug once the prefix and ``.md`` are paid for.

    Computed per file: `task-` and `decision-` prefixes and id widths differ.
    """
    return limit - basename_bytes(prefix) - basename_bytes(".md")


def _cut_bytes(text: str, budget: int) -> str:
    """Cut ``text`` to at most ``budget`` bytes without splitting a character."""
    if budget <= 0:
        return ""
    raw = text.encode("utf-8")
    if len(raw) <= budget:
        return text
    return raw[:budget].decode("utf-8", errors="ignore")


def trim_to_budget(slug: str, budget: int) -> str:
    """Trim ``slug`` to ``budget`` bytes, preferring a hyphen boundary."""
    trimmed = _cut_bytes(slug, budget)
    if trimmed != slug:
        head, sep, _ = trimmed.rpartition("-")
        if sep and head:
            trimmed = head
    return trimmed.strip("-")


def pick_slug_line(raw: str) -> str:
    """Choose the line of ``raw`` most likely to be the proposed slug.

    Two passes, because "output ONLY the slug" is a request, not a
    guarantee. A model that adds a preamble still puts the slug on a line of
    its own, so an already-conforming kebab-case line anywhere in the output
    wins over position. Only when there is no such line does the first
    non-empty, non-fence line get used -- and then just when it is short
    enough to be a slug: ``Here is the slug you asked for:`` is a sentence,
    and returning ``""`` for it routes the artifact to the retry and then
    the FALLBACK truncation instead of onto the filesystem.
    """
    lines = [candidate.strip() for candidate in raw.splitlines()]
    for candidate in lines:
        if CLEAN_SLUG_RE.match(candidate) and len(candidate) >= MIN_SLUG_BYTES:
            return candidate
    for candidate in lines:
        if candidate and not candidate.startswith("```"):
            words = candidate.split()
            return candidate if len(words) <= MAX_SLUG_WORDS else ""
    return ""


def normalize_slug(raw: str, budget: int) -> str:
    """Coerce untrusted ``claude -p`` output into a filename-safe slug.

    The prompt asks for a bare kebab-case slug; this is what enforces it.
    Returns ``""`` when nothing usable survives.
    """
    line = pick_slug_line(raw)
    hyphenated = re.sub(r"[\s_/\\]+", "-", line.lower())
    cleaned = re.sub(r"[^a-z0-9-]+", "", hyphenated)
    collapsed = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return trim_to_budget(collapsed, budget)


def dedupe_target(prefix: str, slug: str, budget: int, taken: Collection[str]) -> str:
    """Return a basename not present in ``taken``, suffixing ``-2``/``-3``/...

    The suffix eats into the slug budget, so the slug is re-trimmed to keep
    the final basename within the limit.
    """
    candidate = f"{prefix}{slug}.md"
    if candidate not in taken:
        return candidate
    for n in range(2, MAX_COLLISION_SUFFIX + 1):
        suffix = f"-{n}"
        stem = trim_to_budget(slug, budget - basename_bytes(suffix))
        candidate = f"{prefix}{stem}{suffix}.md"
        if candidate not in taken:
            return candidate
    raise RuntimeError(f"could not find a free name for {prefix}{slug}.md")


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return ``(frontmatter, body)``; frontmatter is ``""`` when absent."""
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return "", text
    return match["fm"], match["body"]


def content_slice(text: str, cap: int = CONTENT_CAP) -> tuple[str, str]:
    """Return ``(title, bounded body slice)`` for the ``claude -p`` prompt."""
    frontmatter, body = split_frontmatter(text)
    title_match = TITLE_RE.search(frontmatter)
    title = title_match["title"].strip("'\"") if title_match else ""
    return title, body.strip()[:cap]


def build_prompt(title: str, slug: str, budget: int, content: str) -> str:
    """Render the slug-proposal prompt for one artifact."""
    return PROMPT_TEMPLATE.format(
        budget=budget, slug=slug, title=title or "(none)", content=content
    )


def ask_claude(prompt: str, model: str, timeout: float) -> str | None:
    """Run ``claude -p``; return raw stdout, or ``None`` on any failure."""
    try:
        proc = subprocess.run(
            ["claude", "-p", "--model", model, prompt],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


@dataclass(frozen=True)
class Options:
    """Runtime knobs shared by the planning helpers."""

    limit: int = DEFAULT_LIMIT
    model: str = DEFAULT_MODEL
    timeout: float = CLAUDE_TIMEOUT_S


def propose_slug(
    parsed: ParsedName, budget: int, text: str, opts: Options
) -> tuple[str, bool]:
    """Return ``(slug, used_fallback)`` for one over-limit artifact.

    Asks claude up to ``ATTEMPTS`` times (one call plus exactly one retry).
    If nothing usable comes back, falls back to truncating the existing slug
    so the file always ends up under the limit rather than being skipped.
    """
    title, content = content_slice(text)
    prompt = build_prompt(title, parsed.slug, budget, content)
    for _ in range(ATTEMPTS):
        raw = ask_claude(prompt, opts.model, opts.timeout)
        if raw is None:
            continue
        slug = normalize_slug(raw, budget)
        if basename_bytes(slug) >= MIN_SLUG_BYTES:
            return slug, False
    fallback = trim_to_budget(parsed.slug, budget) or _cut_bytes(parsed.slug, budget)
    # `untitled` is 8 bytes; cut it too, or a tiny budget would be blown by
    # the very last resort.
    return fallback or _cut_bytes("untitled", budget), True


@dataclass
class Rename:
    """One planned rename of ``path`` to ``new_name`` in the same directory."""

    path: Path
    new_name: str
    markers: list[str] = field(default_factory=list)

    @property
    def target(self) -> Path:
        return self.path.with_name(self.new_name)

    @property
    def label(self) -> str:
        return "+".join(self.markers) if self.markers else "OK"


@dataclass
class Counters:
    """End-of-run tallies."""

    scanned: int = 0
    over_limit: int = 0
    renamed: int = 0
    fallbacks: int = 0
    collisions: int = 0
    skipped: int = 0
    errors: int = 0


def collect_files(root: Path, include_archive: bool) -> list[Path]:
    """Return every backlog markdown file to consider, in a stable order."""
    subdirs = list(SCAN_SUBDIRS)
    if include_archive:
        subdirs += list(ARCHIVE_SUBDIRS)
    found: list[Path] = []
    for sub in subdirs:
        directory = root / sub
        if directory.is_dir():
            found.extend(p for p in directory.rglob("*.md") if p.is_file())
    return sorted(found)


def plan_renames(files: Sequence[Path], opts: Options) -> tuple[list[Rename], Counters]:
    """Decide a new name for every over-limit file. Performs no renames."""
    counters = Counters(scanned=len(files))
    taken: dict[Path, set[str]] = {}
    plans: list[Rename] = []
    for path in files:
        if basename_bytes(path.name) <= opts.limit:
            continue
        counters.over_limit += 1
        parsed = parse_prefix(path.name)
        if parsed is None:
            counters.skipped += 1
            warn(f"WARNING: skipping {path}: name is not '<type>-<id> - <slug>.md'")
            continue
        budget = slug_budget(parsed.prefix, opts.limit)
        if budget < MIN_SLUG_BYTES:
            counters.skipped += 1
            warn(
                f"WARNING: skipping {path}: prefix leaves no room for a slug "
                f"under the {opts.limit}-byte limit"
            )
            continue
        slug, used_fallback = propose_slug(
            parsed, budget, path.read_text(encoding="utf-8", errors="replace"), opts
        )
        claimed = taken.setdefault(
            path.parent, {p.name for p in path.parent.glob("*.md")}
        )
        try:
            new_name = dedupe_target(parsed.prefix, slug, budget, claimed)
        except RuntimeError as exc:
            # Every -2..-99 suffix is taken. One unnameable file must not
            # abort the run and strand the ones after it.
            counters.skipped += 1
            warn(f"WARNING: skipping {path}: {exc}")
            continue
        claimed.add(new_name)
        plan = Rename(path=path, new_name=new_name)
        if used_fallback:
            plan.markers.append("FALLBACK")
            counters.fallbacks += 1
        if new_name != f"{parsed.prefix}{slug}.md":
            plan.markers.append("COLLISION")
            counters.collisions += 1
        plans.append(plan)
    return plans, counters


def run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """Run git in ``cwd`` with ``safe.directory`` set; ``None`` if it cannot run.

    ``safe.directory`` must name a *resolved* path -- a relative one is a
    silent no-op -- and the container this runs in occasionally reports
    dubious ownership, at which point every git call fails until the
    directory is listed. ``LC_ALL=C`` keeps the stderr we quote stable.
    """
    try:
        return subprocess.run(
            ["git", "-c", f"safe.directory={cwd}", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except OSError:
        return None


def git_repo_root(start: Path) -> tuple[Path | None, str]:
    """Return ``(git top-level containing start, "")``, or ``(None, reason)``.

    The reason is git's own stderr: "is not inside a git repository" is a
    misleading thing to print at a repository whose ownership git merely
    finds dubious.
    """
    proc = run_git(start.resolve(), "rev-parse", "--show-toplevel")
    if proc is None:
        return None, "git is not on PATH"
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"git rev-parse exited {proc.returncode}"
    return Path(proc.stdout.strip()), ""


def git_tracked(repo_root: Path, path: Path) -> bool:
    """Return whether ``path`` is in ``repo_root``'s index."""
    root = repo_root.resolve()
    proc = run_git(
        root, "ls-files", "--error-unmatch", "--", str(path.resolve().relative_to(root))
    )
    return proc is not None and proc.returncode == 0


def git_mv(repo_root: Path, source: Path, target: Path) -> str | None:
    """``git mv`` ``source`` to ``target``; return stderr on failure."""
    root = repo_root.resolve()
    proc = run_git(
        root,
        "mv",
        "--",
        str(source.resolve().relative_to(root)),
        str(target.resolve().parent.relative_to(root) / target.name),
    )
    if proc is None:
        return "git is not on PATH"
    if proc.returncode != 0:
        return proc.stderr.strip() or f"git mv exited {proc.returncode}"
    return None


def plain_rename(source: Path, target: Path) -> str | None:
    """Rename an untracked file; return the reason on failure.

    ``Path.rename`` overwrites silently on POSIX, so the target is checked
    first: a plan is built against a directory listing taken earlier and a
    stale one must not cost a file.
    """
    if target.exists():
        return f"{target.name} already exists"
    try:
        source.rename(target)
    except OSError as exc:
        return str(exc)
    return None


def report(plan: Rename) -> None:
    """Print the ``old -> new`` row for one planned rename."""
    old_bytes = basename_bytes(plan.path.name)
    new_bytes = basename_bytes(plan.new_name)
    print(f"{plan.path}  ({old_bytes} bytes)")
    print(f"  -> {plan.new_name}  ({new_bytes} bytes)  [{plan.label}]")


def apply_renames(plans: Sequence[Rename], root: Path, counters: Counters) -> None:
    """Perform every planned rename, reporting failures.

    Tracked files move with ``git mv`` so the rename lands staged; untracked
    ones fall back to a plain rename.
    """
    repo_root, reason = git_repo_root(root)
    if repo_root is None:
        warn(f"ERROR: cannot resolve the git repository for {root}: {reason}")
        counters.errors += len(plans)
        return
    for plan in plans:
        # `git mv` refuses a file it does not track, which is exactly how an
        # over-limit file arrives: the pre-commit guard rejects the commit
        # that would have added it. Rename it anyway rather than leave it
        # over the limit, and say so, because nothing gets staged.
        tracked = git_tracked(repo_root, plan.path)
        if tracked:
            error = git_mv(repo_root, plan.path, plan.target)
        else:
            error = plain_rename(plan.path, plan.target)
        if error is not None:
            counters.errors += 1
            verb = "git mv" if tracked else "rename"
            warn(f"ERROR: {verb} failed for {plan.path}: {error}")
            continue
        counters.renamed += 1
        if not tracked:
            warn(
                f"NOTICE: {plan.path} is untracked; renamed to {plan.new_name} "
                "without git. Run `git add` to stage it."
            )


def print_summary(counters: Counters, apply: bool) -> None:
    """Print the end-of-run tally."""
    print(
        f"Summary: scanned={counters.scanned} over-limit={counters.over_limit} "
        f"renamed={counters.renamed} fallbacks={counters.fallbacks} "
        f"collisions={counters.collisions} skipped={counters.skipped} "
        f"errors={counters.errors}"
    )
    if not apply:
        print("Dry run: nothing changed. Re-run with --apply to rename.")


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description=(
            "Rename backlog markdown files whose basename exceeds the "
            "filename byte cap, using a claude -p semantic slug."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the renames with git mv (default: dry run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"basename byte cap (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"model passed to claude -p (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--path",
        default=DEFAULT_PATH,
        help=f"backlog root to scan (default: {DEFAULT_PATH})",
    )
    parser.add_argument(
        "--include-archive",
        action="store_true",
        help="also scan archive/ and completed/ (default: live artifacts only)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=CLAUDE_TIMEOUT_S,
        help=f"per-call claude timeout in seconds (default: {CLAUDE_TIMEOUT_S:g})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Scan, plan, report and (with ``--apply``) perform the renames."""
    args = parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        warn(f"ERROR: {root} is not a directory")
        return 2
    opts = Options(limit=args.limit, model=args.model, timeout=args.timeout)
    files = collect_files(root, include_archive=args.include_archive)
    plans, counters = plan_renames(files, opts)
    for plan in plans:
        report(plan)
    if args.apply:
        apply_renames(plans, root, counters)
    print_summary(counters, apply=args.apply)
    return 1 if counters.errors else 0


if __name__ == "__main__":
    sys.exit(main())
