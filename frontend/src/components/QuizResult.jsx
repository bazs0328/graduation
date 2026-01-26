import {
  DIFFICULTY_LABELS,
  TYPE_LABELS,
  formatExpectedAnswer,
  formatRecommendation,
  formatUserAnswer,
} from '../lib/quizFormat';

function getCorrectMeta(value) {
  if (value === true) {
    return { label: '正确', className: 'result-badge correct' };
  }
  if (value === false) {
    return { label: '错误', className: 'result-badge wrong' };
  }
  return { label: '未评分', className: 'result-badge pending' };
}

export default function QuizResult({ quiz, result, summary, showTitle = true }) {
  if (!result) {
    return null;
  }

  const questions = Array.isArray(quiz?.questions) ? quiz.questions : [];
  const questionsById = new Map(questions.map((item) => [item.question_id, item]));
  const difficultyPlan = quiz?.difficulty_plan || {};
  const recommendationText = formatRecommendation(summary);
  const perQuestion = Array.isArray(result.per_question_result)
    ? result.per_question_result
    : [];

  return (
    <div className="card">
      {showTitle && <h2>结果</h2>}
      <div className="grid-3">
        <div>
          <p className="label">得分</p>
          <p className="metric">{result.score}</p>
        </div>
        <div>
          <p className="label">准确率</p>
          <p className="metric">{result.accuracy}</p>
        </div>
        <div>
          <p className="label">反馈</p>
          <p className="subtle">{result.feedback_text}</p>
        </div>
      </div>

      <div className="result-meta">
        <div>
          <p className="label">难度计划</p>
          <div className="inline plan-badges">
            {Object.entries(difficultyPlan).map(([level, count]) => (
              <span className="badge" key={level}>
                {DIFFICULTY_LABELS[level] || level} {count}
              </span>
            ))}
          </div>
        </div>
        <div>
          <p className="label">推荐</p>
          <p className="subtle recommendation">{recommendationText}</p>
        </div>
      </div>

      <div className="result-list">
        {perQuestion.map((item, index) => {
          const question = questionsById.get(item.question_id);
          const type = question?.type || 'unknown';
          const correctMeta = getCorrectMeta(item.correct);
          const userText = formatUserAnswer(type, item.user_answer, question?.options);
          const expectedText = formatExpectedAnswer(
            type,
            item.expected_answer,
            question?.options,
          );

          return (
            <div className="result-item" key={item.question_id || index}>
              <div className="result-header">
                <span className={correctMeta.className}>{correctMeta.label}</span>
                <span className="badge">{TYPE_LABELS[type] || type}</span>
                {question?.difficulty ? (
                  <span className="badge">
                    {DIFFICULTY_LABELS[question.difficulty] || question.difficulty}
                  </span>
                ) : null}
              </div>
              <p className="question-title">
                {index + 1}. {question?.stem || '题干加载中'}
              </p>
              <p className="subtle result-answer">你的答案：{userText}</p>
              <p className="subtle result-answer">参考答案：{expectedText}</p>
              {question?.explanation && (
                <p className="hint">解析：{question.explanation}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
