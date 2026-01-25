import { useState } from 'react';
import { uploadDocument } from '../lib/api';

export default function UploadPage({ sessionId, documentId, setDocumentId }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError(new Error('Please choose a file first.'));
      return;
    }
    setStatus('Uploading...');
    setError(null);
    setResponse(null);
    try {
      const result = await uploadDocument(file, sessionId);
      setResponse(result);
      if (result?.document_id) {
        setDocumentId(String(result.document_id));
      }
      setStatus('Upload complete.');
    } catch (err) {
      setError(err);
      setStatus('Upload failed.');
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Document</p>
          <h1>Upload a document</h1>
          <p className="subtle">Supported: PDF, Word, Markdown.</p>
        </div>
      </div>

      <div className="card">
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Choose file</span>
            <input
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <div className="inline">
            <button className="primary" type="submit">
              Upload
            </button>
            <span className="status">{status}</span>
          </div>
        </form>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Current document ID</h2>
          <div className="inline">
            <input
              className="input"
              value={documentId}
              onChange={(event) => setDocumentId(event.target.value)}
              placeholder="Document ID"
            />
            <span className="hint">Used by quiz generation.</span>
          </div>
        </div>
        <div className="card">
          <h2>Response</h2>
          {error && <p className="alert error">{error.message}</p>}
          {response ? (
            <pre className="code-block">{JSON.stringify(response, null, 2)}</pre>
          ) : (
            <p className="subtle">Upload a document to see the response.</p>
          )}
        </div>
      </div>
    </section>
  );
}
