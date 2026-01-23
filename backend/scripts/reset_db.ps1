param()

$ErrorActionPreference = "Stop"

$mysqlUser = $env:MYSQL_USER; if (-not $mysqlUser) { $mysqlUser = "app_user" }
$mysqlPassword = $env:MYSQL_PASSWORD; if (-not $mysqlPassword) { $mysqlPassword = "app_pass" }
$mysqlDatabase = $env:MYSQL_DATABASE; if (-not $mysqlDatabase) { $mysqlDatabase = "app_db" }

Write-Host "Truncating tables in $mysqlDatabase..."
docker compose exec -T db mysql -u$mysqlUser -p$mysqlPassword -D $mysqlDatabase -e "TRUNCATE TABLE chunks; TRUNCATE TABLE documents;"

Write-Host "Removing local FAISS index files..."
$baseDir = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Remove-Item -ErrorAction SilentlyContinue -Path (Join-Path $baseDir "backend\data\faiss.index"), (Join-Path $baseDir "backend\data\mapping.json")

Write-Host "Done."