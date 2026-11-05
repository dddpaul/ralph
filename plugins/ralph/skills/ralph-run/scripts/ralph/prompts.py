"""Iteration prompt builder — assembles ``MODE: prefix + body`` for the tool.

Mirrors ``ralph.sh:773-794`` exactly:

* MODE prefix is always present (``MODE: autonomous (Ralph loop iteration
  <i> of <max>)``) and is separated from the body by a blank line.
* Body precedence: ``whitelist_task_id`` > ``prompt_file_body`` > default.
* ``--prompt-file`` REPLACES the inner body; the MODE prefix is still
  prepended (AC #6).
* Outside whitelist mode the agent picks its own task, so the body names the
  tasks an earlier iteration of this run left in ``To Do`` (TASK-324). The
  line is absent until a task is skipped, keeping the bash-parity prompt.
"""

from __future__ import annotations

from collections.abc import Sequence

MODE_PREFIX_TEMPLATE = "MODE: autonomous (Ralph loop iteration {i} of {max_i})"


def _whitelist_body(task_id: str) -> str:
    numeric = task_id.removeprefix("TASK-")
    return (
        f"Execute TASK-{numeric} using the full Task Lifecycle from CLAUDE.md. "
        f"Do NOT pick any other task. If TASK-{numeric} is already Done, "
        "reply with <promise>COMPLETE</promise>.\n"
        "Your response MUST end with the ## Task Summary block. "
        "This is not optional."
    )


_DEFAULT_BODY = (
    "Pick the next To Do task and execute the full Task Lifecycle "
    "from CLAUDE.md.\n"
    "Your response MUST end with the ## Task Summary block. "
    "This is not optional."
)


def _excluded_line(task_ids: Sequence[str]) -> str:
    return (
        "Do NOT pick these tasks — an earlier iteration of this run left them "
        f"in To Do: {', '.join(task_ids)}."
    )


def build_prompt(
    iteration: int,
    max_iterations: int,
    *,
    whitelist_task_id: str | None = None,
    prompt_file_body: str | None = None,
    excluded_task_ids: Sequence[str] = (),
) -> str:
    """Compose the iteration prompt with bash-parity formatting.

    Args:
        iteration: 1-based iteration counter (matches the bash ``$i``).
        max_iterations: Total iteration budget for this run.
        whitelist_task_id: When set, the body targets this specific task
            and takes precedence over ``prompt_file_body``.
        prompt_file_body: Already-loaded contents of ``--prompt-file``.
            Used only when ``whitelist_task_id`` is None.
        excluded_task_ids: Tasks the agent must not pick; appended to the
            default or prompt-file body. Ignored in whitelist mode, whose
            body already names the one task to run.
    """
    prefix = MODE_PREFIX_TEMPLATE.format(i=iteration, max_i=max_iterations)
    if whitelist_task_id:
        body = _whitelist_body(whitelist_task_id)
    elif prompt_file_body is not None:
        body = prompt_file_body
    else:
        body = _DEFAULT_BODY
    if excluded_task_ids and not whitelist_task_id:
        body = f"{body.rstrip()}\n{_excluded_line(excluded_task_ids)}"
    return f"{prefix}\n\n{body}"
