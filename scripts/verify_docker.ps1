# Run on a machine with Docker Desktop (Linux containers) running.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is not installed. Container verification cannot run.' }
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is not available.' }
# Alternate ports and an isolated Compose project preserve the local demo.
$env:RELAY_BACKEND_PORT = '18000'
$env:RELAY_FRONTEND_PORT = '13000'
try {
    docker compose -p relay-verification config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed.' }
    docker compose -p relay-verification up --build --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) { throw 'Container build or health checks failed.' }
    $api = 'http://localhost:18000'
    $health = Invoke-RestMethod "$api/api/health"
    if ($health.status -ne 'ok') { throw 'Backend health failed.' }
    $schema = Invoke-RestMethod "$api/api/schema"
    if ($schema.version -ne 3) { throw 'Wrong schema in image.' }
    $ui = Invoke-WebRequest 'http://localhost:13000/' -UseBasicParsing
    if ($ui.StatusCode -ne 200) { throw 'Frontend unavailable.' }
    $run = Invoke-RestMethod "$api/api/demo" -Method Post -ContentType 'application/json' -Body '{}'
    $deadline = (Get-Date).AddSeconds(180)
    do {
        Start-Sleep -Seconds 1
        $run = Invoke-RestMethod "$api/api/runs/$($run.id)"
    } while ($run.status -eq 'mapping' -and (Get-Date) -lt $deadline)
    if ($run.status -ne 'mapping_review') { throw 'Expected Status escalation.' }
    $body = @{file='staff.xlsx';header='Status';field='employment_status';reason='Docker smoke test: HR export'} | ConvertTo-Json
    Invoke-RestMethod "$api/api/runs/$($run.id)/mapping" -Method Post -ContentType 'application/json' -Body $body | Out-Null
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Seconds 1
        $run = Invoke-RestMethod "$api/api/runs/$($run.id)"
    } while ($run.status -ne 'partial' -and (Get-Date) -lt $deadline)
    if ($run.targetCount -ne 6) { throw 'Expected six successful writes after exhausted retries.' }
    Invoke-RestMethod "$api/api/runs/$($run.id)/rollback" -Method Post -ContentType 'application/json' -Body '{}' | Out-Null
    Write-Output 'Docker builds, health, schema, frontend, review, delivery and rollback passed.'
} finally {
    docker compose -p relay-verification down
    Remove-Item Env:RELAY_BACKEND_PORT,Env:RELAY_FRONTEND_PORT -ErrorAction SilentlyContinue
}
