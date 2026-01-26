import { useMemo, useState } from 'react';
import { generateQuiz, getProfile, submitQuiz } from '../lib/api';
import { DIFFICULTY_LABELS, TYPE_LABELS } from '../lib/quizFormat';
import QuizQuestion from '../components/QuizQuestion';
import QuizResult from '../components/QuizResult';

const DEFAULT_TYPES = {
  single: true,
  judge: true,
  short: true,
};

export default function QuizPage({ sessionId, documentId }) {
  const [docId, setDocId] = useState(documentId || '');
  const [count, setCount] = useState(5);
  const [types, setTypes] = useState(DEFAULT_TYPES);
  const [focusConcepts, setFocusConcepts] = useState('');
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitResult, setSubmitResult] = useState(null);
  const [profileSummary, setProfileSummary] = useState(null);
  const [profileStatus, setProfileStatus] = useState('');
  const [profileError, setProfileError] = useState(null);
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
    setProfileSummary(null);
    setProfileError(null);
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
    setProfileError(null);
    setProfileStatus('');
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
      return;
    }

    setProfileStatus('正在同步画像推荐...');
    try {
      const profile = await getProfile(sessionId);
      setProfileSummary(profile?.last_quiz_summary || null);
      setProfileStatus('');
    } catch (err) {
      setProfileError(err);
      setProfileStatus('');
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
          <div className="plan-panel">
            <p className="label">难度计划</p>
            <div className="inline plan-badges">
              {Object.entries(quiz.difficulty_plan || {}).map(
                ([level, value]) => (
                  <span className="badge" key={level}>
                    {DIFFICULTY_LABELS[level] || level} {value}
                  </span>
                ),
              )}
            </div>
          </div>
        )}
      </div>

      {quiz && (
        <div className="card">
          <h2>题目</h2>
          <div className="question-list">
            {quiz.questions.map((question, index) => (
              <QuizQuestion
                key={question.question_id}
                question={question}
                index={index}
                value={answers[question.question_id]}
                onChange={updateAnswer}
              />
            ))}
          </div>
          <button className="primary" type="button" onClick={handleSubmit}>
            提交测验
          </button>
        </div>
      )}

      {submitResult && profileStatus && <p className="status">{profileStatus}</p>}
      {submitResult && profileError && (
        <p className="alert error">
          推荐信息加载失败：{profileError.message}
        </p>
      )}
      {submitResult && (
        <QuizResult quiz={quiz} result={submitResult} summary={profileSummary} />
      )}
    </section>
  );
}
