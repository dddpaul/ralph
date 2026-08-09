# Task reviewer rules (Documentation projects)

## R-DOCS-1: Obsidian cross-link convention

Apply to any `.md` change that adds or edits `[[…]]` wiki-links or `obsidian://` URIs. The source of truth for the format is the "Obsidian cross-link convention" section in CLAUDE.md (do NOT duplicate it here). Return CHANGES REQUESTED if:

- a wiki-link to a canonical doc uses a short name (`[[doc-2 …]]`) instead of the full basename, or `§X.Y` as an anchor instead of the verbatim section heading;
- inside a markdown table cell the wiki-link's display pipe is NOT escaped (`|` instead of `\|`) — check that the column count is consistent across all rows of the table;
- a cross-vault `obsidian://…file=` uses a short name instead of the full basename, or spaces are not encoded as `%20`.

## R-DOCS-2: Terminology discipline

Apply to any `.md` change that adds or edits prose in the project's working language. The source of truth is the "Terminology discipline" section in CLAUDE.md (do NOT duplicate it here). Return CHANGES REQUESTED if the change introduces:

- transliteration of a foreign word into the working language's alphabet where a plain/established term exists;
- an invented term, metaphor, or calque absent from the canon;
- jargon without a definition on first use;
- an unexplained Latin-script technical term in working-language prose (no definition/phrasing);
- a specific commit SHA in prose (references to task IDs are allowed).

Do NOT flag the project's keep-list terms — they are canon.
