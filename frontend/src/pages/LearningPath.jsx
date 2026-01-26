import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getProfile } from '../lib/api';

const MIN_STEPS = 3;
const MAX_STEPS = 5;

function formatPercent(value) {
  if (typeof value !== 'number') {
    return '—';
  }
  return `${Math.round(value * 100)}%`;
}

function buildLearningPath(profile) {
  if (!profile) {
    return [];
  }

  const weakConcepts = Array.isArray(profile.weak_concepts)
    ? [...profile.weak_concepts]
    : [];
  const lastQuizSummary = profile.last_quiz_summary;
  const hasQuizSummary =
    lastQuizSummary && Object.keys(lastQuizSummary).length > 0;

  if (weakConcepts.length === 0 && !hasQuizSummary) {
    return [];
  }

  const steps = [];
  const seen = new Set();

  const pushStep = (step) => {
    if (!step || !step.title || seen.has(step.title)) {
      return;
    }
    seen.add(step.title);
    steps.push(step);
  };
  weakConcepts.sort(
    (left, right) => (right?.wrong_count ?? 0) - (left?.wrong_count ?? 0),
  );

  weakConcepts.slice(0, 3).forEach((concept) => {
    const name = concept?.concept || '未命名概念';
    const wrongCount = concept?.wrong_count ?? 0;
    const wrongRate = formatPercent(concept?.wrong_rate);
    pushStep({
      title: `复习概念：${name}`,
      reason: `该概念错题 ${wrongCount} 次，错误率 ${wrongRate}。`,
      source: { label: '学习画像', to: '/profile' },
    });
  });

  const lastQuiz = hasQuizSummary ? lastQuizSummary : {};
  if (typeof lastQuiz.accuracy === 'number') {
    pushStep({
      title: '回顾最近测验错题',
      reason: `最近一次测验准确率为 ${formatPercent(
        lastQuiz.accuracy,
      )}，建议复盘错题。`,
      source: { label: '最近测验', to: '/quiz' },
    });
  }

  if (
    profile.frustration_score >= 6 ||
    lastQuiz.next_quiz_recommendation === 'easy_first'
  ) {
    pushStep({
      title: '先做简单题巩固基础',
      reason: '系统建议优先简单题，逐步建立信心。',
      source: { label: '测验建议', to: '/quiz' },
    });
  }

  const fillers = [
    {
      title: '回看资料并标注关键段落',
      reason: '把与薄弱概念相关的段落标注出来，降低遗忘率。',
      source: { label: '资料管理', to: '/upload' },
    },
    {
      title: '围绕薄弱概念提一个问题',
      reason: '用问答验证理解是否完整。',
      source: { label: '问答', to: '/chat' },
    },
    {
      title: '完成一轮小测验',
      reason: '将复习结果应用到新的题目上。',
      source: { label: '测验', to: '/quiz' },
    },
  ];

  for (const filler of fillers) {
    if (steps.length >= MIN_STEPS) {
      break;
    }
    pushStep(filler);
  }

  return steps.slice(0, MAX_STEPS);
}

export default function LearningPathPage({ sessionId }) {
  const [profile, setProfile] = useState(null);
  const [steps, setSteps] = useState([]);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  const handleLoad = async () => {
    setStatus('正在生成学习路径...');
    setError(null);
    try {
      const result = await getProfile(sessionId);
      setProfile(result);
      const nextSteps = buildLearningPath(result);
      setSteps(nextSteps);
      if (nextSteps.length === 0) {
        setStatus('暂无可用路径，请先完成一次测验。');
      } else {
        setStatus('');
      }
    } catch (err) {
      setError(err);
      setStatus('');
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">学习路径</p>
          <h1>学习路径 Lite</h1>
          <p className="subtle">
            基于学习画像的规则驱动推荐，给出下一步行动建议。
          </p>
        </div>
        <div className="badge">规则驱动</div>
      </div>

      <div className="card">
        <div className="inline">
          <button className="primary" type="button" onClick={handleLoad}>
            生成学习路径
          </button>
          <span className="hint">需要先完成一次测验</span>
        </div>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
      </div>

      {profile && (
        <div className="grid-3">
          <div className="card">
            <p className="label">能力水平</p>
            <p className="metric">{profile.ability_level || 'unknown'}</p>
          </div>
          <div className="card">
            <p className="label">最近准确率</p>
            <p className="metric">
              {formatPercent(profile.last_quiz_summary?.accuracy)}
            </p>
          </div>
          <div className="card">
            <p className="label">挫败度</p>
            <p className="metric">{profile.frustration_score ?? 0}</p>
          </div>
        </div>
      )}

      <div className="path-list">
        {steps.length > 0 ? (
          steps.map((step, index) => (
            <div className="path-card" key={step.title}>
              <div className="path-header">
                <span className="badge">步骤 {index + 1}</span>
                <h2 className="path-title">{step.title}</h2>
              </div>
              <p className="path-reason">{step.reason}</p>
              <div className="path-source">
                <span className="label">来源</span>
                {step.source ? (
                  <Link className="source-link" to={step.source.to}>
                    {step.source.label}
                  </Link>
                ) : (
                  <span className="subtle">暂无</span>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="card">
            <p className="subtle">
              暂无学习路径，请先完成测验并刷新画像。
            </p>
            <p className="subtle">
              你可以先去{' '}
              <Link className="source-link" to="/quiz">
                测验
              </Link>{' '}
              或{' '}
              <Link className="source-link" to="/profile">
                画像
              </Link>{' '}
              看看数据是否更新。
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
