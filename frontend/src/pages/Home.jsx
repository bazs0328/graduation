export default function Home() {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Phase 3 Frontend MVP</p>
          <h1>Learning assistant frontend</h1>
          <p className="subtle">
            Use the tabs to upload a document, rebuild the index, ask questions,
            generate quizzes, and review your profile.
          </p>
        </div>
        <div className="badge">React + Vite</div>
      </div>
      <div className="grid-2">
        <div className="card">
          <h2>Quick start flow</h2>
          <ol className="steps">
            <li>Upload a document</li>
            <li>Rebuild the index</li>
            <li>Ask a question</li>
            <li>Generate and submit a quiz</li>
            <li>Check your profile</li>
          </ol>
        </div>
        <div className="card">
          <h2>What this MVP covers</h2>
          <ul className="list">
            <li>Upload → Index → Chat → Quiz → Profile</li>
            <li>Session-aware requests via X-Session-Id</li>
            <li>Minimal UI for end-to-end validation</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
