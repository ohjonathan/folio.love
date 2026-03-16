#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Bootstrap Folio on macOS.

Usage:
  scripts/bootstrap_macos.sh [--renderer auto|libreoffice|powerpoint|pdf-only] [--llm]

Options:
  --renderer  Install path for PPTX/PPT support.
              auto         Install LibreOffice and let Folio auto-select it.
              libreoffice  Install LibreOffice explicitly.
              powerpoint   Skip LibreOffice; use Microsoft PowerPoint workflow.
              pdf-only     Skip PPTX/PPT renderer install; PDF conversion only.
              Default: auto
  --llm       Install optional OpenAI/Gemini SDKs via folio-love[llm].
  --help      Show this help text.

Notes:
  - Requires Homebrew and Python 3.
  - Installs the CLI into ~/.local/share/folio-love/venv
  - Symlinks the `folio` command into ~/.local/bin/folio
EOF
}

renderer="auto"
install_llm="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --renderer)
      renderer="${2:-}"
      shift 2
      ;;
    --llm)
      install_llm="1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$renderer" in
  auto|libreoffice|powerpoint|pdf-only)
    ;;
  *)
    echo "Invalid renderer: $renderer" >&2
    usage >&2
    exit 1
    ;;
esac

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This bootstrap script is macOS-only." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found." >&2
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Homebrew is required for this bootstrap path and was not found.

Install Homebrew first, then rerun this script:
  https://brew.sh/
EOF
  exit 1
fi

echo "Installing system prerequisites..."
brew list poppler >/dev/null 2>&1 || brew install poppler

case "$renderer" in
  auto|libreoffice)
    brew list --cask libreoffice >/dev/null 2>&1 || brew install --cask libreoffice
    ;;
  powerpoint|pdf-only)
    ;;
esac

venv_dir="${FOLIO_VENV_DIR:-$HOME/.local/share/folio-love/venv}"
bin_dir="${FOLIO_BIN_DIR:-$HOME/.local/bin}"

echo "Creating/updating virtual environment at $venv_dir..."
python3 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --upgrade pip

package_spec="folio-love"
if [[ "$install_llm" == "1" ]]; then
  package_spec="folio-love[llm]"
fi

echo "Installing $package_spec..."
"$venv_dir/bin/python" -m pip install --upgrade "$package_spec"

mkdir -p "$bin_dir"
ln -sf "$venv_dir/bin/folio" "$bin_dir/folio"

path_note=""
case ":$PATH:" in
  *":$bin_dir:"*)
    ;;
  *)
    path_note="Add this to your shell profile if needed: export PATH=\"$bin_dir:\$PATH\""
    ;;
esac

cat <<EOF

Folio bootstrap complete.

Installed:
  - Python environment: $venv_dir
  - CLI symlink:        $bin_dir/folio

Next checks:
  - folio --help
  - folio convert your_deck.pdf

If you want PPTX/PPT support:
EOF

case "$renderer" in
  auto|libreoffice)
    cat <<'EOF'
  - LibreOffice was installed. Folio can use the default renderer path.
EOF
    ;;
  powerpoint)
    cat <<'EOF'
  - Microsoft PowerPoint must already be installed.
  - In the folder where you run Folio, create folio.yaml with:

    conversion:
      pptx_renderer: powerpoint

  - Then run: folio convert your_deck.pptx
EOF
    ;;
  pdf-only)
    cat <<'EOF'
  - This setup is PDF-only. Export PPTX/PPT to PDF manually before conversion.
EOF
    ;;
esac

if [[ "$install_llm" == "1" ]]; then
  cat <<'EOF'

LLM setup:
  - Anthropic works with ANTHROPIC_API_KEY
  - OpenAI works with OPENAI_API_KEY
  - Gemini works with GEMINI_API_KEY
EOF
fi

if [[ -n "$path_note" ]]; then
  echo
  echo "$path_note"
fi
