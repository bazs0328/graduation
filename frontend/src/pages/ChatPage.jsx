import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { chat, resolveSources } from '../lib/api';

export default function ChatPage({ sessionId }) {
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [documentId, setDocumentId] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);
  const [sourceItems, setSourceItems] = useState([]);
  const [sourceStatus, setSourceStatus] = useState('');
  const [sourceError, setSourceError] = useState(null);
  const [showTools, setShowTools] = useState(false);
  const sessionReady = Boolean((sessionId || '').trim());

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const preset = params.get('q');
    const doc = params.get('doc');
    if (preset) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setQuery(preset);
    }
    if (doc && Number.isInteger(Number(doc))) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDocumentId(Number(doc));
    }
  }, [location.search]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!sessionReady) {
      setError(new Error('请先在顶部填写会话 ID。'));
      return;
    }
    if (!query.trim()) {
      setError(new Error('请输入问题。'));
      return;
    }
    setStatus('正在思考...');
    setError(null);
    setAnswer(null);
    setSourceItems([]);
    setSourceStatus('');
    setSourceError(null);
    setShowTools(false);
    try {
      const result = await chat(query.trim(), Number(topK), sessionId, documentId);
      setAnswer(result);
      setStatus('');
      const chunkIds = (result?.sources || [])
        .map((item) => item?.chunk_id)
        .filter((id) => Number.isInteger(id));
      if (chunkIds.length) {
        setSourceStatus('正在加载引用...');
        try {
          const resolved = await resolveSources({ chunk_ids: chunkIds }, sessionId);
          setSourceItems(resolved?.items || []);
          setSourceStatus('');
        } catch (err) {
          setSourceError(err);
          setSourceStatus('');
        }
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
          <p className="eyebrow">问答</p>
          <h1>提问</h1>
          <p className="subtle">回答基于索引的资料片段。</p>
        </div>
      </div>

      <div className="card">
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>问题</span>
            <input
              className="input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="请输入与资料相关的问题"
            />
          </label>
          <label className="field">
            <span>Top K（召回数）</span>
            <input
              className="input"
              type="number"
              min="1"
              value={topK}
              onChange={(event) => setTopK(event.target.value)}
            />
          </label>
          {documentId ? (
            <p className="subtle">当前资料：文档 {documentId}</p>
          ) : (
            <p className="subtle">当前为全库提问。</p>
          )}
          <button className="primary" type="submit">发送</button>
        </form>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
        {!sessionReady && (
          <p className="alert info">当前会话 ID 为空，请先填写再提问。</p>
        )}
      </div>

      <div className="card">
        <h2>回答</h2>
        {answer ? (
          <>
            {answer.structured?.conclusion ? (
              <div className="answer-structured">
                <div className="structured-section">
                  <p className="label">结论</p>
                  <p className="answer">{answer.structured.conclusion}</p>
                </div>
                <div className="structured-section">
                  <p className="label">证据</p>
                  {answer.structured.evidence?.length ? (
                    <ul className="list">
                      {answer.structured.evidence.map((item, index) => (
                        <li key={`${item.chunk_id}-${index}`}>
                          <span className="badge">片段 {item.chunk_id}</span>{' '}
                          {item.quote}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="subtle">暂无可用证据。</p>
                  )}
                </div>
                <div className="structured-section">
                  <p className="label">推理</p>
                  <p className="subtle">{answer.structured.reasoning || '暂无推理信息。'}</p>
                </div>
                <div className="structured-section">
                  <p className="label">下一步</p>
                  {answer.structured.next_steps?.length ? (
                    <ul className="list">
                      {answer.structured.next_steps.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="subtle">暂无建议。</p>
                  )}
                </div>
              </div>
            ) : (
              <p className="answer">{answer.answer}</p>
            )}
            {answer.retrieval && (
              <div className="retrieval-meta">
                <span className="badge">
                  检索模式：{answer.retrieval.mode === 'exact' ? '精确' : '语义'}
                </span>
                {answer.retrieval.reason && (
                  <span className="badge">原因：{answer.retrieval.reason}</span>
                )}
              </div>
            )}
            {answer.retrieval?.suggestions?.length ? (
              <div className="card soft-suggestions">
                <p className="label">改写建议</p>
                <ul className="list">
                  {answer.retrieval.suggestions.map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {answer.tool_traces?.length ? (
              <div className="tools">
                <div className="tool-header">
                  <p className="label">工具轨迹</p>
                  <button
                    className="ghost"
                    type="button"
                    onClick={() => setShowTools((prev) => !prev)}
                  >
                    {showTools ? '收起' : '展开'}
                  </button>
                </div>
                {showTools && (
                  <div className="tool-list">
                    {answer.tool_traces.map((trace, index) => (
                      <div className="tool-item" key={`${trace.tool_name}-${index}`}>
                        <div className="tool-meta">
                          <span className="badge">{trace.tool_name}</span>
                          {typeof trace.duration_ms === 'number' && (
                            <span className="badge">{trace.duration_ms}ms</span>
                          )}
                        </div>
                        <p className="tool-content">
                          输入：{JSON.stringify(trace.input ?? {})}
                        </p>
                        {trace.error ? (
                          <p className="alert error">错误：{trace.error}</p>
                        ) : (
                          <p className="tool-content">
                            输出：{trace.output ?? '无输出'}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
            {answer.sources?.length ? (
              <div className="sources">
                <p className="label">引用来源</p>
                {sourceStatus && <p className="hint">{sourceStatus}</p>}
                {sourceError && (
                  <p className="alert error">引用加载失败：{sourceError.message}</p>
                )}
                {sourceItems.length ? (
                  <div className="source-list">
                    {sourceItems.map((item) => (
                      <div className="source-item" key={item.chunk_id}>
                        <div className="source-meta">
                          <span className="badge">
                            {item.document_name
                              ? item.document_name
                              : `文档 ${item.document_id}`}
                          </span>
                          <span className="badge">片段 {item.chunk_id}</span>
                        </div>
                        <p className="source-preview">
                          {item.text_preview || '暂无摘要'}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="subtle">暂无引用可展示。</p>
                )}
              </div>
            ) : (
              <p className="subtle">暂无来源返回。</p>
            )}
          </>
        ) : (
          <p className="subtle">提交问题后将在这里显示回答。</p>
        )}
      </div>
    </section>
  );
}
