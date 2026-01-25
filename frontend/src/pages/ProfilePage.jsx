import { useState } from 'react';
import { getProfile } from '../lib/api';

export default function ProfilePage({ sessionId }) {
  const [profile, setProfile] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  const handleLoad = async () => {
    setStatus('Loading profile...');
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
          <p className="eyebrow">Profile</p>
          <h1>Learning profile</h1>
          <p className="subtle">Ability level, frustration score, and weak concepts.</p>
        </div>
      </div>

      <div className="card">
        <button className="primary" type="button" onClick={handleLoad}>
          Load profile
        </button>
        <p className="status">{status}</p>
        {error && <p className="alert error">{error.message}</p>}
        {profile ? (
          <pre className="code-block">{JSON.stringify(profile, null, 2)}</pre>
        ) : (
          <p className="subtle">Click to fetch the profile.</p>
        )}
      </div>
    </section>
  );
}
