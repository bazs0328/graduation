import { useEffect, useMemo, useState } from 'react';
import { resolveSources } from '../lib/api';
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
  const [sourceMap, setSourceMap] = useState({});
  const [sourceStatus, setSourceStatus] = useState('');
  const [sourceError, setSourceError] = useState(null);
  const questions = useMemo(
    () => (Array.isArray(quiz?.questions) ? quiz.questions : []),
    [quiz],
  );
  const questionsById = useMemo(
    () => new Map(questions.map((item) => [item.question_id, item])),
    [questions],
  );
  const safeResult = result || {};
  const difficultyPlan = quiz?.difficulty_plan || {};
  const recommendationText = formatRecommendation(summary);
  const perQuestion = Array.isArray(safeResult.per_question_result)
    ? safeResult.per_question_result
    : [];
  const allChunkIds = useMemo(() => {
    const ids = new Set();
    questions.forEach((question) => {
      (question?.source_chunk_ids || []).forEach((chunkId) => {
        if (Number.isInteger(chunkId)) {
          ids.add(chunkId);
        }
      });
    });
    return Array.from(ids);
  }, [questions]);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!allChunkIds.length) {
      setSourceMap({});
      return;
    }
    let active = true;
    setSourceStatus('正在加载引用...');
    setSourceError(null);
    resolveSources({ chunk_ids: allChunkIds })
      .then((result) => {
        if (!active) return;
        const map = {};
        (result?.items || []).forEach((item) => {
          if (item?.chunk_id != null) {
            map[item.chunk_id] = item;
          }
        });
        setSourceMap(map);
        setSourceStatus('');
      })
      .catch((err) => {
        if (!active) return;
        setSourceError(err);
        setSourceStatus('');
      });
    return () => {
      active = false;
    };
  }, [allChunkIds]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (!result) {
    return null;
  }

  return (
    <div className="card">
      {showTitle && <h2>结果</h2>}
      <div className="grid-3">
        <div>
          <p className="label">得分</p>
          <p className="metric">{safeResult.score}</p>
        </div>
        <div>
          <p className="label">准确率</p>
          <p className="metric">{safeResult.accuracy}</p>
        </div>
        <div>
          <p className="label">反馈</p>
          <p className="subtle">{safeResult.feedback_text}</p>
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

      {sourceStatus && <p className="hint">{sourceStatus}</p>}
      {sourceError && (
        <p className="alert error">引用加载失败：{sourceError.message}</p>
      )}
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
              {question?.difficulty_reason && (
                <p className="hint">难度理由：{question.difficulty_reason}</p>
              )}
              {question?.key_points?.length ? (
                <div className="hint">
                  <span className="label">考点</span>
                  <div className="inline">
                    {question.key_points.map((point, idx) => (
                      <span className="badge" key={`${point}-${idx}`}>
                        {point}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
              {question?.review_suggestion && (
                <p className="hint">复习建议：{question.review_suggestion}</p>
              )}
              {question?.next_step && (
                <p className="hint">下一步行动：{question.next_step}</p>
              )}
              {question?.validation && (
                <p className="hint">
                  校验：{question.validation.kb_coverage || 'n/a'} ·{' '}
                  {question.validation.extension_points || 'n/a'}
                </p>
              )}
              <div className="sources">
                <p className="label">引用来源</p>
                {question?.source_chunk_ids?.length ? (
                  <div className="source-list">
                    {question.source_chunk_ids
                      .map((chunkId) => sourceMap[chunkId])
                      .filter(Boolean)
                      .map((source) => (
                        <div className="source-item" key={source.chunk_id}>
                          <div className="source-meta">
                            <span className="badge">
                              {source.document_name
                                ? source.document_name
                                : `文档 ${source.document_id}`}
                            </span>
                            <span className="badge">片段 {source.chunk_id}</span>
                          </div>
                          <p className="source-preview">
                            {source.text_preview || '暂无摘要'}
                          </p>
                        </div>
                      ))}
                    {!question.source_chunk_ids
                      .map((chunkId) => sourceMap[chunkId])
                      .filter(Boolean).length && (
                      <p className="subtle">暂无引用可展示。</p>
                    )}
                  </div>
                ) : (
                  <p className="subtle">暂无引用可展示。</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
