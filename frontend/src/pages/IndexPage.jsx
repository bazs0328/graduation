import { useState } from 'react';
import { rebuildIndex } from '../lib/api';

export default function IndexPage({ sessionId }) {
  const [status, setStatus] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleRebuild = async () => {
    setStatus('Rebuilding index...');
    setError(null);
    setResponse(null);
    try {
      const result = await rebuildIndex(sessionId);
      setResponse(result);
      setStatus('Index rebuilt.');
    } catch (err) {
      setError(err);
      setStatus('Index rebuild failed.');
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Index</p>
          <h1>Rebuild search index</h1>
          <p className="subtle">Required before chat and quiz generation.</p>
        </div>
      </div>

      <div className="card">
        <button className="primary" type="button" onClick={handleRebuild}>
          Rebuild index
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
