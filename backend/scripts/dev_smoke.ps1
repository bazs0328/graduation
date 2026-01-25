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

Write-Host "==> Quiz generate (easy)"
if ($docId) {
  $quiz = Invoke-RestMethod -Uri "$BaseUrl/quiz/generate" -Method Post -ContentType "application/json" -Body ('{"document_id":' + $docId + ',"count":5,"types":["single","judge","short"]}')
  $quiz | ConvertTo-Json -Compress
} else {
  Write-Host "document_id missing; skip quiz generate"
  $quiz = $null
}

$quizId = if ($quiz) { $quiz.quiz_id } else { $null }
$questions = if ($quiz) { $quiz.questions } else { @() }

Write-Host "==> Quiz submit"
if ($quizId -and $questions.Count -gt 0) {
  $answers = @()
  $wrongUsed = $false
  foreach ($q in $questions) {
    $qid = $q.question_id
    $qtype = $q.type
    $expected = $q.answer
    if ($qtype -eq "single") {
      $choice = if ($expected -and $expected.choice) { $expected.choice } else { "A" }
      if (-not $wrongUsed) {
        $wrongChoice = if ($choice -ne "B") { "B" } else { "C" }
        $userAnswer = @{ choice = $wrongChoice }
        $wrongUsed = $true
      } else {
        $userAnswer = @{ choice = $choice }
      }
    } elseif ($qtype -eq "judge") {
      $expectedValue = if ($expected -and $null -ne $expected.value) { [bool]$expected.value } else { $true }
      if (-not $wrongUsed) {
        $userAnswer = @{ value = (-not $expectedValue) }
        $wrongUsed = $true
      } else {
        $userAnswer = @{ value = $expectedValue }
      }
    } else {
      $userAnswer = @{ text = "self-review" }
    }
    $answers += @{ question_id = $qid; user_answer = $userAnswer }
  }

  $payload = @{ quiz_id = $quizId; answers = $answers } | ConvertTo-Json -Depth 6 -Compress
  $submit = Invoke-RestMethod -Uri "$BaseUrl/quiz/submit" -Method Post -ContentType "application/json" -Body $payload
  $submit | ConvertTo-Json -Compress
} else {
  Write-Host "quiz_id missing; skip quiz submit"
}
