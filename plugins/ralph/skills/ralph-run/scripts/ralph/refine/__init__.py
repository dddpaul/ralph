"""ralph-refine sub-package: adversarial author-reviewer refinement loop.

Ralph's non-code sibling loop. Ralph loops a *coder* over backlog tasks;
ralph-refine loops an *author-reviewer* over a digital artifact (md / draw.io /
PlantUML) until a reviewer score meets a threshold. This package adds only the
refine-specific ``args`` / ``roles`` / ``extract`` / ``loop`` / ``summary`` /
``cli`` modules; the tool, devcontainer, and signal layer is reused verbatim
from the shared ``ralph`` package (see backlog ``doc-4`` for the cross-task
invariants).

The re-exports below smoke-test that the sub-package can reach the reused
shared modules from under the pinned ``ralph`` root (US-001 AC #1) and give
refine modules a single import site for the reused layer.
"""

from __future__ import annotations

from ralph import devcontainer, signals, tools

__all__ = ["devcontainer", "signals", "tools"]
