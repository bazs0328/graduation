export default function Home() {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Phase 3 前端 MVP</p>
          <h1>学习助理前端</h1>
          <p className="subtle">
            通过导航完成上传资料、重建索引、问答、生成测验并提交，
            最后查看学习画像。
          </p>
        </div>
        <div className="badge">React + Vite</div>
      </div>
      <div className="grid-2">
        <div className="card">
          <h2>快速流程</h2>
          <ol className="steps">
            <li>上传资料</li>
            <li>重建索引</li>
            <li>发起问答</li>
            <li>生成并提交测验</li>
            <li>查看画像</li>
          </ol>
        </div>
        <div className="card">
          <h2>本 MVP 覆盖</h2>
          <ul className="list">
            <li>上传 → 索引 → 问答 → 测验 → 画像</li>
            <li>通过 X-Session-Id 区分会话</li>
            <li>最小 UI 用于端到端验证</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
