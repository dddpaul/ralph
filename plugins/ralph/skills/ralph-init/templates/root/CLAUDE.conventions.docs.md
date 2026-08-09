This is a documentation project using Obsidian for markdown editing and the /pptx skill for presentations.

**Workflow**

- Write and organize content in markdown files
- Use Obsidian wikilinks (`[[page]]`) for internal cross-references
- Generate presentations with the /pptx skill and python-pptx
- Convert presentations to PDF with LibreOffice when needed: `libreoffice --headless --convert-to pdf file.pptx`

**Markdown Standards**

- One H1 heading per file (the document title)
- Use ATX-style headings (`#`, `##`, `###`)
- Wrap lines at 120 characters in source files
- Use fenced code blocks with language identifiers
- Prefer tables over nested lists for structured data

**File Organization**

- Place images and attachments in an `assets/` folder
- Name files with lowercase-kebab-case: `architecture-overview.md`
- Group related documents in subdirectories by topic

**Presentation Generation**

- Use python-pptx for programmatic slide generation
- Run Python scripts with `uv run script.py`
- Install script dependencies with PEP 723 inline metadata
- Extract text from existing PPTX: `uv run python -c "from pptx import Presentation; ..."`
- Convert PPTX to images: `pdftoppm -png file.pdf output-prefix`

### Code Style

- Python scripts: Follow PEP 8, use type hints
- Markdown: Consistent heading hierarchy, no skipped levels
- File naming: lowercase-kebab-case for all documents

### Obsidian cross-link convention

The documents in this project live in an Obsidian vault. Links between them must resolve — otherwise clicking a link makes Obsidian create empty stub notes.

- **Link to a canonical document:** `[[<full-basename-without-.md>#<verbatim-heading>|<short display>]]`. The filename is the FULL basename (`doc-2 - Architecture-layers-and-system-classes`), not `doc-2`. `§X.Y` is NOT an anchor; the anchor is the exact section-heading text (`#1.3. Cross-product services`).
- **Documents without item-headings** (e.g. the TERMS glossary) — link to the whole file: `[[TERMS|TERMS #14]]`. Jumping to a specific item is impossible if it has no heading.
- **Inside markdown table cells** the display-alias pipe MUST be escaped: `[[…\|display]]`. An unescaped `|` is read by the table as a column separator and breaks the markup. In prose (outside tables) no escaping is needed.
- **Link into an adjacent vault (cross-vault):** `obsidian://open?vault=<vault>&file=<full-basename>`; encode spaces in the filename as `%20`.

### Terminology discipline

The documents in this project (and your own answers) are written in the project's working language — plainly and consistently. Headings are in English (naming-guard); everything else is prose in the working language. Apply this proactively, without waiting for review comments; proofread YOUR OWN wording before submitting.

- **Do not transliterate foreign technical terms** into the working language's alphabet where a plain or established term exists. Take the replacement from the canon/domain — do not invent one.
- **Do not invent terms, metaphors, or calques.** If the canon already named a thing, use that name.
- **Introduce jargon with a definition on first use**, then use it consistently. Jargon thrown straight into use without a definition is a defect.
- **Keep a project keep-list** of established domain/canonical terms that must NOT be rewritten; extend it per project.
- **Follow the vocabulary of the referenced project/domain** — do not "fix" an established term to your taste.
- **Remove commit SHAs from prose**; references to task IDs (e.g. TASK-N) are fine (provenance).
