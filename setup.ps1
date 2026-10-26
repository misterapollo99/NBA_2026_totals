# One-time setup for the Lily.ai take-home. Run from the project folder:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Stop"

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }

Step "Checking prerequisites"
foreach ($tool in @("python", "git")) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) { Ok "$tool found" }
    else { Warn "$tool not found. Install it, then rerun this script."; exit 1 }
}
python --version
if (Get-Command node -ErrorAction SilentlyContinue) { Ok "node $(node --version)" }
else { Warn "node not found. Pyright will be installed with pip instead of npm." }
if (Get-Command claude -ErrorAction SilentlyContinue) { Ok "claude $(claude --version)" }
else { Warn "Claude Code not found. Install it from https://code.claude.com/docs/en/setup" }

Step "Creating virtual environment (.venv)"
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r requirements.txt --quiet
Ok "pandas $(& $py -c 'import pandas; print(pandas.__version__)')"
Ok "ruff $(& .\.venv\Scripts\ruff.exe --version)"

Step "Pinning exact versions to requirements.lock.txt"
& $py -m pip freeze | Out-File -Encoding utf8 requirements.lock.txt
Ok "requirements.lock.txt written"

Step "Installing pyright (language server for the pyright-lsp plugin)"
if (Get-Command pyright-langserver -ErrorAction SilentlyContinue) { Ok "pyright already on PATH" }
elseif (Get-Command npm -ErrorAction SilentlyContinue) { npm install -g pyright | Out-Null; Ok "pyright installed with npm" }
else { & $py -m pip install pyright --quiet; Ok "pyright installed into .venv (activate the venv before starting claude)" }

Step "Smoke-testing the acceptance checker"
& $py .claude\skills\check-takehome\scripts\check_outputs.py
Write-Host "    (FAILs above are expected: update_catalog.py does not exist yet.)"

Step "Initializing git"
if (-not (Test-Path ".git")) {
    git init -b main | Out-Null
    git add .
    git commit -m "Project scaffold: inputs, Claude Code config, acceptance checks" | Out-Null
    Ok "First commit created"
} else { Ok "git repo already exists" }

Step "Done. Next steps"
Write-Host @"
  1. code .                        (open in VS Code, accept the recommended extensions)
  2. .\.venv\Scripts\Activate.ps1  (in the VS Code terminal)
  3. claude                        (accept the plugin install prompt, then run /doctor)
  4. Open prompts\01_python.md and follow it.
"@
