---
id: TASK-235
title: >-
  Stop devcontainer runs from clobbering the host .venv with a container
  interpreter
status: In Progress
assignee: []
created_date: '2026-09-04 13:46'
updated_date: '2026-09-04 14:00'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Root cause (verified): the repo workspace is bind-mounted into the devcontainer and .venv/ is not excluded from that mount. When Ralph runs 'uv sync' inside the container, uv writes .venv/ with a container-specific interpreter path onto the host via the bind mount. Proof — after a devcontainer run the host .venv/pyvenv.cfg reads 'home = /home/node/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin' and .venv/bin/python3 -> /home/node/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin/python3.14, which does not exist on the macOS host. Result: .venv/bin/python3 is a broken symlink, so 'uv run ...' and the ralph-run preflight fail with exit 2 ('Broken symlink at .venv/bin/python3'). Observed ~8 times in one session; current manual workaround is 'rm -rf .venv && uv sync' on the host before each launch.

Recommended fix (precedent in the same file): add a container volume overlay for .venv, mirroring the existing .claude volume-overlay in .devcontainer/devcontainer.json (the 'source=claude-code-project-config-${devcontainerId},target=/workspace/.claude,type=volume' mount). A 'target=/workspace/.venv,type=volume' overlay keeps the container's Linux .venv off the host bind mount so the host macOS .venv is never clobbered. Alternatives to weigh if the overlay is problematic: set UV_PROJECT_ENVIRONMENT to a container-only path (e.g. /tmp/venv) so the container never writes to ./.venv; or a host-side preflight self-heal that detects a foreign/broken .venv interpreter and rebuilds (papers over rather than fixes).

Parity note: .devcontainer/ is mirrored into plugins/ralph/skills/ralph-init/templates/devcontainer/, so a devcontainer.json change must be mirrored there (R11) and ralph-init SKILL.md updated in both Init and Upgrade Mode if the template changes. Verify whether the templates carry this mount block before deciding parity scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After a full devcontainer Ralph run, the host .venv/bin/python3 remains a valid interpreter and 'uv run python -V' plus the ralph-run preflight succeed with no manual 'rm -rf .venv && uv sync'
- [ ] #2 The container's virtualenv no longer lands on the host bind mount — verified by host .venv/pyvenv.cfg still pointing at a host (darwin/arm64) interpreter home after a container run, not a /home/node/.local/share/uv/...linux... path
- [x] #3 The mechanism is a .venv container volume overlay in .devcontainer/devcontainer.json (or a documented equivalent that keeps the container venv off the host), consistent with the existing .claude overlay pattern
- [x] #4 If .devcontainer/ is mirrored in ralph-init templates, the same change is applied to plugins/ralph/skills/ralph-init/templates/devcontainer/ and ralph-init SKILL.md is updated in both Init and Upgrade Mode; if not mirrored, that is noted explicitly
- [x] #5 uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Add a .venv container-volume overlay to .devcontainer/devcontainer.json — 'source=claude-code-project-venv-${devcontainerId},target=/workspace/.venv,type=volume' — mirroring the existing .claude overlay, plus 'sudo chown node:node /workspace/.venv' in postCreateCommand (Docker creates a fresh named-volume mountpoint root-owned, same reason the .claude overlay already chowns). (2) Mirror byte-for-byte into plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json — R11 parity is enforced by the 'exact' row in tests/unit/template-parity.bats. (3) Document in ralph-init SKILL.md Init 3.6 and Upgrade Mode (rebuild required for the new mount to take effect) plus README. (4) Add a bats regression test asserting the overlay mount + chown in BOTH live and template devcontainer.json. (5) Baselines captured before edits: uv run pytest = 468 passed, uv run ruff check . = clean, LC_ALL=C bats tests/unit = 107/107 ok.

AC #1 and AC #2 left UNCHECKED — deliberately, not overlooked. Both are host-side observations ('after a full devcontainer Ralph run, the HOST .venv/pyvenv.cfg still points at a darwin/arm64 interpreter home'), and this task executed INSIDE the devcontainer, where none of that is reachable: no docker CLI, no /var/run/docker.sock, no devcontainer CLI, no view of the macOS filesystem. I cannot rebuild the container from within it, so I cannot make the observation those two ACs ask for. The implementation that produces them is shipped and the mechanism is proven; the observation itself lands on the user's next rebuild.

What WAS proven empirically, in this container:
1. The bug, reproduced live. Before: host-written .venv/pyvenv.cfg read 'home = /opt/homebrew/opt/python@3.14/bin'. A single 'uv run python -V' in the container rewrote it to 'home = /home/node/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin' with .venv/bin/python -> that path. That write reached the host through the bind mount — exactly the reported failure.
2. The fix mechanism, proven working in this exact environment. /proc/self/mountinfo shows '/workspace virtiofs' (the Docker Desktop macOS host bind) with '/workspace/.claude ext4' nested inside it — the existing .claude volume overlay. A named volume mounted over a subpath of a virtiofs bind mount demonstrably shadows it here. /workspace/.venv has no such line today, which is precisely why container writes to it reach the host.
3. uv self-heals a stale volume, so nothing has to reset it after an image rebuild: given a venv whose base interpreter is gone, uv prints 'Ignoring existing virtual environment linked to non-existent Python interpreter' -> 'Removed virtual environment' -> recreates, exit 0. Verified by mutation on a scratch project.

Host-side confirmation, once the user rebuilds ('Dev Containers: Rebuild Container' — a restart will NOT pick up mounts):
  # inside the rebuilt container — /workspace/.venv must now be its own fs
  awk '$5 == "/workspace" || $5 ~ /^\/workspace\// { print $5, $(NF-2) }' /proc/self/mountinfo
  # expect: /workspace virtiofs | /workspace/.claude ext4 | /workspace/.venv ext4
  # on the macOS host, during/after that container run:
  grep '^home' .venv/pyvenv.cfg     # must stay /opt/homebrew/... , never /home/node/...
  uv run python -V                  # AC #1
One-time host repair is still required before the first post-fix run: the host .venv is already clobbered (this run clobbered it again), so run 'rm -rf .venv && uv sync' on the host ONCE. That is documented in README.md and in the ralph-init Upgrade note, not left as folklore.
<!-- SECTION:NOTES:END -->
