import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  deleteDocument,
  generateDocSummary,
  listDocumentChunks,
  listDocuments,
  rebuildIndex,
  uploadDocument,
} from '../lib/api';

export default function UploadPage({ sessionId, documentId, setDocumentId }) {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [docs, setDocs] = useState([]);
  const [docsTotal, setDocsTotal] = useState(0);
  const [docsStatus, setDocsStatus] = useState('');
  const [docsError, setDocsError] = useState(null);
  const [search, setSearch] = useState('');
  const [expandedDocId, setExpandedDocId] = useState(null);
  const [chunksByDoc, setChunksByDoc] = useState({});
  const [summaryByDoc, setSummaryByDoc] = useState({});
  const [rebuildStatus, setRebuildStatus] = useState('');
  const [rebuildError, setRebuildError] = useState(null);
  const [rebuildResponse, setRebuildResponse] = useState(null);

  const loadDocuments = useCallback(async () => {
    setDocsStatus('正在加载资料...');
    setDocsError(null);
    try {
      const result = await listDocuments(200, 0, sessionId);
      setDocs(result?.items || []);
      setDocsTotal(result?.total || 0);
      setDocsStatus('');
    } catch (err) {
      setDocsError(err);
      setDocsStatus('加载失败。');
    }
  }, [sessionId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const filteredDocs = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) {
      return docs;
    }
    return docs.filter((doc) => doc.filename.toLowerCase().includes(term));
  }, [docs, search]);

  const handleToggleChunks = async (docId) => {
    if (expandedDocId === docId) {
      setExpandedDocId(null);
      return;
    }
    setExpandedDocId(docId);
    const existing = chunksByDoc[docId];
    if (existing?.items?.length) {
      return;
    }
    setChunksByDoc((prev) => ({
      ...prev,
      [docId]: { items: [], total: 0, status: '正在加载片段...', error: null },
    }));
    try {
      const result = await listDocumentChunks(docId, 50, 0, sessionId);
      setChunksByDoc((prev) => ({
        ...prev,
        [docId]: {
          items: result?.items || [],
          total: result?.total || 0,
          status: '',
          error: null,
        },
      }));
    } catch (err) {
      setChunksByDoc((prev) => ({
        ...prev,
        [docId]: { items: [], total: 0, status: '加载失败。', error: err },
      }));
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`确认删除「${filename}」吗？删除后需重建索引。`)) {
      return;
    }
    try {
      await deleteDocument(docId, sessionId);
      setExpandedDocId(null);
      setSummaryByDoc((prev) => {
        const next = { ...prev };
        delete next[docId];
        return next;
      });
      await loadDocuments();
    } catch (err) {
      setDocsError(err);
    }
  };

  const handleRebuild = async () => {
    setRebuildStatus('正在重建索引...');
    setRebuildError(null);
    setRebuildResponse(null);
    try {
      const result = await rebuildIndex(sessionId);
      setRebuildResponse(result);
      setRebuildStatus('索引已重建。');
    } catch (err) {
      setRebuildError(err);
      setRebuildStatus('索引重建失败。');
    }
  };

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
      await loadDocuments();
      setStatus('上传完成。');
    } catch (err) {
      setError(err);
      setStatus('上传失败。');
    }
  };

  const handleGenerateSummary = async (docId, force = false) => {
    setSummaryByDoc((prev) => ({
      ...prev,
      [docId]: { ...(prev[docId] || {}), status: '正在生成摘要...', error: null },
    }));
    try {
      const result = await generateDocSummary(docId, force, sessionId);
      setSummaryByDoc((prev) => ({
        ...prev,
        [docId]: { ...result, status: '', error: null },
      }));
    } catch (err) {
      setSummaryByDoc((prev) => ({
        ...prev,
        [docId]: { ...(prev[docId] || {}), status: '生成失败。', error: err },
      }));
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">资料</p>
          <h1>资料管理</h1>
          <p className="subtle">上传、查看、删除资料，并一键重建索引。</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>上传新资料</h2>
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
          {error && <p className="alert error">{error.message}</p>}
          {response ? (
            <pre className="code-block">{JSON.stringify(response, null, 2)}</pre>
          ) : (
            <p className="subtle">上传后将显示文档 ID 与分片数量。</p>
          )}
        </div>
        <div className="card">
          <h2>索引管理</h2>
          <p className="subtle">
            上传、删除资料后请点击重建索引，问答/测验才会命中新内容。
          </p>
          <button className="primary" type="button" onClick={handleRebuild}>
            重建索引
          </button>
          <p className="status">{rebuildStatus}</p>
          {rebuildError && <p className="alert error">{rebuildError.message}</p>}
          {rebuildResponse && (
            <pre className="code-block">
              {JSON.stringify(rebuildResponse, null, 2)}
            </pre>
          )}
        </div>
      </div>

      <div className="card">
        <div className="inline spaced">
          <div>
            <h2>资料列表</h2>
            <p className="subtle">
              共 {docsTotal} 份资料，可搜索文件名并查看切分片段。
            </p>
          </div>
          <div className="inline">
            <input
              className="input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索文件名..."
            />
            <button className="ghost" type="button" onClick={loadDocuments}>
              刷新
            </button>
          </div>
        </div>

        <div className="doc-actions">
          <label className="field">
            <span>当前测验文档 ID</span>
            <input
              className="input"
              value={documentId}
              onChange={(event) => setDocumentId(event.target.value)}
              placeholder="文档 ID"
            />
          </label>
          <p className="hint">测验生成默认读取该文档。</p>
        </div>

        {docsError && <p className="alert error">{docsError.message}</p>}
        {docsStatus && <p className="status">{docsStatus}</p>}
        {filteredDocs.length === 0 ? (
          <p className="subtle">暂无资料，先上传一份试试。</p>
        ) : (
          <div className="doc-list">
            {filteredDocs.map((doc) => {
              const chunkState = chunksByDoc[doc.id];
              const isExpanded = expandedDocId === doc.id;
              return (
                <div key={doc.id} className="doc-item">
                  <div className="doc-main">
                    <div>
                      <p className="doc-title">{doc.filename}</p>
                      <p className="subtle">
                        ID {doc.id} · {doc.content_type || 'unknown'} · 分片 {doc.chunk_count}
                      </p>
                    </div>
                    <div className="inline">
                      <button
                        className="ghost"
                        type="button"
                        onClick={() => setDocumentId(String(doc.id))}
                      >
                        设为测验文档
                      </button>
                      <button
                        className="ghost"
                        type="button"
                        onClick={() => handleGenerateSummary(doc.id, Boolean(summaryByDoc[doc.id]?.summary))}
                      >
                        {summaryByDoc[doc.id]?.summary ? '重新生成摘要' : '生成摘要'}
                      </button>
                      <button
                        className="ghost"
                        type="button"
                        onClick={() => handleToggleChunks(doc.id)}
                      >
                        {isExpanded ? '收起片段' : '查看片段'}
                      </button>
                      <button
                        className="danger"
                        type="button"
                        onClick={() => handleDelete(doc.id, doc.filename)}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                  <div className="doc-summary">
                    {summaryByDoc[doc.id]?.status && (
                      <p className="status">{summaryByDoc[doc.id].status}</p>
                    )}
                    {summaryByDoc[doc.id]?.error && (
                      <p className="alert error">{summaryByDoc[doc.id].error.message}</p>
                    )}
                    {summaryByDoc[doc.id]?.summary ? (
                      <div className="summary-card">
                        <div className="summary-header">
                          <span className="badge">LLM 摘要</span>
                          {summaryByDoc[doc.id]?.cached && (
                            <span className="badge">缓存命中</span>
                          )}
                        </div>
                        <p className="summary-text">{summaryByDoc[doc.id].summary}</p>
                        <div className="summary-section">
                          <p className="label">关键词</p>
                          <div className="keyword-list">
                            {(summaryByDoc[doc.id].keywords || []).map((item, index) => (
                              <span className="badge" key={`${item}-${index}`}>
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="summary-section">
                          <p className="label">可问问题</p>
                          <div className="question-actions">
                            {(summaryByDoc[doc.id].questions || []).map((item, index) => (
                              <button
                                className="ghost"
                                type="button"
                                key={`${item}-${index}`}
                                onClick={() => navigate(`/chat?q=${encodeURIComponent(item)}`)}
                              >
                                {item}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <p className="subtle">可按需生成 LLM 摘要与问题建议。</p>
                    )}
                  </div>
                  {isExpanded && (
                    <div className="doc-chunks">
                      {chunkState?.status && (
                        <p className="status">{chunkState.status}</p>
                      )}
                      {chunkState?.error && (
                        <p className="alert error">{chunkState.error.message}</p>
                      )}
                      {chunkState?.items?.length ? (
                        <div className="chunk-list">
                          {chunkState.items.map((chunk) => (
                            <div key={chunk.id} className="chunk-item">
                              <div className="chunk-meta">
                                <span>片段 {chunk.chunk_index + 1}</span>
                                <span>
                                  {chunk.metadata?.start ?? 0} - {chunk.metadata?.end ?? 0}
                                </span>
                              </div>
                              <p className="chunk-text">{chunk.text}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="subtle">暂无片段数据。</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
