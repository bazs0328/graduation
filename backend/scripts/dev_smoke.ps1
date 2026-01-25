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

function Build-Answers {
  param(
    [object[]]$QuestionItems,
    [bool]$MakeWrong
  )
  $results = @()
  $usedWrong = $false
  foreach ($q in $QuestionItems) {
    $qid = $q.question_id
    $qtype = $q.type
    $expected = $q.answer
    if ($qtype -eq "single") {
      $choice = if ($expected -and $expected.choice) { $expected.choice } else { "A" }
      $wrongChoice = if ($choice -ne "B") { "B" } else { "C" }
      if ($MakeWrong -or -not $usedWrong) {
        $userAnswer = @{ choice = $wrongChoice }
        $usedWrong = $true
      } else {
        $userAnswer = @{ choice = $choice }
      }
    } elseif ($qtype -eq "judge") {
      $expectedValue = if ($expected -and $null -ne $expected.value) { [bool]$expected.value } else { $true }
      if ($MakeWrong -or -not $usedWrong) {
        $userAnswer = @{ value = (-not $expectedValue) }
        $usedWrong = $true
      } else {
        $userAnswer = @{ value = $expectedValue }
      }
    } else {
      $userAnswer = @{ text = "self-review" }
    }
    $results += @{ question_id = $qid; user_answer = $userAnswer }
  }
  return $results
}

function Generate-Quiz {
  param([string]$SessionId)
  Write-Host "==> Quiz generate (easy) ($SessionId)"
  if (-not $docId) {
    Write-Host "document_id missing; skip quiz generate"
    return $null
  }
  $headers = @{ "X-Session-Id" = $SessionId }
  $payload = ('{"document_id":' + $docId + ',"count":5,"types":["single","judge","short"]}')
  $quiz = Invoke-RestMethod -Uri "$BaseUrl/quiz/generate" -Method Post -Headers $headers -ContentType "application/json" -Body $payload
  $quiz | ConvertTo-Json -Compress
  return $quiz
}

function Submit-And-Profile {
  param(
    [string]$SessionId,
    [string]$Mode
  )
  $quiz = Generate-Quiz -SessionId $SessionId
  if (-not $quiz) {
    Write-Host "quiz_id missing; skip quiz submit"
    return
  }
  $quizId = $quiz.quiz_id
  $questions = $quiz.questions
  if (-not $quizId -or $questions.Count -eq 0) {
    Write-Host "quiz_id missing; skip quiz submit"
    return
  }
  Write-Host "==> Quiz submit ($SessionId)"
  $headers = @{ "X-Session-Id" = $SessionId }
  $makeWrong = $Mode -eq "bad"
  $answers = Build-Answers -QuestionItems $questions -MakeWrong:$makeWrong
  $payload = @{ quiz_id = $quizId; answers = $answers } | ConvertTo-Json -Depth 6 -Compress
  $submit = Invoke-RestMethod -Uri "$BaseUrl/quiz/submit" -Method Post -Headers $headers -ContentType "application/json" -Body $payload
  $submit | ConvertTo-Json -Compress
  $submit2 = Invoke-RestMethod -Uri "$BaseUrl/quiz/submit" -Method Post -Headers $headers -ContentType "application/json" -Body $payload
  $submit2 | ConvertTo-Json -Compress
  Write-Host "==> Profile me ($SessionId)"
  $profile = Invoke-RestMethod -Uri "$BaseUrl/profile/me" -Headers $headers
  $profile | ConvertTo-Json -Compress
}

Submit-And-Profile -SessionId "session-good" -Mode "good"
Submit-And-Profile -SessionId "session-bad" -Mode "bad"
