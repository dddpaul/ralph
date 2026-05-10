---
id: TASK-115
title: >-
  Soften init-firewall on unresolvable hostnames; remove dead
  statsig.anthropic.com
status: Done
assignee: []
created_date: '2026-05-10 18:35'
updated_date: '2026-05-10 18:37'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
devcontainer postStartCommand fails when any allow-list hostname does not resolve. Currently statsig.anthropic.com returns NXDOMAIN (Anthropic appears to have retired it), and init-firewall.sh treats this as fatal (exit 1), blocking the entire container start.

Two changes:

1. Soften the resolution-failure path in init-firewall.sh: log WARN and continue instead of exit 1. Future hostname retirements should not brick the devcontainer.
2. Remove statsig.anthropic.com from the allowed-domains list (known dead).

R11 (template parity) requires updating both copies identically:
- ./.devcontainer/init-firewall.sh (live)
- ./skills/ralph-init/templates/devcontainer/init-firewall.sh (template)

## Specific edits

Replace the existing block:

```bash
if [ -z "$ips" ]; then
    echo "ERROR: Failed to resolve $domain"
    exit 1
fi
```

with:

```bash
if [ -z "$ips" ]; then
    echo "WARN: Failed to resolve $domain — skipping (allow list unaffected)"
    continue
fi
```

And remove the line:

```
    "statsig.anthropic.com" \
```

from the for-loop domain list (currently around line 81 of the live file).

## Smoke test

After edits, run the script with a known-NXDOMAIN domain temporarily prepended to the list (or just the existing list) and verify:
- exit code 0 (not 1)
- WARN line appears for any unresolvable hostname
- Resolution proceeds for the rest of the list
- iptables rules still applied after the loop
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 init-firewall.sh handles unresolvable hostnames by logging "WARN: Failed to resolve <domain>" and continuing the loop instead of exit 1
- [x] #2 statsig.anthropic.com is removed from the for-loop allowed-domains list in init-firewall.sh
- [x] #3 .devcontainer/init-firewall.sh and skills/ralph-init/templates/devcontainer/init-firewall.sh are byte-identical (R11 parity verifiable via diff exit 0)
- [x] #4 bash -n passes on both init-firewall.sh copies
- [x] #5 No surviving "exit 1" on the per-domain resolution path; the only exit-on-error in the for-loop is for the IP-format validation (which remains)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Edit .devcontainer/init-firewall.sh to (a) replace exit 1 with continue + WARN on resolution failure, (b) remove statsig.anthropic.com from the allowed-domains list. Mirror to skills/ralph-init/templates/devcontainer/init-firewall.sh via cp. Verify byte-identical via diff and bash -n on both.

Commit: `269c1fc` - task-115: Soften init-firewall on unresolvable hostnames; remove dead statsig.anthropic.com

All 5 ACs verified. Resolution-failure path now logs WARN and continues; statsig.anthropic.com removed from allow list. R11 parity confirmed. Reviewer APPROVED.
<!-- SECTION:NOTES:END -->
