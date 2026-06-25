import "./App.css";

const PERSONAS = [
  "Architect",
  "QA / Test",
  "Security",
  "Frontend",
  "Backend",
  "SRE / On-call",
  "Product / Maintainability",
] as const;

function App() {
  return (
    <div className="app">
      <header className="app__header">
        <span className="app__badge">MVP</span>
        <h1 className="app__title">MR Review Council</h1>
        <p className="app__tagline">
          A multi-persona AI reviewer for your merge requests. Get a diff
          reviewed through the eyes of an Architect, QA, Security engineer, and
          more — with a clear risk level and merge recommendation.
        </p>
      </header>

      <main className="app__main">
        <section className="panel">
          <h2 className="panel__title">Start a review</h2>
          <p className="panel__text">
            Paste a GitLab/GitHub diff or upload a <code>.diff</code> /
            <code>.patch</code> file, pick your reviewer personas, and get a
            structured review back.
          </p>
          <button
            type="button"
            className="button button--primary"
            disabled
            title="Coming soon"
          >
            Start Review
          </button>
          <p className="panel__hint">Review flow coming in the next step.</p>
        </section>

        <section className="panel">
          <h2 className="panel__title">Reviewer personas</h2>
          <ul className="persona-list">
            {PERSONAS.map((persona) => (
              <li key={persona} className="persona-list__item">
                {persona}
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="app__footer">
        <span>Runs locally · No AI integration yet</span>
      </footer>
    </div>
  );
}

export default App;
