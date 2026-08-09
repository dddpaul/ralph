# Task reviewer rules (Documentation projects)

## R-DOCS-1: Obsidian cross-link convention

Apply to any `.md` change that adds or edits `[[…]]` wiki-links or `obsidian://` URIs. The source of truth for the format is the "Obsidian cross-link convention" section in CLAUDE.md (do NOT duplicate it here). Return CHANGES REQUESTED if:

- a wiki-link to a canonical doc uses a short name (`[[doc-2 …]]`) instead of the full basename, or `§X.Y` as an anchor instead of the verbatim section heading;
- inside a markdown table cell the wiki-link's display pipe is NOT escaped (`|` instead of `\|`) — check that the column count is consistent across all rows of the table;
- a cross-vault `obsidian://…file=` uses a short name instead of the full basename, or spaces are not encoded as `%20`.
