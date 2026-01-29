const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}, sessionId) {
  const url = `${API_BASE_URL}${path}`;
  const headers = new Headers(options.headers || {});
  const trimmedSession = (sessionId || '').trim();
  if (trimmedSession) {
    headers.set('X-Session-Id', trimmedSession);
  }

  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const contentType = response.headers.get('content-type') || '';
  let payload = null;
  if (contentType.includes('application/json')) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : null;
    const message = detail || payload?.message || response.statusText;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

export function uploadDocument(file, sessionId) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/docs/upload', { method: 'POST', body: formData }, sessionId);
}

export function rebuildIndex(sessionId) {
  return request('/index/rebuild', { method: 'POST' }, sessionId);
}

export function chat(query, topK, sessionId) {
  return request(
    '/chat',
    {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    },
    sessionId,
  );
}

export function generateQuiz(payload, sessionId) {
  return request(
    '/quiz/generate',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    sessionId,
  );
}

export function submitQuiz(payload, sessionId) {
  return request(
    '/quiz/submit',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    sessionId,
  );
}

export function getProfile(sessionId) {
  return request('/profile/me', { method: 'GET' }, sessionId);
}

export function resolveSources(payload, sessionId) {
  return request(
    '/sources/resolve',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    sessionId,
  );
}

export function getRecentQuizzes(limit = 5, sessionId) {
  return request(
    '/quizzes/recent',
    {
      method: 'POST',
      body: JSON.stringify({ limit }),
    },
    sessionId,
  );
}

export function createResearch(payload, sessionId) {
  return request(
    '/research',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    sessionId,
  );
}

export function listResearch(sessionId) {
  return request('/research', { method: 'GET' }, sessionId);
}

export function getResearchDetail(researchId, sessionId) {
  return request(`/research/${researchId}`, { method: 'GET' }, sessionId);
}

export function appendResearchEntry(researchId, payload, sessionId) {
  return request(
    `/research/${researchId}/entries`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    sessionId,
  );
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}
