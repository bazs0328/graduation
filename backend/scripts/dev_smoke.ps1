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
  param(
    [string]$SessionId,
    [string]$Label = "Quiz generate"
  )
  Write-Host "==> $Label ($SessionId)"
  if (-not $docId) {
    Write-Host "document_id missing; skip quiz generate"
    return $null
  }
  $headers = @{ "X-Session-Id" = $SessionId }
  $payload = ('{"document_id":' + $docId + ',"count":5,"types":["single","judge","short"]}')
  $quiz = Invoke-RestMethod -Uri "$BaseUrl/quiz/generate" -Method Post -Headers $headers -ContentType "application/json" -Body $payload
  $quiz | ConvertTo-Json -Compress
  Write-Host ("quiz_id=" + $quiz.quiz_id)
  if ($quiz.questions) {
    Write-Host ("question_count=" + $quiz.questions.Count)
    if ($quiz.questions.Count -lt 5) {
      throw "quiz question count < 5"
    }
  }
  Write-Host ("difficulty_plan=" + ($quiz.difficulty_plan | ConvertTo-Json -Compress))
  return $quiz
}

function Submit-And-Profile {
  param(
    [string]$SessionId,
    [string]$Mode
  )
  $quiz = Generate-Quiz -SessionId $SessionId -Label "Quiz generate (initial)"
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
  Write-Host ("score=" + $submit.score + " accuracy=" + $submit.accuracy)
  if ($null -eq $submit.score -or $null -eq $submit.accuracy) {
    throw "submit missing score/accuracy"
  }
  $submit2 = Invoke-RestMethod -Uri "$BaseUrl/quiz/submit" -Method Post -Headers $headers -ContentType "application/json" -Body $payload
  $submit2 | ConvertTo-Json -Compress
  Write-Host "==> Profile me ($SessionId)"
  $profile = Invoke-RestMethod -Uri "$BaseUrl/profile/me" -Headers $headers
  $profile | ConvertTo-Json -Compress
  Write-Host ("profile_ability=" + $profile.ability_level + " frustration=" + $profile.frustration_score)
  if ($profile.last_quiz_summary) {
    Write-Host ("profile_last_accuracy=" + $profile.last_quiz_summary.accuracy)
    if ($profile.last_quiz_summary.next_quiz_recommendation) {
      Write-Host ("profile_recommendation=" + $profile.last_quiz_summary.next_quiz_recommendation)
    }
    if ($Mode -eq "bad" -and $profile.last_quiz_summary.next_quiz_recommendation -ne "easy_first") {
      throw "profile missing easy_first recommendation"
    }
  } elseif ($Mode -eq "bad") {
    throw "profile missing last_quiz_summary"
  }
  if ($Mode -eq "bad") {
    $nextQuiz = Generate-Quiz -SessionId $SessionId -Label "Quiz generate (after overhard)"
    if ($nextQuiz -and $nextQuiz.difficulty_plan) {
      Write-Host ("next_difficulty_plan=" + ($nextQuiz.difficulty_plan | ConvertTo-Json -Compress))
      if (($nextQuiz.difficulty_plan.Hard -ne 0) -or ($nextQuiz.difficulty_plan.Easy -lt 4)) {
        throw "overhard fallback not applied"
      }
    }
  }
}

Submit-And-Profile -SessionId "session-good" -Mode "good"
Submit-And-Profile -SessionId "session-bad" -Mode "bad"
