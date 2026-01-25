import { useState } from 'react';
import { rebuildIndex } from '../lib/api';

export default function IndexPage({ sessionId }) {
  const [status, setStatus] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleRebuild = async () => {
    setStatus('正在重建索引...');
    setError(null);
    setResponse(null);
    try {
      const result = await rebuildIndex(sessionId);
      setResponse(result);
      setStatus('索引已重建。');
    } catch (err) {
      setError(err);
      setStatus('索引重建失败。');
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">索引</p>
          <h1>重建检索索引</h1>
          <p className="subtle">问答与测验前需要先完成索引。</p>
        </div>
      </div>

      <div className="card">
        <button className="primary" type="button" onClick={handleRebuild}>
          重建索引
        </button>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
        {response && (
          <pre className="code-block">{JSON.stringify(response, null, 2)}</pre>
        )}
      </div>
    </section>
  );
}
