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

``--path`` names a tree to sweep, not necessarily one backlog: every backlog
root under it is discovered, grouped by the git repository that owns it, and
each project is renamed and then committed on its own before the next one is
touched. A single backlog root is the degenerate one-project case, so
``--path backlog`` keeps behaving as it always has.

Usage::

    uv run scripts/shorten-backlog-filenames.py            # dry run, this repo
    uv run scripts/shorten-backlog-filenames.py --apply
    uv run scripts/shorten-backlog-filenames.py --path ~/projects --apply
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, field, fields
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

# `backlog init` always writes config.yml, but a config.yml on its own says
# nothing -- plenty of tools ship one. Requiring an artifact directory next to
# it is the second signal that makes the pair mean "a backlog lives here".
BACKLOG_CONFIG = "config.yml"
# Directories a sweep must not walk into: vendored trees and build output can
# hold a config.yml + tasks/ pair that belongs to nobody, and .git is large
# and never interesting.
PRUNE_DIRS = frozenset(
    {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", "dist", "build"}
)
PROJECT_NAME_RE = re.compile(r"^project_name:[ \t]*(?P<name>.+?)[ \t]*$", re.MULTILINE)

# Housekeeping commit; the count is the only variable part, so no model is
# consulted for it.
COMMIT_MESSAGE = (
    "chore(backlog): shorten {count} over-limit filename(s) for ecryptfs sync"
)

CLAUDE_TIMEOUT_S = 60.0
CONTENT_CAP = 2500
MIN_SLUG_BYTES = 3
ATTEMPTS = 2  # one call plus exactly one retry
MAX_COLLISION_SUFFIX = 99
# Whitespace-separated words tolerated on a line that is not already a bare
# kebab-case slug. Beyond this the line reads as prose, not a proposal.
MAX_SLUG_WORDS = 4
# Openers that mark a line as a refusal or a first-person aside rather than a
# proposal. A word count cannot tell the two apart -- `I cannot help` and
# `Shorten Backlog Filenames` are both three words -- so the fallback pass
# needs a content signal as well as a length one. Contracted spellings are
# folded onto their bare form (`i'm` -> `im`) by `opening_token`.
REFUSAL_OPENERS = frozenset(
    {
        "i",
        "im",
        "ive",
        "sorry",
        "apologies",
        "unable",
        "cannot",
        "cant",
        "unfortunately",
    }
)

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


def opening_token(line: str) -> str:
    """Return ``line``'s first word, folded for a stop-list comparison.

    Surrounding punctuation is dropped (``Sorry,`` -> ``sorry``) and inner
    apostrophes, straight or curly, are removed (``I'm`` -> ``im``) so one
    entry covers a contraction and its expansion. Nothing else is stripped,
    which is what keeps ``i18n`` from folding onto ``i``.
    """
    words = line.split()
    if not words:
        return ""
    token = words[0].lower().replace("\u2019", "").replace("'", "")
    return re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", token)


def pick_slug_line(raw: str) -> str:
    """Choose the line of ``raw`` most likely to be the proposed slug.

    Two passes, because "output ONLY the slug" is a request, not a
    guarantee. A model that adds a preamble still puts the slug on a line of
    its own, so an already-conforming kebab-case line anywhere in the output
    wins over position. Only when there is no such line does the first
    non-empty, non-fence line get used -- and then only if it looks like a
    proposal rather than an answer *about* the request.

    Two signals disqualify it. Length: ``Here is the slug you asked for:``
    is a sentence. Content: a refusal short enough to clear the word cap,
    such as ``I cannot help``, would otherwise pass the byte minimum and
    name the file ``i-cannot-help``, so the opening word is matched against
    REFUSAL_OPENERS. Either way ``""`` routes the artifact to the retry and
    then the FALLBACK truncation instead of onto the filesystem.

    Both signals are confined to this pass. A line matching CLEAN_SLUG_RE
    has obeyed the prompt and is returned above without ever reaching the
    stop-list, so a genuine ``cannot-reproduce-the-hang`` slug survives.
    """
    lines = [candidate.strip() for candidate in raw.splitlines()]
    for candidate in lines:
        if CLEAN_SLUG_RE.match(candidate) and len(candidate) >= MIN_SLUG_BYTES:
            return candidate
    for candidate in lines:
        if not candidate or candidate.startswith("```"):
            continue
        prose = len(candidate.split()) > MAX_SLUG_WORDS
        refusal = opening_token(candidate) in REFUSAL_OPENERS
        return "" if prose or refusal else candidate
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
    """File tallies, kept per project and folded into the run total."""

    scanned: int = 0
    over_limit: int = 0
    renamed: int = 0
    fallbacks: int = 0
    collisions: int = 0
    skipped: int = 0
    errors: int = 0

    def merge(self, other: Counters) -> None:
        """Add ``other``'s tallies to this one.

        Field-driven rather than written out, so a counter added later is
        summed across projects without anyone having to remember to.
        """
        for spec in fields(self):
            total = getattr(self, spec.name) + getattr(other, spec.name)
            setattr(self, spec.name, total)


@dataclass
class SweepTally:
    """Project tallies for the run: how many were seen, committed, failed."""

    projects: int = 0
    committed: int = 0
    errors: int = 0


@dataclass
class ProjectResult:
    """What one project's pass produced."""

    counters: Counters
    committed: bool = False
    failed: bool = False


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


def run_git(
    cwd: Path, *args: str, trust: Sequence[Path] = ()
) -> subprocess.CompletedProcess[str] | None:
    """Run git in ``cwd``; return ``None`` when git cannot be run at all.

    The container this runs in occasionally reports dubious ownership, at
    which point every git call fails until the repository is listed in
    ``safe.directory``. That entry must name the *resolved top-level*: a
    relative path is a silent no-op, and so is a subdirectory of the
    repository. Callers that already know the top-level get it as ``cwd``;
    ``trust`` is for the discovery call, which does not yet. ``LC_ALL=C``
    keeps the stderr we quote stable.
    """
    config: list[str] = []
    for path in trust or (cwd,):
        config += ["-c", f"safe.directory={path}"]
    try:
        return subprocess.run(
            ["git", *config, "-C", str(cwd), *args],
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
    # The top-level is what git wants trusted and is exactly what this call
    # exists to find, so list `start` and every ancestor: the top-level is
    # one of them. Naming ancestors of a path the user pointed us at is far
    # narrower than `safe.directory=*`, and it is a per-invocation `-c`.
    resolved = start.resolve()
    proc = run_git(
        resolved, "rev-parse", "--show-toplevel", trust=(resolved, *resolved.parents)
    )
    if proc is None:
        return None, "git is not on PATH"
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"git rev-parse exited {proc.returncode}"
    return Path(proc.stdout.strip()), ""


def git_tracked(repo_root: Path, path: Path) -> bool:
    """Return whether ``path`` is in ``repo_root``'s index.

    ``ls-files --error-unmatch`` exits 1 for a path git does not track and
    128 for a git that could not answer at all. Only the first is really
    "untracked"; anything else is reported as tracked so the rename goes
    through ``git mv`` and surfaces git's own error, rather than quietly
    taking the plain-rename path under a NOTICE that is not true.
    """
    root = repo_root.resolve()
    proc = run_git(
        root, "ls-files", "--error-unmatch", "--", str(path.resolve().relative_to(root))
    )
    return proc is None or proc.returncode != 1


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


def git_commit(
    repo_root: Path, paths: Iterable[Path], message: str, no_verify: bool
) -> str | None:
    """Commit exactly ``paths`` in ``repo_root``; return the reason on failure.

    Pathspec form, so the commit carries the renames and nothing else: a
    sweep runs unattended over repositories whose working state nobody has
    inspected, and staged-but-unrelated work must not be swept into a
    housekeeping commit. It lands on whatever branch is checked out.

    Hooks run unless ``no_verify``: another project's commit-prefix guard
    rejecting this message is a real answer, not a bug to route around.
    """
    root = repo_root.resolve()
    pathspecs = [str(path.resolve().relative_to(root)) for path in paths]
    options = ["--no-verify"] if no_verify else []
    proc = run_git(root, "commit", *options, "-m", message, "--", *pathspecs)
    if proc is None:
        return "git is not on PATH"
    if proc.returncode != 0:
        # A blocking hook writes to stdout as often as to stderr, and its
        # message is the whole reason the commit did not happen.
        detail = proc.stderr.strip() or proc.stdout.strip()
        return detail or f"git-commit exited {proc.returncode}"
    return None


def plain_rename(source: Path, target: Path) -> str | None:
    """Rename an untracked file; return the reason on failure.

    ``Path.rename`` overwrites silently on POSIX, so the target is checked
    first: a plan is built against a directory listing taken earlier and a
    stale one must not cost a file. The check is ``lexists``, because a
    dangling symlink occupies the name just as well as a file does.
    """
    if os.path.lexists(target):
        return f"{target.name} already exists"
    try:
        source.rename(target)
    except OSError as exc:
        return str(exc)
    return None


@dataclass
class Project:
    """One git repository and the backlog roots the sweep found inside it."""

    repo_root: Path
    name: str
    backlog_roots: list[Path] = field(default_factory=list)


def is_backlog_root(path: Path) -> bool:
    """Return whether ``path`` looks like a backlog root.

    Two signals, both required: the ``config.yml`` every ``backlog init``
    writes, and at least one of the artifact directories it creates. Either
    alone is common enough elsewhere to produce false positives.
    """
    return (path / BACKLOG_CONFIG).is_file() and any(
        (path / sub).is_dir() for sub in SCAN_SUBDIRS
    )


def find_backlog_roots(root: Path) -> list[Path]:
    """Return every backlog root at or under ``root``, in a stable order.

    The walk does not descend into a root it has found: a backlog holds
    artifacts, not further projects, and its archive/ carries the same
    directory names a nested project would.
    """
    found: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(root):
        current = Path(dirpath)
        if is_backlog_root(current):
            found.append(current)
            dirnames.clear()
            continue
        # Sorted so two runs over one tree report the projects in one order.
        dirnames[:] = sorted(name for name in dirnames if name not in PRUNE_DIRS)
    return found


def read_project_name(backlog_root: Path, default: str) -> str:
    """Return ``project_name`` from ``backlog_root``'s config.yml.

    Read with a regex rather than a YAML parser to keep the script on the
    standard library, which is what lets it run under ``uv run`` with no
    dependency resolution at all. A missing or unreadable key falls back to
    ``default``.
    """
    try:
        text = (backlog_root / BACKLOG_CONFIG).read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return default
    match = PROJECT_NAME_RE.search(text)
    if match is None:
        return default
    return match["name"].strip("'\"") or default


def discover_projects(root: Path) -> list[Project]:
    """Return the committable projects under ``root``, one per git repository.

    Backlog roots are grouped by the repository that owns them, so a
    monorepo holding several backlogs is one project and takes one commit.
    A root in no repository has nothing to commit to and is dropped with a
    warning rather than renamed without version control.
    """
    projects: dict[Path, Project] = {}
    for backlog_root in find_backlog_roots(root):
        repo_root, reason = git_repo_root(backlog_root)
        if repo_root is None:
            warn(
                f"WARNING: skipping {backlog_root}: "
                f"not in a git repository ({reason})"
            )
            continue
        key = repo_root.resolve()
        project = projects.get(key)
        if project is None:
            # Named after the first root found in the repository; a second
            # backlog in the same repository is part of that same project.
            project = Project(
                repo_root=key, name=read_project_name(backlog_root, key.name)
            )
            projects[key] = project
        project.backlog_roots.append(backlog_root)
    return list(projects.values())


def report(plan: Rename) -> None:
    """Print the ``old -> new`` row for one planned rename."""
    old_bytes = basename_bytes(plan.path.name)
    new_bytes = basename_bytes(plan.new_name)
    print(f"{plan.path}  ({old_bytes} bytes)")
    print(f"  -> {plan.new_name}  ({new_bytes} bytes)  [{plan.label}]")


def apply_renames(
    plans: Sequence[Rename], repo_root: Path, counters: Counters
) -> list[Rename]:
    """Perform every planned rename; return the ones git has staged.

    Tracked files move with ``git mv`` so the rename lands staged; untracked
    ones fall back to a plain rename. Only the staged ones come back, because
    only they can be committed -- adding a file the repository has never seen
    is a larger step than renaming one, and not one to take unattended.
    """
    staged: list[Rename] = []
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
        if tracked:
            staged.append(plan)
        else:
            warn(
                f"NOTICE: {plan.path} is untracked; renamed to {plan.new_name} "
                "without git. Run `git add` to stage it."
            )
    return staged


def sweep_project(
    project: Project,
    opts: Options,
    *,
    apply: bool,
    include_archive: bool,
    no_verify: bool,
) -> ProjectResult:
    """Plan, rename and commit one project, reporting what it did.

    A failure here is the project's own: it is reported and returned, never
    raised, so one blocked repository cannot strand the rest of the sweep.
    """
    print(f"== {project.name} [{project.repo_root}] ==")
    print(f"   backlog: {', '.join(str(root) for root in project.backlog_roots)}")
    files: list[Path] = []
    for backlog_root in project.backlog_roots:
        files.extend(collect_files(backlog_root, include_archive=include_archive))
    plans, counters = plan_renames(files, opts)
    for plan in plans:
        report(plan)
    if not apply:
        # Count what would actually be committed, not what would be renamed:
        # an untracked file is renamed but never joins the commit.
        pending = sum(1 for plan in plans if git_tracked(project.repo_root, plan.path))
        print(
            f"Would commit {pending} rename(s) in "
            f"{project.name} [{project.repo_root}]"
        )
        return ProjectResult(counters=counters)
    staged = apply_renames(plans, project.repo_root, counters)
    result = ProjectResult(counters=counters, failed=counters.errors > 0)
    if not staged:
        return result
    paths = [path for plan in staged for path in (plan.path, plan.target)]
    error = git_commit(
        project.repo_root,
        paths,
        COMMIT_MESSAGE.format(count=len(staged)),
        no_verify=no_verify,
    )
    if error is None:
        result.committed = True
        print(f"Committed {len(staged)} rename(s) in {project.name}")
    else:
        result.failed = True
        warn(f"ERROR: commit failed in {project.name} [{project.repo_root}]: {error}")
    return result


def print_summary(counters: Counters, tally: SweepTally, apply: bool) -> None:
    """Print the end-of-run tally: files first, then projects."""
    print(
        f"Summary: scanned={counters.scanned} over-limit={counters.over_limit} "
        f"renamed={counters.renamed} fallbacks={counters.fallbacks} "
        f"collisions={counters.collisions} skipped={counters.skipped} "
        f"errors={counters.errors} projects={tally.projects} "
        f"committed={tally.committed} project-errors={tally.errors}"
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
        help=(
            "tree to sweep, or a single backlog root; every backlog under it "
            f"is found and committed to its own repository (default: {DEFAULT_PATH})"
        ),
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="bypass git hooks when committing (default: hooks run)",
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
    """Sweep every project under ``--path``, one project at a time."""
    args = parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        warn(f"ERROR: {root} is not a directory")
        return 2
    opts = Options(limit=args.limit, model=args.model, timeout=args.timeout)
    projects = discover_projects(root)
    if not projects:
        warn(f"WARNING: no backlog project found under {root}")
    counters = Counters()
    tally = SweepTally()
    for project in projects:
        tally.projects += 1
        try:
            result = sweep_project(
                project,
                opts,
                apply=args.apply,
                include_archive=args.include_archive,
                no_verify=args.no_verify,
            )
        except (OSError, ValueError) as exc:
            # A sweep meets repositories nobody has inspected first. An
            # unreadable file or a backlog symlinked out of its own repository
            # costs that project, not the rest of the fleet.
            warn(f"ERROR: {project.name} [{project.repo_root}] failed: {exc}")
            tally.errors += 1
            continue
        counters.merge(result.counters)
        tally.committed += int(result.committed)
        tally.errors += int(result.failed)
    print_summary(counters, tally, apply=args.apply)
    return 1 if counters.errors or tally.errors else 0


if __name__ == "__main__":
    sys.exit(main())
