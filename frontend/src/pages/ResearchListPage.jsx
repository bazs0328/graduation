import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createResearch, listResearch } from '../lib/api';

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

export default function ResearchListPage({ sessionId }) {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [createStatus, setCreateStatus] = useState('');
  const [createError, setCreateError] = useState(null);
  const sessionReady = Boolean((sessionId || '').trim());
  const summaryTemplate =
    '问题：\n证据：\n结论：\n下一步：';

  const loadResearch = useCallback(async () => {
    setStatus('正在加载研究记录...');
    setError(null);
    try {
      const result = await listResearch(sessionId);
      setItems(result?.items || []);
      if (!result?.items?.length) {
        setStatus('暂无研究记录，先创建一个新的 Notebook。');
      } else {
        setStatus('');
      }
    } catch (err) {
      setError(err);
      setStatus('');
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionReady) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadResearch();
    } else {
      setItems([]);
    }
  }, [sessionReady, sessionId, loadResearch]);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!sessionReady) {
      setCreateError(new Error('请先在顶部填写会话 ID。'));
      return;
    }
    if (!title.trim()) {
      setCreateError(new Error('请填写研究标题。'));
      return;
    }
    setCreateStatus('正在创建...');
    setCreateError(null);
    try {
      await createResearch(
        {
          title: title.trim(),
          summary: summary.trim() || null,
        },
        sessionId,
      );
      setTitle('');
      setSummary('');
      setCreateStatus('已创建，可在列表中查看。');
      await loadResearch();
    } catch (err) {
      setCreateError(err);
      setCreateStatus('');
    }
  };

  return (
    <section className="page research-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">研究 / Notebook</p>
          <h1>研究记录</h1>
          <p className="subtle">
            把工具轨迹、引用摘要与结论组织成可回访的研究记录。
          </p>
        </div>
        <div className="badge">/research</div>
      </div>

      <div className="research-hero card">
        <div>
          <p className="label">快速提示</p>
          <h2>把研究过程变成可追溯产物</h2>
          <p className="subtle">
            每条记录可包含工具轨迹和引用摘要，便于在详情页复盘。
          </p>
        </div>
        <div className="research-hero-tags">
          <span className="badge">工具轨迹</span>
          <span className="badge">引用摘要</span>
          <span className="badge">可回访</span>
        </div>
      </div>

      <div className="research-layout">
        <div className="card">
          <div className="inline">
            <h2>新建研究</h2>
            <span className="badge">Notebook</span>
          </div>
          <form className="form" onSubmit={handleCreate}>
            <label className="field">
              <span>标题</span>
              <input
                className="input"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="例如：LLM 引用可信度评估"
              />
            </label>
            <label className="field">
              <span>摘要（可选）</span>
              <textarea
                className="input"
                rows="3"
                value={summary}
                onChange={(event) => setSummary(event.target.value)}
                placeholder="概括研究目标或当前结论"
              />
            </label>
            <button
              className="ghost"
              type="button"
              onClick={() => setSummary(summaryTemplate)}
            >
              使用结构化摘要模板
            </button>
            <button className="primary" type="submit" disabled={!sessionReady}>
              创建研究记录
            </button>
          </form>
          {createStatus && <p className="status">{createStatus}</p>}
          {createError && <p className="alert error">{createError.message}</p>}
          {!sessionReady && (
            <p className="alert info">请先在顶部填写会话 ID，再创建记录。</p>
          )}
        </div>

        <div className="card research-tips">
          <p className="label">建议流程</p>
          <ol className="steps">
            <li>先写清楚问题与目标</li>
            <li>追加工具调用与来源摘要</li>
            <li>用条目记录结论与下一步</li>
          </ol>
        </div>
      </div>

      <div className="card">
        <div className="inline">
          <h2>研究列表</h2>
          <button className="secondary" type="button" onClick={loadResearch}>
            刷新列表
          </button>
        </div>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
        {items.length ? (
          <div className="research-list">
            {items.map((item) => (
              <div className="research-item" key={item.research_id}>
                <div>
                  <h3>{item.title || '未命名研究'}</h3>
                  <p className="subtle">{item.summary || '暂无摘要'}</p>
                </div>
                <div className="research-meta">
                  <span className="badge">条目 {item.entry_count}</span>
                  <span className="badge">更新 {formatDate(item.updated_at)}</span>
                </div>
                <Link className="primary link-button" to={`/research/${item.research_id}`}>
                  查看详情
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtle">暂无研究记录。</p>
        )}
      </div>
    </section>
  );
}
