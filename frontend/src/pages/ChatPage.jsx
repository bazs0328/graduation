import { useState } from 'react';
import { chat, resolveSources } from '../lib/api';

export default function ChatPage({ sessionId }) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);
  const [sourceItems, setSourceItems] = useState([]);
  const [sourceStatus, setSourceStatus] = useState('');
  const [sourceError, setSourceError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
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
    try {
      const result = await chat(query.trim(), Number(topK), sessionId);
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
          <button className="primary" type="submit">发送</button>
        </form>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
      </div>

      <div className="card">
        <h2>回答</h2>
        {answer ? (
          <>
            <p className="answer">{answer.answer}</p>
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
