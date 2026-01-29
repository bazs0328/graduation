import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { appendResearchEntry, getResearchDetail } from '../lib/api';

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

function safeJsonParse(value, label) {
  if (!value.trim()) {
    return null;
  }
  try {
    return JSON.parse(value);
  } catch (err) {
    const error = new Error(`${label} 不是有效的 JSON。`);
    error.cause = err;
    throw error;
  }
}

export default function ResearchDetailPage({ sessionId }) {
  const { researchId } = useParams();
  const [detail, setDetail] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);
  const [entryType, setEntryType] = useState('note');
  const [content, setContent] = useState('');
  const [toolTraces, setToolTraces] = useState('');
  const [sources, setSources] = useState('');
  const [submitStatus, setSubmitStatus] = useState('');
  const [submitError, setSubmitError] = useState(null);
  const [openEntryId, setOpenEntryId] = useState(null);
  const sessionReady = Boolean((sessionId || '').trim());

  const loadDetail = useCallback(async () => {
    if (!researchId) {
      return;
    }
    setStatus('正在加载研究详情...');
    setError(null);
    try {
      const result = await getResearchDetail(researchId, sessionId);
      setDetail(result);
      setStatus('');
    } catch (err) {
      setError(err);
      setStatus('');
    }
  }, [researchId, sessionId]);

  useEffect(() => {
    if (sessionReady && researchId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadDetail();
    }
  }, [sessionReady, researchId, sessionId, loadDetail]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!sessionReady) {
      setSubmitError(new Error('请先填写会话 ID。'));
      return;
    }
    if (!content.trim()) {
      setSubmitError(new Error('请填写条目内容。'));
      return;
    }
    setSubmitStatus('正在追加条目...');
    setSubmitError(null);
    try {
      const payload = {
        entry_type: entryType.trim() || 'note',
        content: content.trim(),
        tool_traces: safeJsonParse(toolTraces, '工具轨迹') || undefined,
        sources: safeJsonParse(sources, '引用摘要') || undefined,
      };
      await appendResearchEntry(researchId, payload, sessionId);
      setContent('');
      setToolTraces('');
      setSources('');
      setSubmitStatus('已追加，可在下方查看。');
      await loadDetail();
    } catch (err) {
      setSubmitError(err);
      setSubmitStatus('');
    }
  };

  const toggleEntry = (entryId) => {
    setOpenEntryId((prev) => (prev === entryId ? null : entryId));
  };

  return (
    <section className="page research-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">研究详情</p>
          <h1>{detail?.title || '研究详情'}</h1>
          <p className="subtle">{detail?.summary || '暂无摘要'}</p>
        </div>
        <div className="inline">
          <Link className="secondary" to="/research">
            返回列表
          </Link>
          <span className="badge">ID {researchId}</span>
        </div>
      </div>

      <div className="card research-detail-card">
        <div className="inline">
          <h2>追加研究条目</h2>
          <span className="badge">Entry</span>
        </div>
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>条目类型</span>
            <input
              className="input"
              value={entryType}
              onChange={(event) => setEntryType(event.target.value)}
              placeholder="note / analysis / tool / decision"
            />
          </label>
          <label className="field">
            <span>内容</span>
            <textarea
              className="input"
              rows="4"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              placeholder="描述当前发现、结论或下一步行动"
            />
          </label>
          <label className="field">
            <span>工具轨迹（JSON，可选）</span>
            <textarea
              className="input code-input"
              rows="4"
              value={toolTraces}
              onChange={(event) => setToolTraces(event.target.value)}
              placeholder='[{"tool_name":"calc","input":{"expression":"2+2"},"output":"4"}]'
            />
          </label>
          <label className="field">
            <span>引用摘要（JSON，可选）</span>
            <textarea
              className="input code-input"
              rows="4"
              value={sources}
              onChange={(event) => setSources(event.target.value)}
              placeholder='[{"document_name":"sample.md","text_preview":"...","chunk_id":1}]'
            />
          </label>
          <button className="primary" type="submit" disabled={!sessionReady}>
            追加条目
          </button>
        </form>
        {submitStatus && <p className="status">{submitStatus}</p>}
        {submitError && <p className="alert error">{submitError.message}</p>}
        {!sessionReady && (
          <p className="alert info">请先在顶部填写会话 ID，再追加条目。</p>
        )}
      </div>

      <div className="card">
        <div className="inline">
          <h2>条目时间线</h2>
          <button className="secondary" type="button" onClick={loadDetail}>
            刷新详情
          </button>
        </div>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
        {detail?.entries?.length ? (
          <div className="research-entries">
            {detail.entries.map((entry) => (
              <div className="research-entry" key={entry.entry_id}>
                <div className="research-entry-header">
                  <div>
                    <span className="badge">{entry.entry_type}</span>
                    <span className="badge">#{entry.entry_id}</span>
                  </div>
                  <span className="subtle">{formatDate(entry.created_at)}</span>
                </div>
                <p className="research-entry-content">{entry.content}</p>
                <button
                  className="ghost"
                  type="button"
                  onClick={() => toggleEntry(entry.entry_id)}
                >
                  {openEntryId === entry.entry_id ? '收起细节' : '展开工具/引用'}
                </button>
                {openEntryId === entry.entry_id && (
                  <div className="research-entry-extra">
                    <div>
                      <p className="label">工具轨迹</p>
                      {entry.tool_traces?.length ? (
                        <pre className="code-block">
                          {JSON.stringify(entry.tool_traces, null, 2)}
                        </pre>
                      ) : (
                        <p className="subtle">暂无工具轨迹。</p>
                      )}
                    </div>
                    <div>
                      <p className="label">引用摘要</p>
                      {entry.sources?.length ? (
                        <pre className="code-block">
                          {JSON.stringify(entry.sources, null, 2)}
                        </pre>
                      ) : (
                        <p className="subtle">暂无引用摘要。</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="subtle">暂无条目，先追加第一条记录吧。</p>
        )}
      </div>
    </section>
  );
}
