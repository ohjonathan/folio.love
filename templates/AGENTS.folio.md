# Folio Agent Instructions

Use Folio CLI commands for presentation conversion and analysis tasks.

## Command Mapping

- Single file conversion:
  - `folio convert <file>`
- Batch conversion for a directory:
  - PPTX/PPT (default): `folio batch <dir>`
  - PDF: `folio batch <dir> --pattern "*.pdf"`
- Library status:
  - `folio status`
- Scan configured source roots:
  - `folio scan`
- Re-convert stale decks:
  - `folio refresh`
- Promote a deck's curation level:
  - `folio promote <deck_id> <level>`

## Decision Rules

- If the user asks to convert one file, use `folio convert`.
- If the user asks to process a folder, use `folio batch`.
- If the user explicitly asks for diagram extraction, diagram scanning, or
  deeper analysis, prefer `--passes 2`.
- If the user asks for a fresh run, add `--no-cache`.
- Do not invent `--client`, `--engagement`, `--industry`, `--tags`, or
  `--subtype` unless the user provided them.
- If the user asks to analyze PDFs, use the PDF batch pattern:
  `folio batch <dir> --pattern "*.pdf"`.
- If an API key is missing and the user asked for analysis, explain that Folio
  can still convert the file but LLM-backed analysis will be skipped.
- If Folio is not installed, bootstrap it first instead of guessing commands.

## Environment Checks

Before converting PPTX/PPT files:
- Confirm either LibreOffice or Microsoft PowerPoint is available.
- If running on a managed Mac where LibreOffice may be blocked, use the
  PowerPoint workflow and `pptx_renderer: powerpoint` in `folio.yaml`.
- If neither renderer is available, tell the user to export to PDF and run
  Folio on the PDF instead.

Before requesting LLM-backed analysis:
- Check whether `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`
  is available.
- Anthropic works in the base install.
- OpenAI and Gemini require `folio-love[llm]`.

## Output Expectations

After running a Folio command, report:
- the command used
- the output path
- whether analysis was standard or `--passes 2`
- whether cache was used or bypassed
- any prerequisite or renderer issue that affected the run

## Natural Language Examples

- "Convert this deck with Folio" ->
  `folio convert ./deck.pptx`
- "Scan these diagram PDFs for Folio" ->
  `folio batch ./diagrams --pattern "*.pdf" --passes 2`
- "Re-run this deck from scratch" ->
  `folio convert ./deck.pdf --no-cache`
- "Show me what decks are stale" ->
  `folio status --refresh`

## Safety

- Never print API keys.
- Never overwrite user-edited files unless the user asked for it.
- If the task is ambiguous between one file and one folder, inspect the path
  before choosing `convert` or `batch`.
