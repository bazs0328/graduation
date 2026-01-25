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
      setError(new Error('Please enter a question.'));
      return;
    }
    setStatus('Thinking...');
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
          <p className="eyebrow">Chat</p>
          <h1>Ask a question</h1>
          <p className="subtle">Answers are based on indexed chunks.</p>
        </div>
      </div>

      <div className="card">
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Question</span>
            <input
              className="input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask something from your documents"
            />
          </label>
          <label className="field">
            <span>Top K</span>
            <input
              className="input"
              type="number"
              min="1"
              value={topK}
              onChange={(event) => setTopK(event.target.value)}
            />
          </label>
          <button className="primary" type="submit">
            Send
          </button>
        </form>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
      </div>

      <div className="card">
        <h2>Answer</h2>
        {answer ? (
          <>
            <p className="answer">{answer.answer}</p>
            {answer.sources?.length ? (
              <div className="sources">
                <p className="label">Sources (raw)</p>
                <ul>
                  {answer.sources.map((source) => (
                    <li key={`${source.document_id}-${source.chunk_id}`}>
                      doc {source.document_id} / chunk {source.chunk_id} / score{' '}
                      {source.score}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="subtle">No sources returned.</p>
            )}
          </>
        ) : (
          <p className="subtle">Ask a question to see the response.</p>
        )}
      </div>
    </section>
  );
}
