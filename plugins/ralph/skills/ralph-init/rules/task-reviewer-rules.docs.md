# Task reviewer rules (Documentation projects)

<!-- Managed by ralph-init: this file is overwritten from the plugin template on every ralph-init upgrade. Do not edit it here — project rules belong in .claude/task-reviewer-rules.md, which ralph-init never touches. A project rule that names a rule ID from this file (for example "replaces R-DOCS-3") overrides that rule. -->

## R-DOCS-1: Obsidian cross-link convention

Apply to any `.md` change that adds or edits `[[…]]` wiki-links or `obsidian://` URIs. The source of truth for the format is the "Obsidian cross-link convention" section in CLAUDE.md (do NOT duplicate it here). Return CHANGES REQUESTED if:

- a wiki-link to a canonical doc uses a short name (`[[doc-2 …]]`) instead of the full basename, or `§X.Y` as an anchor instead of the verbatim section heading;
- inside a markdown table cell the wiki-link's display pipe is NOT escaped (`|` instead of `\|`) — check that the column count is consistent across all rows of the table;
- a cross-vault `obsidian://…file=` uses a short name instead of the full basename, or spaces are not encoded as `%20`.

Outside tables (in prose, lists and headings) a wiki-link's display pipe needs no escaping: `[[target|label]]` is correct there, and the reviewer MUST NOT demand `\|` in that position.

## R-DOCS-2: Terminology discipline

Apply to any `.md` change that adds or edits prose in the project's working language. The source of truth is the "Terminology discipline" section in CLAUDE.md (do NOT duplicate it here). Return CHANGES REQUESTED if the change introduces:

- transliteration of a foreign word into the working language's alphabet where a plain/established term exists;
- an invented term, metaphor, or calque absent from the canon;
- jargon without a definition on first use;
- an unexplained Latin-script technical term in working-language prose (no definition/phrasing);
- a specific commit SHA in prose (references to task IDs are allowed).

Do NOT flag the project's keep-list terms — they are canon.

Task titles and `task-<id>` branch names stay ASCII English where a naming hook enforces it (for example a filename-length or ASCII guard on backlog task files). The reviewer MUST NOT demand that an English task title or branch name be translated into the working language.

## R-DOCS-3: Markdown prose no hard-wrap

Apply to any `.md` change that adds or edits prose. The source of truth is the "Markdown prose
line-wrapping" section in CLAUDE.md (do NOT duplicate it here). The reviewer must NOT require,
request, or itself introduce a hard mid-paragraph line break to satisfy a column limit — that
limit is code-only. Return CHANGES REQUESTED if the diff:

- inserts a hard newline inside a prose paragraph purely to wrap at a column width (a paragraph
  that was one physical line is split into several with no semantic reason);
- re-wraps an already-reflowed document back to a column limit.

Do NOT flag the legitimately multi-line structures (blank-line paragraph separators, list items,
table rows, headings, code fences, blockquote paragraphs) — only hard wraps inside a single
prose paragraph are a defect.

## R-DOCS-4: Markdown document consistency

Apply when the diff touches any `backlog/docs/**/*.md` or `design/**/*.md` file.

1. Read the full HEAD version of each modified `.md` file, not just the diff.
2. Verify the new or changed content does not contradict what the document already states: assumptions and base statements, fixed criteria or pre-decided values, impossibility statements, and quantitative claims (counts, sums) that must stay consistent across sections.
3. If the change revisits a previously closed question, the reframing must be explicit — a visible note that the earlier decision is reopened and why — never a silent re-fork.
4. Cross-section terminology drift is a defect: the same concept uses the same term throughout the document.

Any contradiction or drift → CHANGES REQUESTED naming the conflicting section and line.

## R-DOCS-5: Document family consistency

A document family is a canonical document plus its derived artifacts, identified by a shared document id in the path or filename — e.g. `backlog/docs/doc-N*.md`, `design/doc-N-*.md`, `presentations/doc-N/**`, and `drawio/**` / `puml/**` files naming `doc-N`. A project may define its families more precisely in its own rules file.

When the diff touches two or more artifacts of one family, verify across them:

- **identifier alignment** — names and numbers of sections, patterns and components match;
- **dimension alignment** — fixed value sets use the same vocabulary;
- **quantitative claims** — counts and sums match.

A change to one artifact without the corresponding update to the others is a defect: return CHANGES REQUESTED and name each missing update.

## R-DOCS-6: A fit criterion is closed by a crop with verified fonts plus a slack number

Apply to any acceptance criterion claiming that text stays inside a frame, card or slide edge in a built deck.

- **Crop.** The criterion MUST NOT be marked done unless a raster crop of that area, taken from the BUILT artifact, is attached to the task notes (`soffice --headless --convert-to pdf`, then `pdftoppm -png -r 220 -f <N> -l <N>`, cropped to the area). No crop → CHANGES REQUESTED, however convincing the diff looks.
- **Fonts.** A crop is only as honest as the fonts under it. For every font family the deck declares, run `fc-match -f '%{family[0]} | %{file}\n'` for regular and for bold: the family MUST be the one declared (or a documented metric-compatible twin), and regular and bold MUST come from different files. Checking the family alone misses a variable font without a static bold (bold drawn at regular weight, text looks narrower); checking distinct files alone misses substitution (another family served, text looks wider). Both errors occur in practice.
- **Slack number.** The crop is necessary, not sufficient. Read it together with a slack number: the volume of text per box against the box's line capacity, not the length of the longest line. A block rendering N lines into room for exactly N lines overflows on any metric disagreement, including the presenting machine's fonts. Ask for the slack number whenever the crop shows a block at its line capacity.
- **Declared heights.** A height declared in the source is a layout cache that the presentation software re-autofits; a number in the diff proves nothing.

Why all three: fit criteria have been closed and approved on renders made with the wrong fonts, and text was later cut that never needed cutting.

## R-DOCS-7: A measurement in a comment belongs to the text it measured

When a change edits text whose size, fit or wording a nearby comment measures or justifies, that comment MUST be updated in the same change. Read the comments around every edited block and return CHANGES REQUESTED when one still describes the old text.

- **Check by grep.** Take the numbers and distinctive phrases from comments in the changed region and search the repository after the edit; every hit that still describes superseded text is a defect. Hits in completed tasks' notes are history — leave them.
- **Name the edition.** Every measurement written into a comment MUST name the edition it belongs to: the task that produced it or the wording it measured.
- **Scope.** This covers any comment whose truth depends on the text beside it: a rationale for a cut, a count of occurrences, a claim that a block is the tightest.

## R-DOCS-8: Publication is never implicit

Publishing a document outside the repository — to a wiki, a shared drive, a chat channel or any external service — is a separate action that a task must ask for in its own words. A task that writes or edits a document does not authorize publishing it.

- The reviewer MUST NOT treat an unpublished document as unfinished work, nor ask for a publication the task did not request.
- Return CHANGES REQUESTED when the diff performs or automates an external publication outside the task's stated scope.
- When the task does ask for publication, the publication is in scope and this rule does not apply.

A project may be stricter (for example, requiring a named approver); it may not be looser.

## R-DOCS-9: The review report is written in the project's working language

The "Terminology discipline" section in CLAUDE.md requires the project's documents and an agent's own answers to use the working language. This rule applies that to the one output the reviewer itself writes: the review report.

- Rule IDs, file paths, command names, identifiers and quoted code or output stay verbatim.
- Headings stay English where a naming hook enforces it (see R-DOCS-2).
- A report written in another language is the reviewer's own defect to fix before returning it, never a finding against the author.
