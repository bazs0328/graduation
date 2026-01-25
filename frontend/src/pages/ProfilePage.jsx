import { useState } from 'react';
import { getProfile } from '../lib/api';

export default function ProfilePage({ sessionId }) {
  const [profile, setProfile] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  const handleLoad = async () => {
    setStatus('正在加载画像...');
    setError(null);
    try {
      const result = await getProfile(sessionId);
      setProfile(result);
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
          <p className="eyebrow">画像</p>
          <h1>学习画像</h1>
          <p className="subtle">能力水平、挫败度、薄弱概念。</p>
        </div>
      </div>

      <div className="card">
        <button className="primary" type="button" onClick={handleLoad}>
          加载画像
        </button>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
        {profile ? (
          <pre className="code-block">{JSON.stringify(profile, null, 2)}</pre>
        ) : (
          <p className="subtle">点击按钮获取画像。</p>
        )}
      </div>
    </section>
  );
}
