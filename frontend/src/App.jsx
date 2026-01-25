import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import './App.css';
import { getApiBaseUrl } from './lib/api';
import { usePersistedState } from './lib/storage';
import Home from './pages/Home';
import UploadPage from './pages/UploadPage';
import IndexPage from './pages/IndexPage';
import ChatPage from './pages/ChatPage';
import QuizPage from './pages/QuizPage';
import ProfilePage from './pages/ProfilePage';

const navItems = [
  { to: '/', label: 'Home' },
  { to: '/upload', label: 'Upload' },
  { to: '/index', label: 'Index' },
  { to: '/chat', label: 'Chat' },
  { to: '/quiz', label: 'Quiz' },
  { to: '/profile', label: 'Profile' },
];

function App() {
  const [sessionId, setSessionId] = usePersistedState('sessionId', 'default');
  const [documentId, setDocumentId] = usePersistedState('documentId', '');

  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">GT</div>
            <div>
              <p className="brand-title">Grad Tutor</p>
              <p className="brand-sub">Frontend MVP</p>
            </div>
          </div>
          <nav className="nav">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? 'nav-link active' : 'nav-link'
                }
                end={item.to === '/'}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="session">
            <label>
              <span>Session</span>
              <input
                className="input"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                placeholder="default"
              />
            </label>
            <p className="subtle">API: {getApiBaseUrl()}</p>
          </div>
        </header>

        <main className="container">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route
              path="/upload"
              element={
                <UploadPage
                  sessionId={sessionId}
                  documentId={documentId}
                  setDocumentId={setDocumentId}
                />
              }
            />
            <Route path="/index" element={<IndexPage sessionId={sessionId} />} />
            <Route path="/chat" element={<ChatPage sessionId={sessionId} />} />
            <Route
              path="/quiz"
              element={<QuizPage sessionId={sessionId} documentId={documentId} />}
            />
            <Route
              path="/profile"
              element={<ProfilePage sessionId={sessionId} />}
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
