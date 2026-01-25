import { useState } from 'react';
import { chat } from '../lib/api';

export default function ChatPage({ sessionId }) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!query.trim()) {
      setError(new Error('请输入问题。'));
      return;
    }
    setStatus('正在思考...');
    setError(null);
    setAnswer(null);
    try {
      const result = await chat(query.trim(), Number(topK), sessionId);
      setAnswer(result);
      setStatus('');
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
                <p className="label">来源（原始）</p>
                <ul>
                  {answer.sources.map((source) => (
                    <li key={`${source.document_id}-${source.chunk_id}`}>
                      文档 {source.document_id} / 片段 {source.chunk_id} / 分数{' '}
                      {source.score}
                    </li>
                  ))}
                </ul>
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
