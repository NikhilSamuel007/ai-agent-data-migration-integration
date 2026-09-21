$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $projectRoot '.cache/ollama-runtime/ollama.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Run scripts/bootstrap_ollama.py first, or install Ollama normally.' }
$env:OLLAMA_MODELS = Join-Path $projectRoot '.cache/ollama-models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_CONTEXT_LENGTH = '2048'
$env:OLLAMA_NUM_PARALLEL = '1'
Start-Process -FilePath $runtime -ArgumentList 'serve' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot '.cache/ollama-runtime/server.out.log') -RedirectStandardError (Join-Path $projectRoot '.cache/ollama-runtime/server.err.log')
Write-Output 'Ollama started on loopback port 11434. Pull a model using the runtime ollama.exe.'
