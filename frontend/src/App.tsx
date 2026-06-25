import "./App.css";

import { DiffInputPanel } from "./components/DiffInputPanel";
import { ReviewSummary } from "./components/ReviewSummary";
import { useReview } from "./hooks/useReview";

function App() {
  const { status, result, error, submit } = useReview();

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__heading">
          <h1 className="app__title">MR Review Council</h1>
          <span className="app__badge">MVP</span>
        </div>
        <p className="app__tagline">
          Multi-persona merge request review assistant
        </p>
      </header>

      <main className="app__main">
        <DiffInputPanel isLoading={status === "loading"} onRun={submit} />
        <ReviewSummary status={status} result={result} error={error} />
      </main>

      <footer className="app__footer">
        <span>Runs locally · Deterministic mock review engine · No AI yet</span>
      </footer>
    </div>
  );
}

export default App;
