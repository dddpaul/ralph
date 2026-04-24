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
