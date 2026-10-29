import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Repo = {
  id: string;
  name: string;
  root_path: string;
  indexed_commit?: string | null;
  file_count: number;
  symbol_count: number;
  status: string;
};
type SearchResult = { path: string; language: string; snippet: string; rank: number };
type Evidence = {
  path: string;
  language: string;
  start_line: number;
  end_line: number;
  snippet: string;
  sha256: string;
  indexed_commit?: string | null;
};

function App() {
  const [repos, setRepos] = React.useState<Repo[]>([]);
  const [path, setPath] = React.useState("");
  const [selected, setSelected] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [results, setResults] = React.useState<SearchResult[]>([]);
  const [evidence, setEvidence] = React.useState<Evidence[]>([]);
  const [answer, setAnswer] = React.useState("");
  const [message, setMessage] = React.useState("Connect to your local RepoPilot API.");
  const [busy, setBusy] = React.useState(false);

  async function refresh() {
    try {
      const response = await fetch("/api/repos");
      if (!response.ok) throw new Error("API unavailable");
      const data: Repo[] = await response.json();
      setRepos(data);
      if (!selected || !data.some((repo) => repo.id === selected)) {
        setSelected(data[0]?.id ?? "");
      }
      setMessage(data.length ? `${data.length} indexed repository(s)` : "No repositories indexed yet.");
    } catch {
      setMessage("API not reachable. Start the backend with: repopilot serve");
    }
  }
  React.useEffect(() => { void refresh(); }, []);

  function selectRepository(id: string) {
    setSelected(id);
    setResults([]);
    setEvidence([]);
    setAnswer("");
  }

  async function addRepo(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("Indexing repository…");
    try {
      const response = await fetch("/api/repos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not index repository");
      setSelected(data.id);
      setPath("");
      setResults([]);
      setEvidence([]);
      setAnswer("");
      const listResponse = await fetch("/api/repos");
      if (listResponse.ok) setRepos(await listResponse.json());
      setMessage(`Indexed ${data.file_count} files and ${data.symbol_count} Python symbols.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Index failed");
    } finally {
      setBusy(false);
    }
  }

  async function reindexRepository(repo: Repo) {
    setBusy(true);
    setMessage(`Re-indexing ${repo.name}…`);
    try {
      const response = await fetch(`/api/repos/${repo.id}/index`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Re-index failed");
      setRepos((current) => current.map((item) => item.id === repo.id ? { ...item, ...data } : item));
      const delta = data.index_delta;
      setMessage(
        `Re-indexed ${repo.name}: ${delta.added} added, ${delta.updated} updated, ${delta.removed} removed, ${delta.unchanged} unchanged.`,
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Re-index failed");
    } finally {
      setBusy(false);
    }
  }

  async function search(event: React.FormEvent) {
    event.preventDefault();
    if (!selected || !query.trim()) return;
    setBusy(true);
    setEvidence([]);
    setAnswer("");
    try {
      const response = await fetch(`/api/repos/${selected}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query, limit: 12 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Search failed");
      setResults(data.results);
      setMessage(`${data.result_count} result(s)`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    if (!selected || !query.trim()) return;
    setBusy(true);
    setResults([]);
    try {
      const response = await fetch(`/api/repos/${selected}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query, limit: 8 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Evidence retrieval failed");
      setAnswer(data.answer);
      setEvidence(data.evidence);
      setMessage(data.abstained ? "No verifiable evidence found" : `${data.evidence.length} evidence citation(s)`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Evidence retrieval failed");
    } finally {
      setBusy(false);
    }
  }

  return <main className="shell">
    <header>
      <div className="mark">RP</div>
      <div><p className="eyebrow">CODEBASE INTELLIGENCE</p><h1>RepoPilot</h1><p className="subtitle">Understand your repository. Follow the evidence.</p></div>
      <span className="local">LOCAL-FIRST</span>
    </header>
    <div className="status" role="status">{message}</div>
    <section className="panel">
      <div className="section-head"><div><p className="eyebrow">01 / ONBOARD</p><h2>Your repositories</h2></div><button onClick={() => void refresh()} disabled={busy}>Refresh</button></div>
      <form onSubmit={addRepo} className="inline-form">
        <input value={path} onChange={(event) => setPath(event.target.value)} placeholder="Absolute local repository path" required />
        <button disabled={busy}>{busy ? "Working…" : "Index repository"}</button>
      </form>
      <div className="repo-list">{repos.map((repo) => <div className="repo-row" key={repo.id}>
        <button className={`repo ${selected === repo.id ? "active" : ""}`} onClick={() => selectRepository(repo.id)}>
          <span className="repo-icon">⌘</span><span className="repo-name"><strong>{repo.name}</strong><small>{repo.root_path}</small></span><span className="count">{repo.file_count} files · {repo.symbol_count} symbols</span>
        </button>
        <button disabled={busy} onClick={() => void reindexRepository(repo)}>Re-index</button>
      </div>)}</div>
    </section>
    <section className="panel">
      <div className="section-head"><div><p className="eyebrow">02 / INVESTIGATE</p><h2>Search the codebase</h2></div><span className="pill">FTS5 SEARCH</span></div>
      <form onSubmit={search} className="inline-form">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Try a function name, error message, or identifier" required />
        <button disabled={busy || !selected}>Search</button>
      </form>
      <form onSubmit={ask} className="inline-form ask-form">
        <button disabled={busy || !selected || !query.trim()} type="submit">Retrieve evidence citations</button>
        <small>Evidence retrieval only; no LLM-generated explanation is claimed.</small>
      </form>
      {answer && <div className="status evidence-answer">{answer}</div>}
      <div className="results">
        {evidence.map((item, index) => <article className="result" key={`${item.path}-${item.start_line}-${index}`}>
          <div className="result-meta"><code>{item.path}:{item.start_line}-{item.end_line}</code><span>{item.language}</span></div>
          <pre>{item.snippet}</pre>
          <small>Commit: {item.indexed_commit ?? "unavailable"} · SHA-256: {item.sha256.slice(0, 16)}…</small>
        </article>)}
        {results.map((item, index) => <article className="result" key={`${item.path}-${index}`}>
          <div className="result-meta"><code>{item.path}</code><span>{item.language}</span></div><pre>{item.snippet}</pre>
        </article>)}
        {results.length === 0 && evidence.length === 0 && <div className="empty"><span>⌕</span><p>Search results and source evidence will appear here.</p><small>Index a local repository, then search or retrieve line-addressable evidence.</small></div>}
      </div>
    </section>
    <footer><span>RepoPilot · local MVP</span><span>Evidence first. No automatic code execution.</span><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">API docs ↗</a></footer>
  </main>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
