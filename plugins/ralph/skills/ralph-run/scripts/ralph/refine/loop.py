"""Refinement loop, output structure, and summary (US-005).

Ralph's non-code sibling loop. Where :mod:`ralph.loop` iterates a *coder* over
backlog tasks, this iterates an *author↔reviewer* pair over a single artifact
until a reviewer score meets ``--threshold`` (exit 0) or the run hits
``--max-iterations`` (exit 1). Per iteration N:

1. compose the author prompt (:mod:`ralph.refine.roles`), run it through the
   reused tool factory, extract the artifact (:mod:`ralph.refine.extract`), and
   save ``{output-dir}/artifact-vN.{type}``;
2. compose the reviewer prompt, run it, save the full reviewer transcript to
   ``{output-dir}/review-vN.md`` (the source of truth for the score/summary on
   ``--resume`` and the author's feedback next iteration), extract the score and
   summary, and print ``Iteration N: score X/10``.

Everything subprocess-shaped is **reused verbatim**: the claude/opencode tool
factory and its combined-stdout tee / timeout=124 / process-group kill
(:mod:`ralph.tools`), the pre-loop ``devcontainer up`` (:mod:`ralph.devcontainer`),
and the SIGTERM-forwarding ``on_spawn`` contract (:class:`_SignalForwarder`
mirrors :class:`ralph.loop._SignalInstaller` but stays self-contained so refine
never couples to ``backlog`` / ``tasks.py``, per PRD FR-7).
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from ralph.devcontainer import start_devcontainer
from ralph.refine import extract as extract_module
from ralph.refine import roles as roles_module
from ralph.refine import summary as summary_module
from ralph.refine.args import RefineArgs
from ralph.refine.extract import ExtractionError
from ralph.tools import Tool, ToolResult
from ralph.tools.claude import ClaudeTool
from ralph.tools.opencode import OpencodeTool

ITER_SLEEP_SEC = 2.0
"""Backoff between retry attempts (mirrors ``ralph.loop.ITER_SLEEP_SEC``)."""

MAX_SCORE = 10
"""Reviewer scores are 1-10; used only for the ``score X/10`` display."""

_POST_MORTEM_TAIL = 4000
"""Chars of transcript tail embedded in a call-failure message (parity with
:data:`ralph.refine.extract._POST_MORTEM_TAIL`)."""


@dataclass
class _Interrupted(BaseException):  # noqa: N818
    """Raised inside the loop when a pending SIGINT/SIGTERM is observed."""

    signum: int = 0


class _CallFailure(Exception):
    """An author/reviewer LLM call failed (bad exit code or unusable output).

    Governed by ``--on-error``. Carries the tee'd transcript so the loop can
    surface a post-mortem (parity with :class:`ralph.refine.extract.ExtractionError`).
    """

    def __init__(self, message: str, *, transcript: str | None = None) -> None:
        self.transcript = transcript
        if transcript:
            tail = transcript[-_POST_MORTEM_TAIL:]
            message = f"{message}\n--- LLM transcript (post-mortem) ---\n{tail}"
        super().__init__(message)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def run(args: RefineArgs, cwd: Path | None = None) -> int:
    """Execute one refine run; return the process exit code.

    Args:
        args: Parsed & validated CLI args.
        cwd: Working directory anchoring a relative ``--output-dir`` and the
            devcontainer workspace folder. Defaults to :func:`Path.cwd`.

    Returns:
        ``0`` when the threshold is met (or already met on ``--resume``),
        ``1`` at max iterations / on an ``--on-error stop`` failure, ``130``
        on interrupt, or the ``devcontainer up`` exit code on setup failure.
    """
    root = cwd if cwd is not None else Path.cwd()
    output_dir = _resolve_output_dir(args, root)

    try:
        author_role, reviewer_role, task, draft = _load_inputs(args)
    except _InputError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        return _dry_run(author_role, task, draft)

    if args.devcontainer:
        rc = start_devcontainer(root)
        if rc != 0:
            return rc

    output_dir.mkdir(parents=True, exist_ok=True)

    resume = _ResumeState()
    if args.resume:
        try:
            resume = _prepare_resume(args, output_dir)
        except ExtractionError as exc:
            print(f"Error: cannot resume, corrupt review file: {exc}", file=sys.stderr)
            return 1
        if resume.terminal_exit is not None:
            return resume.terminal_exit

    tool = build_tool(args, root)
    forwarder = _SignalForwarder()
    forwarder.install()
    try:
        return _run_loop(
            args=args,
            output_dir=output_dir,
            tool=tool,
            forwarder=forwarder,
            author_role=author_role,
            reviewer_role=reviewer_role,
            task=task,
            draft=draft,
            resume=resume,
        )
    except _Interrupted:
        print("Interrupted; stopping.", file=sys.stderr)
        return 130
    finally:
        forwarder.restore()


def build_tool(args: RefineArgs, workspace_folder: Path) -> Tool:
    """Construct the concrete :class:`Tool` for ``args.tool`` (reused factory)."""
    if args.tool == "opencode":
        return OpencodeTool(
            devcontainer=args.devcontainer,
            workspace_folder=workspace_folder if args.devcontainer else None,
        )
    return ClaudeTool(
        model=args.model,
        effort=args.effort,
        devcontainer=args.devcontainer,
        workspace_folder=workspace_folder if args.devcontainer else None,
    )


# --------------------------------------------------------------------------- #
# The iteration loop
# --------------------------------------------------------------------------- #
def _run_loop(
    *,
    args: RefineArgs,
    output_dir: Path,
    tool: Tool,
    forwarder: _SignalForwarder,
    author_role: str,
    reviewer_role: str,
    task: str | None,
    draft: str | None,
    resume: _ResumeState,
) -> int:
    ext = args.artifact_type
    timeout_sec = args.timeout * 60
    history = list(resume.history)
    prev_artifact = resume.prev_artifact
    prev_review = resume.prev_review
    prev_summary = resume.prev_summary
    last_artifact_path: Path | None = (
        output_dir / f"artifact-v{resume.start - 1}.{ext}" if resume.start > 1 else None
    )

    for n in range(resume.start, args.max_iterations + 1):
        forwarder.raise_if_pending()

        author_p = _compose_author(author_role, task, draft, prev_artifact, prev_review)
        _maybe_verbose(args, f"author (iteration {n})", author_p)
        try:
            artifact_text = _author_call(
                tool, author_p, timeout_sec, forwarder, args, f"author (iteration {n})"
            )
        except _CallFailure as exc:
            if _skip_after_failure(args, n, "author", exc):
                continue
            return 1
        artifact_path = output_dir / f"artifact-v{n}.{ext}"
        artifact_path.write_text(artifact_text, encoding="utf-8")
        last_artifact_path = artifact_path

        reviewer_p = roles_module.reviewer_prompt(
            reviewer_role, artifact_text, previous_summary=prev_summary
        )
        _maybe_verbose(args, f"reviewer (iteration {n})", reviewer_p)
        try:
            review_text, score, summ = _reviewer_call(
                tool, reviewer_p, timeout_sec, forwarder, args, f"reviewer (iteration {n})"
            )
        except _CallFailure as exc:
            if _skip_after_failure(args, n, "reviewer", exc):
                continue
            return 1
        (output_dir / f"review-v{n}.md").write_text(review_text, encoding="utf-8")
        print(f"Iteration {n}: score {score}/{MAX_SCORE}")
        history.append(score)
        prev_artifact, prev_review, prev_summary = artifact_text, review_text, summ

        if score >= args.threshold:
            _finalize(output_dir, ext, artifact_path, history, args.threshold, reached=True)
            print(
                f"Threshold {args.threshold} reached at iteration {n} "
                f"(score {score}). Wrote {output_dir / f'final.{ext}'}"
            )
            return 0

    return _finalize_max_iter(args, output_dir, ext, history, last_artifact_path)


def _skip_after_failure(
    args: RefineArgs, iteration: int, role: str, exc: _CallFailure
) -> bool:
    """Decide the post-failure action for a stopped call.

    Returns ``True`` when the loop should ``continue`` to the next iteration
    (``--on-error continue``); ``False`` when it should stop (``stop``, or
    ``retry`` with attempts exhausted). The caller returns exit 1 on ``False``.
    """
    if args.on_error == "continue":
        print(f"Iteration {iteration}: {role} failed; continuing.", file=sys.stderr)
        return True
    print(f"Stopping (--on-error {args.on_error}): {exc}", file=sys.stderr)
    return False


def _compose_author(
    author_role: str,
    task: str | None,
    draft: str | None,
    prev_artifact: str | None,
    prev_review: str | None,
) -> str:
    """Compose the author prompt: continuation when a prior pair exists, else seed."""
    if prev_artifact is not None and prev_review is not None:
        return roles_module.author_prompt(
            author_role, previous_artifact=prev_artifact, previous_review=prev_review
        )
    return roles_module.author_prompt(author_role, task=task, draft=draft)


# --------------------------------------------------------------------------- #
# LLM calls with --on-error / --retry-count
# --------------------------------------------------------------------------- #
def _author_call(
    tool: Tool,
    prompt: str,
    timeout_sec: int,
    forwarder: _SignalForwarder,
    args: RefineArgs,
    label: str,
) -> str:
    """Run the author call (with retry), returning the extracted artifact."""

    def once() -> str:
        result = _invoke(tool, prompt, timeout_sec, forwarder)
        forwarder.raise_if_pending()
        _check_exit(result, "author")
        return extract_module.artifact(result)

    return _retry(once, args=args, forwarder=forwarder, label=label)


def _reviewer_call(
    tool: Tool,
    prompt: str,
    timeout_sec: int,
    forwarder: _SignalForwarder,
    args: RefineArgs,
    label: str,
) -> tuple[str, int, str]:
    """Run the reviewer call (with retry), returning (transcript, score, summary)."""

    def once() -> tuple[str, int, str]:
        result = _invoke(tool, prompt, timeout_sec, forwarder)
        forwarder.raise_if_pending()
        _check_exit(result, "reviewer")
        transcript = _read_text(result.stdout_path)
        return transcript, extract_module.score(result), extract_module.summary(result)

    return _retry(once, args=args, forwarder=forwarder, label=label)


def _retry[T](
    do: Callable[[], T], *, args: RefineArgs, forwarder: _SignalForwarder, label: str
) -> T:
    """Invoke ``do``; re-run on failure under ``--on-error retry`` up to the count.

    A failure is a bad tool exit (:class:`_CallFailure`) *or* unusable output
    (:class:`ExtractionError`) — both are governed uniformly (AC #6). Every
    attempt prints a post-mortem. When retries are exhausted (or the strategy
    is not ``retry``) the failure propagates to the loop for the stop/continue
    decision. ``_Interrupted`` is a ``BaseException`` and passes straight through.
    """
    attempt = 0
    while True:
        try:
            return do()
        except (ExtractionError, _CallFailure) as exc:
            print(f"ERROR: {label} failed:\n{exc}", file=sys.stderr)
            if args.on_error == "retry" and attempt < args.retry_count:
                attempt += 1
                print(
                    f"WARNING: {label} failed; retrying "
                    f"(attempt {attempt} of {args.retry_count})...",
                    file=sys.stderr,
                )
                forwarder.raise_if_pending()
                time.sleep(ITER_SLEEP_SEC)
                continue
            raise _CallFailure(f"{label} failed") from exc


def _invoke(
    tool: Tool, prompt: str, timeout_sec: int, forwarder: _SignalForwarder
) -> ToolResult:
    """Run one tool call, registering the child so a signal can reach it (AC #10)."""
    try:
        return tool.run(prompt, timeout_sec, on_spawn=forwarder.set_active_subprocess)
    finally:
        forwarder.set_active_subprocess(None)


def _check_exit(result: ToolResult, role: str) -> None:
    """Raise :class:`_CallFailure` on a nonzero / timeout (124) tool exit."""
    if result.exit_code != 0:
        raise _CallFailure(
            f"{role} call failed with exit code {result.exit_code}",
            transcript=_read_text(result.stdout_path),
        )


# --------------------------------------------------------------------------- #
# Terminal writes
# --------------------------------------------------------------------------- #
def _finalize(
    output_dir: Path,
    ext: str,
    artifact_path: Path,
    scores: list[int],
    threshold: int,
    *,
    reached: bool,
) -> None:
    """Copy ``artifact_path`` to ``final.{ext}`` and write ``summary.md``."""
    shutil.copyfile(artifact_path, output_dir / f"final.{ext}")
    rendered = summary_module.render_summary(
        summary_module.RefineSummary(
            scores=list(scores), threshold=threshold, reached_threshold=reached
        )
    )
    (output_dir / "summary.md").write_text(rendered, encoding="utf-8")


def _finalize_max_iter(
    args: RefineArgs,
    output_dir: Path,
    ext: str,
    history: list[int],
    last_artifact_path: Path | None,
) -> int:
    """Handle the max-iterations fall-through: warn, copy last artifact, exit 1."""
    if not history or last_artifact_path is None:
        print(
            f"ERROR: reached max iterations ({args.max_iterations}) with no "
            "successful iteration; nothing to finalize.",
            file=sys.stderr,
        )
        return 1
    print(
        f"WARNING: reached max iterations ({args.max_iterations}) without meeting "
        f"threshold {args.threshold} (best score {max(history)}).",
        file=sys.stderr,
    )
    _finalize(output_dir, ext, last_artifact_path, history, args.threshold, reached=False)
    print(f"Wrote {output_dir / f'final.{ext}'}")
    return 1


# --------------------------------------------------------------------------- #
# --resume
# --------------------------------------------------------------------------- #
@dataclass
class _ResumeState:
    """Loop-start context recovered by ``--resume`` (or the fresh-run default)."""

    start: int = 1
    history: list[int] = field(default_factory=list[int])
    prev_artifact: str | None = None
    prev_review: str | None = None
    prev_summary: str | None = None
    terminal_exit: int | None = None
    """Set only for the nothing-to-do paths (outputs already written); the
    caller returns it immediately instead of entering the loop."""


def _prepare_resume(args: RefineArgs, output_dir: Path) -> _ResumeState:
    """Recover loop state from the last complete artifact/review pair (AC #7)."""
    ext = args.artifact_type
    last = _scan_resume(output_dir, ext)
    if last == 0:
        return _ResumeState()  # nothing on disk yet — start fresh at iteration 1

    history = [
        extract_module.score(output_dir / f"review-v{n}.md")
        for n in range(1, last + 1)
    ]
    last_artifact = output_dir / f"artifact-v{last}.{ext}"
    review_path = output_dir / f"review-v{last}.md"
    prev_artifact = _read_text(last_artifact)
    prev_review = _read_text(review_path)
    prev_summary = extract_module.summary(review_path)
    last_score = history[-1]

    if last_score >= args.threshold:
        _finalize(output_dir, ext, last_artifact, history, args.threshold, reached=True)
        print(
            f"Nothing to do: threshold {args.threshold} already met at "
            f"iteration {last} (score {last_score})."
        )
        return _ResumeState(last + 1, history, prev_artifact, prev_review, prev_summary, 0)

    if last >= args.max_iterations:
        _finalize(output_dir, ext, last_artifact, history, args.threshold, reached=False)
        print(
            f"Nothing to do: all {args.max_iterations} iterations complete; "
            f"best score {max(history)} < threshold {args.threshold}.",
            file=sys.stderr,
        )
        return _ResumeState(last + 1, history, prev_artifact, prev_review, prev_summary, 1)

    print(f"Resuming from iteration {last + 1} (last score {last_score}).")
    return _ResumeState(last + 1, history, prev_artifact, prev_review, prev_summary)


def _scan_resume(output_dir: Path, ext: str) -> int:
    """Return the highest N with both ``artifact-vN.{ext}`` and ``review-vN.md``."""
    n = 0
    while (output_dir / f"artifact-v{n + 1}.{ext}").is_file() and (
        output_dir / f"review-v{n + 1}.md"
    ).is_file():
        n += 1
    return n


# --------------------------------------------------------------------------- #
# --dry-run / --verbose / inputs
# --------------------------------------------------------------------------- #
def _dry_run(author_role: str, task: str | None, draft: str | None) -> int:
    """Print the iteration-1 author prompt without any LLM call (AC #8)."""
    prompt = _compose_author(author_role, task, draft, None, None)
    print("=== DRY RUN: iteration 1 author prompt ===")
    print(prompt)
    print(
        "=== (no LLM call made; the reviewer prompt is composed once the author "
        "produces an artifact) ==="
    )
    return 0


def _maybe_verbose(args: RefineArgs, label: str, prompt: str) -> None:
    """Print a composed prompt before its call when ``--verbose`` (AC #9)."""
    if not args.verbose:
        return
    print(f"--- composed prompt: {label} ---")
    print(prompt)
    print("--- end prompt ---")


class _InputError(Exception):
    """A required input file could not be read."""


def _load_inputs(args: RefineArgs) -> tuple[str, str, str | None, str | None]:
    """Read the role files and resolve the seed (``--prompt`` / ``--draft``).

    ``--prompt`` and ``--draft`` are resolved leniently: when the value names a
    readable file its contents are used, otherwise the value is taken as literal
    text. This reconciles the file-path usage (``--prompt examples/.../prompt.md``)
    with inline text, and is why :func:`ralph.refine.args.validate` — which does
    require readable ``--author`` / ``--reviewer`` files — does not constrain them.
    """
    author_role = _read_required(args.author, "author role")
    reviewer_role = _read_required(args.reviewer, "reviewer role")
    task = _resolve_seed(args.prompt) if args.prompt else None
    draft = _resolve_seed(args.draft) if args.draft else None
    return author_role, reviewer_role, task, draft


def _resolve_seed(value: str) -> str:
    """Return the file contents when ``value`` is a readable file, else ``value``."""
    path = Path(value)
    if path.is_file() and os.access(value, os.R_OK):
        return path.read_text(encoding="utf-8")
    return value


def _read_required(path: str, label: str) -> str:
    """Read a required file, raising :class:`_InputError` on failure."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise _InputError(f"Error: failed to read {label} file '{path}': {exc}") from exc


def _read_text(path: Path) -> str:
    """Read a transcript/artifact file, tolerating stray non-UTF-8 bytes."""
    return path.read_text(encoding="utf-8", errors="replace")


def _resolve_output_dir(args: RefineArgs, root: Path) -> Path:
    """Anchor a relative ``--output-dir`` under ``root``; keep absolute as-is."""
    output_dir = Path(args.output_dir)
    return output_dir if output_dir.is_absolute() else root / output_dir


# --------------------------------------------------------------------------- #
# Signal forwarding (reused on_spawn contract; self-contained per FR-7)
# --------------------------------------------------------------------------- #
class _SignalForwarder:
    """Forward SIGINT/SIGTERM to the active tool subprocess's process group.

    Mirrors :class:`ralph.loop._SignalInstaller`, trimmed to refine's needs and
    kept in-package so refine stays decoupled from ``ralph.loop`` (which imports
    ``backlog``/``tasks`` — off-limits per FR-7). The handler sets a pending flag
    the loop polls at :meth:`raise_if_pending` boundaries *and* immediately
    ``killpg``-forwards SIGTERM to the child registered via ``on_spawn`` (AC #10),
    so a signal mid-call reaps the child instead of waiting out its timeout.
    """

    def __init__(self) -> None:
        self._pending: int = 0
        self._prev_int: object = None
        self._prev_term: object = None
        self._installed = False
        self._active_pgid: int | None = None
        # RLock: a signal handler runs synchronously on the main thread and may
        # fire while that thread already holds the lock inside
        # set_active_subprocess — a plain Lock would deadlock re-entering.
        self._lock = threading.RLock()

    def install(self) -> None:
        self._prev_int = signal.signal(signal.SIGINT, self._handler)
        self._prev_term = signal.signal(signal.SIGTERM, self._handler)
        self._installed = True

    def restore(self) -> None:
        if not self._installed:
            return
        with suppress(TypeError, ValueError):
            signal.signal(signal.SIGINT, self._prev_int)  # type: ignore[arg-type]
            signal.signal(signal.SIGTERM, self._prev_term)  # type: ignore[arg-type]
        self._installed = False

    def raise_if_pending(self) -> None:
        """Raise :class:`_Interrupted` if a signal arrived since the last check."""
        if self._pending:
            signum, self._pending = self._pending, 0
            raise _Interrupted(signum=signum)

    def set_active_subprocess(self, proc: subprocess.Popen[bytes] | None) -> None:
        """Register (or clear) the live child so the handler can reach it.

        Wired in as the tool's ``on_spawn`` callback. Registering a child that
        already exited is a no-op. If a signal arrived between spawn and this
        call, the pending flag is already set with no pgid to target, so we
        forward here to reap the just-registered child promptly.
        """
        with self._lock:
            if proc is None:
                self._active_pgid = None
                return
            try:
                self._active_pgid = os.getpgid(proc.pid)
            except ProcessLookupError:
                self._active_pgid = None
            pgid = self._active_pgid
        if pgid is not None and self._pending:
            with suppress(ProcessLookupError, PermissionError, OSError):
                os.killpg(pgid, signal.SIGTERM)

    def _handler(self, signum: int, _frame: object) -> None:
        self._pending = signum
        with self._lock:
            pgid = self._active_pgid
        if pgid is None:
            return
        with suppress(ProcessLookupError, PermissionError, OSError):
            os.killpg(pgid, signal.SIGTERM)
