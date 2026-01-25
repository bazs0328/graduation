import { useMemo, useState } from 'react';
import { generateQuiz, submitQuiz } from '../lib/api';

const DEFAULT_TYPES = {
  single: true,
  judge: true,
  short: true,
};

const TYPE_LABELS = {
  single: '单选',
  judge: '判断',
  short: '简答',
};

const DIFFICULTY_LABELS = {
  Easy: '易',
  Medium: '中',
  Hard: '难',
};

function letterForIndex(index) {
  return String.fromCharCode(65 + index);
}

export default function QuizPage({ sessionId, documentId }) {
  const [docId, setDocId] = useState(documentId || '');
  const [count, setCount] = useState(5);
  const [types, setTypes] = useState(DEFAULT_TYPES);
  const [focusConcepts, setFocusConcepts] = useState('');
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitResult, setSubmitResult] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  const selectedTypes = useMemo(
    () => Object.entries(types).filter(([, value]) => value).map(([key]) => key),
    [types],
  );

  const handleGenerate = async () => {
    setStatus('正在生成测验...');
    setError(null);
    setSubmitResult(null);
    try {
      const payload = {
        count: Number(count) || 5,
        types: selectedTypes.length ? selectedTypes : ['single'],
      };
      const parsedDocId = Number(docId);
      if (parsedDocId) {
        payload.document_id = parsedDocId;
      }
      const focusList = focusConcepts
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
      if (focusList.length) {
        payload.focus_concepts = focusList;
      }

      const result = await generateQuiz(payload, sessionId);
      setQuiz(result);
      setAnswers({});
      setStatus('测验已生成。');
    } catch (err) {
      setError(err);
      setStatus('');
    }
  };

  const handleSubmit = async () => {
    if (!quiz) {
      return;
    }
    setStatus('正在提交测验...');
    setError(null);
    try {
      const payload = {
        quiz_id: quiz.quiz_id,
        answers: quiz.questions.map((question) => {
          const stored = answers[question.question_id];
          let userAnswer = stored ?? null;
          if (question.type === 'single') {
            userAnswer = stored ? { choice: stored } : null;
          } else if (question.type === 'judge') {
            userAnswer = typeof stored === 'boolean' ? { value: stored } : null;
          } else if (question.type === 'short') {
            userAnswer = stored ? { text: stored } : null;
          }
          return {
            question_id: question.question_id,
            user_answer: userAnswer,
          };
        }),
      };
      const result = await submitQuiz(payload, sessionId);
      setSubmitResult(result);
      setStatus('');
    } catch (err) {
      setError(err);
      setStatus('');
    }
  };

  const updateAnswer = (questionId, value) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">测验</p>
          <h1>生成并提交</h1>
          <p className="subtle">在同一页面完成生成与提交。</p>
        </div>
      </div>

      <div className="card">
        <div className="form-grid">
          <label className="field">
            <span>文档 ID</span>
            <input
              className="input"
              value={docId}
              onChange={(event) => setDocId(event.target.value)}
              placeholder="可选"
            />
          </label>
          <label className="field">
            <span>题量</span>
            <input
              className="input"
              type="number"
              min="1"
              max="20"
              value={count}
              onChange={(event) => setCount(event.target.value)}
            />
          </label>
          <label className="field">
            <span>重点概念（逗号分隔）</span>
            <input
              className="input"
              value={focusConcepts}
              onChange={(event) => setFocusConcepts(event.target.value)}
              placeholder="可选"
            />
          </label>
        </div>
        <div className="inline">
          {Object.keys(types).map((typeKey) => (
            <label className="checkbox" key={typeKey}>
              <input
                type="checkbox"
                checked={types[typeKey]}
                onChange={() =>
                  setTypes((prev) => ({ ...prev, [typeKey]: !prev[typeKey] }))
                }
              />
              <span>{TYPE_LABELS[typeKey] || typeKey}</span>
            </label>
          ))}
        </div>
        <button className="primary" type="button" onClick={handleGenerate}>
          生成测验
        </button>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
        {quiz && (
          <pre className="code-block">
            {JSON.stringify(quiz.difficulty_plan, null, 2)}
          </pre>
        )}
      </div>

      {quiz && (
        <div className="card">
          <h2>题目</h2>
          <div className="question-list">
            {quiz.questions.map((question, index) => (
              <div className="question" key={question.question_id}>
                <div className="question-meta">
                  <span className="badge">
                    {TYPE_LABELS[question.type] || question.type}
                  </span>
                  <span className="badge">
                    {DIFFICULTY_LABELS[question.difficulty] ||
                      question.difficulty}
                  </span>
                </div>
                <p className="question-title">
                  {index + 1}. {question.stem}
                </p>
                {question.options?.length ? (
                  <div className="options">
                    {question.options.map((option, optionIndex) => {
                      const letter = letterForIndex(optionIndex);
                      return (
                        <label className="option" key={letter}>
                          <input
                            type="radio"
                            name={`q-${question.question_id}`}
                            value={letter}
                            checked={answers[question.question_id] === letter}
                            onChange={() =>
                              updateAnswer(question.question_id, letter)
                            }
                          />
                          <span>
                            {letter}. {option}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                ) : null}
                {question.type === 'judge' && (
                  <div className="options">
                    <label className="option">
                      <input
                        type="radio"
                        name={`q-${question.question_id}`}
                        checked={answers[question.question_id] === true}
                        onChange={() => updateAnswer(question.question_id, true)}
                      />
                      <span>正确</span>
                    </label>
                    <label className="option">
                      <input
                        type="radio"
                        name={`q-${question.question_id}`}
                        checked={answers[question.question_id] === false}
                        onChange={() => updateAnswer(question.question_id, false)}
                      />
                      <span>错误</span>
                    </label>
                  </div>
                )}
                {question.type === 'short' && (
                  <label className="field">
                    <span>你的回答</span>
                    <textarea
                      className="input"
                      rows="3"
                      value={answers[question.question_id] || ''}
                      onChange={(event) =>
                        updateAnswer(question.question_id, event.target.value)
                      }
                    />
                  </label>
                )}
                {question.explanation && (
                  <p className="subtle">解析：{question.explanation}</p>
                )}
              </div>
            ))}
          </div>
          <button className="primary" type="button" onClick={handleSubmit}>
            提交测验
          </button>
        </div>
      )}

      {submitResult && (
        <div className="card">
          <h2>结果</h2>
          <div className="grid-3">
            <div>
              <p className="label">得分</p>
              <p className="metric">{submitResult.score}</p>
            </div>
            <div>
              <p className="label">准确率</p>
              <p className="metric">{submitResult.accuracy}</p>
            </div>
            <div>
              <p className="label">反馈</p>
              <p className="subtle">{submitResult.feedback_text}</p>
            </div>
          </div>
          <pre className="code-block">
            {JSON.stringify(submitResult.per_question_result, null, 2)}
          </pre>
        </div>
      )}
    </section>
  );
}
