import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getRecentQuizzes } from '../lib/api';
import { DIFFICULTY_LABELS } from '../lib/quizFormat';

function formatPercent(value) {
  if (typeof value !== 'number') {
    return 'N/A';
  }
  return `${Math.round(value * 100)}%`;
}

function formatDate(value) {
  if (!value) {
    return 'N/A';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'N/A';
  }
  return date.toLocaleString();
}

export default function DashboardPage({ sessionId }) {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);
  const [openQuizId, setOpenQuizId] = useState(null);

  const handleLoad = async () => {
    setStatus('正在加载最近测验...');
    setError(null);
    try {
      const result = await getRecentQuizzes(5, sessionId);
      setItems(result?.items || []);
      if (!result?.items?.length) {
        setStatus('暂无测验记录，请先完成一次测验。');
      } else {
        setStatus('');
      }
    } catch (err) {
      setError(err);
      setStatus('');
    }
  };

  const toggleSummary = (quizId) => {
    setOpenQuizId((prev) => (prev === quizId ? null : quizId));
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">仪表盘</p>
          <h1>最近学习记录</h1>
          <p className="subtle">展示最近 5 次测验的成绩与摘要。</p>
        </div>
        <div className="badge">/dashboard</div>
      </div>

      <div className="card">
        <div className="inline">
          <button className="primary" type="button" onClick={handleLoad}>
            加载最近测验
          </button>
          <span className="hint">基于当前会话 ID</span>
        </div>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
      </div>

      {items.length > 0 ? (
        <div className="result-list">
          {items.map((item) => (
            <div className="result-item" key={item.quiz_id}>
              <div className="result-header">
                <span className="badge">测验 #{item.quiz_id}</span>
                <span className="subtle">{formatDate(item.submitted_at)}</span>
                <span className="badge">
                  准确率 {formatPercent(item.accuracy)}
                </span>
                <span className="badge">得分 {item.score ?? 'N/A'}</span>
              </div>
              {item.difficulty_plan && (
                <div className="inline">
                  {Object.entries(item.difficulty_plan).map(([level, value]) => (
                    <span className="badge" key={level}>
                      {DIFFICULTY_LABELS[level] || level} {value}
                    </span>
                  ))}
                </div>
              )}
              <div className="inline">
                <button
                  className="secondary"
                  type="button"
                  onClick={() => toggleSummary(item.quiz_id)}
                >
                  {openQuizId === item.quiz_id ? '收起摘要' : '查看摘要'}
                </button>
                <Link className="source-link" to="/quiz">
                  查看测验
                </Link>
              </div>
              {openQuizId === item.quiz_id && (
                <pre className="code-block">
                  {JSON.stringify(item.summary || {}, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <p className="subtle">暂无测验记录。</p>
          <p className="subtle">
            先去 <Link className="source-link" to="/quiz">测验</Link>{' '}
            完成一次测验，再回来查看记录。
          </p>
        </div>
      )}
    </section>
  );
}
