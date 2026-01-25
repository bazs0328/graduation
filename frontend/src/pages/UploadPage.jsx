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
      setError(new Error('请先选择文件。'));
      return;
    }
    setStatus('正在上传...');
    setError(null);
    setResponse(null);
    try {
      const result = await uploadDocument(file, sessionId);
      setResponse(result);
      if (result?.document_id) {
        setDocumentId(String(result.document_id));
      }
      setStatus('上传完成。');
    } catch (err) {
      setError(err);
      setStatus('上传失败。');
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">资料</p>
          <h1>上传资料</h1>
          <p className="subtle">支持格式：PDF / Word / Markdown。</p>
        </div>
      </div>

      <div className="card">
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>选择文件</span>
            <input
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <div className="inline">
            <button className="primary" type="submit">上传</button>
            <span className="status">{status}</span>
          </div>
        </form>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>当前文档 ID</h2>
          <div className="inline">
            <input
              className="input"
              value={documentId}
              onChange={(event) => setDocumentId(event.target.value)}
              placeholder="文档 ID"
            />
            <span className="hint">用于测验生成。</span>
          </div>
        </div>
        <div className="card">
          <h2>返回结果</h2>
          {error && <p className="alert error">{error.message}</p>}
          {response ? (
            <pre className="code-block">{JSON.stringify(response, null, 2)}</pre>
          ) : (
            <p className="subtle">上传后将在这里显示响应。</p>
          )}
        </div>
      </div>
    </section>
  );
}
