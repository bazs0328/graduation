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

function Submit-And-Profile {
  param([string]$SessionId)
  Write-Host "==> Quiz submit ($SessionId)"
  if (-not $quizId -or $questions.Count -eq 0) {
    Write-Host "quiz_id missing; skip quiz submit"
    return
  }
  $headers = @{ "X-Session-Id" = $SessionId }
  $answersMixed = Build-Answers -QuestionItems $questions -MakeWrong:$false
  $answersWrong = Build-Answers -QuestionItems $questions -MakeWrong:$true
  $payload = @{ quiz_id = $quizId; answers = $answersMixed } | ConvertTo-Json -Depth 6 -Compress
  $submit = Invoke-RestMethod -Uri "$BaseUrl/quiz/submit" -Method Post -Headers $headers -ContentType "application/json" -Body $payload
  $submit | ConvertTo-Json -Compress
  $payloadWrong = @{ quiz_id = $quizId; answers = $answersWrong } | ConvertTo-Json -Depth 6 -Compress
  $submitWrong = Invoke-RestMethod -Uri "$BaseUrl/quiz/submit" -Method Post -Headers $headers -ContentType "application/json" -Body $payloadWrong
  $submitWrong | ConvertTo-Json -Compress
  Write-Host "==> Profile me ($SessionId)"
  $profile = Invoke-RestMethod -Uri "$BaseUrl/profile/me" -Headers $headers
  $profile | ConvertTo-Json -Compress
}

Submit-And-Profile -SessionId "session-good"
Submit-And-Profile -SessionId "session-bad"
