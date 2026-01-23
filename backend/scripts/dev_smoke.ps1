param(
  [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "==> Health"
$health = Invoke-RestMethod -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Compress

Write-Host "==> Upload sample.md"
$samplePath = Join-Path $PSScriptRoot "..\..\sample.md"
if (-not (Test-Path $samplePath)) { throw "sample.md not found at $samplePath" }
$uploadRaw = & curl.exe -s -F "file=@$samplePath" "$BaseUrl/docs/upload"
$upload = $uploadRaw | ConvertFrom-Json
$upload | ConvertTo-Json -Compress

$docId = $upload.document_id
Write-Host "document_id=$docId"

Write-Host "==> Rebuild index"
$rebuild = Invoke-RestMethod -Uri "$BaseUrl/index/rebuild" -Method Post
$rebuild | ConvertTo-Json -Compress

Write-Host "==> Search keyword"
$search = Invoke-RestMethod -Uri "$BaseUrl/search" -Method Post -ContentType "application/json" -Body '{"query":"fox","top_k":5}'
$search | ConvertTo-Json -Compress

Write-Host "==> Chat question"
$chat = Invoke-RestMethod -Uri "$BaseUrl/chat" -Method Post -ContentType "application/json" -Body '{"query":"fox","top_k":5}'
$chat | ConvertTo-Json -Compress
