# Agentic Setup

This guide covers onboarding Folio in agentic CLI environments — Cursor,
Claude Code, Antigravity, or any tool that reads project-level instruction
files.

The important constraint is that `pip install folio-love` only installs Python
dependencies. It does not provision macOS system tools like Poppler or
LibreOffice, and it does not configure API keys. Agent prompts should be
explicit about system prerequisites and validation.

---

## Quick Install (No Repo Required)

If you installed Folio via PyPI and don't have the repo checked out, run these
commands directly:

```bash
brew install poppler
brew install --cask libreoffice   # skip if on a managed Mac
pip install folio-love
folio --help
```

For managed Macs where LibreOffice is blocked, see the
[Managed Mac workflow](managed_mac_workflow.md) and set
`pptx_renderer: powerpoint` in `folio.yaml`.

If you use an enterprise gateway, keep the gateway URL in an environment
variable such as `ANTHROPIC_BASE_URL`, `OPENAI_BASE_URL`, or
`GEMINI_BASE_URL`, then reference that variable from the selected Folio LLM
profile with `base_url_env`.

---

## One-Command Bootstrap (macOS, Repo Required)

The bootstrap script automates system dependency installation, venv creation,
and CLI symlinking. **It requires a checkout of the folio.love repo** — it
references `scripts/bootstrap_macos.sh` relative to the repo root.

```bash
# From the repo root (folio.love/)
scripts/bootstrap_macos.sh
```

With optional OpenAI/Gemini SDKs:

```bash
scripts/bootstrap_macos.sh --llm
```

Managed Mac / PowerPoint workflow:

```bash
scripts/bootstrap_macos.sh --renderer powerpoint
```

PDF-only workflow:

```bash
scripts/bootstrap_macos.sh --renderer pdf-only
```

---

## Enterprise Gateway Profiles

Folio supports profile-level gateway routing through `base_url_env` in
`folio.yaml`:

```yaml
llm:
  profiles:
    gateway_openai:
      provider: openai
      model: gpt-4o
      api_key_env: OPENAI_API_KEY
      base_url_env: OPENAI_BASE_URL
```

Use `--llm-profile` to select the gateway-backed profile explicitly:

```bash
folio convert sample.pdf --llm-profile gateway_openai
```

At the start of each conversion run, Folio runs a warning-only model preflight
once per selected profile. The probe is bounded, uses the same runtime
guardrails as normal model calls, and only emits warnings. If a model is
blocked or unavailable, you will see a warning before the expensive analysis
stages begin, but the run will continue.

Related runtime notes for agents and operators:

- managed Macs can keep using `pptx_renderer: powerpoint`
- scanned or image-only PDFs stay flagged for review, but no longer get the
  old blanket confidence penalty just because text validation is unavailable
- oversized PDF pages automatically reduce DPI before triggering Pillow size
  limits

---

## Cursor Prompts

### Standard macOS

Paste this into Cursor:

```text
Set up Folio on this Mac for local use.

Requirements:
- Use the repo's bootstrap script if present: scripts/bootstrap_macos.sh
- If the script is missing, follow the Prerequisites and Install sections
  in README.md to install system dependencies and Folio manually.
- Do not ask me to copy files manually if you can do the command yourself.
- Do not handle or print any API keys.
- At the end, tell me exactly what you installed and whether ~/.local/bin
  needs to be added to PATH.
```

### Managed Mac / PowerPoint

Paste this into Cursor:

```text
Set up Folio on this Mac, but assume LibreOffice may be blocked by device
management.

Requirements:
- Use the repo's bootstrap script if present with the PowerPoint path:
  scripts/bootstrap_macos.sh --renderer powerpoint
- If the script is missing, follow the Prerequisites and Install sections
  in README.md. Skip LibreOffice and set pptx_renderer: powerpoint in
  folio.yaml instead.
- Do not handle or print any API keys.
- At the end, tell me exactly what you installed and remind me that
  Microsoft PowerPoint must already be installed.
```

---

## Claude Code

Claude Code uses `CLAUDE.md` files and project-level memory for persistent
instructions. To teach Claude Code about Folio commands:

1. Copy the contents of
   [`templates/AGENTS.folio.md`](../../templates/AGENTS.folio.md) into your
   project's `CLAUDE.md` (or append it if one already exists).
2. Alternatively, paste the same content into Claude Code's project-level
   memory via the `/memory` command.

That gives Claude Code the full command mapping, decision rules, and
environment checks so it can handle requests like "convert this deck" or
"scan the PDFs folder" without ad hoc prompting.

---

## Other Agentic CLIs

Each tool has its own convention for project-level instructions. Copy the
contents of [`templates/AGENTS.folio.md`](../../templates/AGENTS.folio.md) into
whatever filename your tool reads — for example, `AGENTS.md` for tools that
follow that convention, or a tool-specific config file. The template is a
starting point; adapt it to fit your tool's format.

---

## Persistent Agent Rules (Cursor)

If you want Cursor to reliably understand Folio commands from natural language,
use a Project Rule instead of depending on ad hoc chat context.

Templates in this repo:

- **AGENTS.folio.md** — generic agent instruction file:
  [`templates/AGENTS.folio.md`](../../templates/AGENTS.folio.md)
- **Cursor Project Rule** — `.mdc` format for `.cursor/rules/`:
  [`templates/cursor/folio-workflow.mdc`](../../templates/cursor/folio-workflow.mdc)

Recommended setup:

1. For Cursor, copy the Project Rule template into `.cursor/rules/`.
2. If your project already has an `AGENTS.md`, append the Folio section from
   the template rather than overwriting it. If it doesn't, copy the template
   as `AGENTS.md`.
3. Keep the rule focused on command routing, prerequisites, and output
   expectations.

---

## Success Criteria

The setup is complete when:

```bash
folio --help
```

works, and one of these succeeds:

```bash
folio convert sample.pdf
folio convert sample.pptx
```

If the user wants LLM-backed analysis, add the provider key in their shell
environment and then run:

```bash
folio convert sample.pptx --passes 2
```
