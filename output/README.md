# Portable editions

Use [Read anywhere](../READ-ANYWHERE.md) to choose a format. These files are exports of the current canonical notebooks, not additional claims of curriculum completion.

The full PDF has 219 pages; the LinkedIn companion has nine. EPUB contains 33 notebooks plus static experiment explanations. GitHub mirrors are in `../github/`.

Rebuilding: `python export_editions.py` uses Python with reportlab, pypdf and markdown-it-py; this builder currently loads Arial and Consolas from Windows Fonts. Reading the exports does not require Python or Windows. Run `python finalize_library.py` afterward to refresh the HTML library and ZIP. EPUB format validation was performed with EPUBCheck 5.4.0; see edition-report.json for scoped checks.

Re-export after changing canonical Markdown so editions do not drift. PDF code wraps for layout; use the original lab source files for execution.
