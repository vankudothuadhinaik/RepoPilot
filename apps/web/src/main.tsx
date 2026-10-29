import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Repo = { id: string; name: string; root_path: string; indexed_commit?: string | null; file_count: number; symbol_count: number; status: string };
type SearchResult = { path: string; language: string; snippet: string; rank: number };

function App() {
  const [repos, setRepos] = React.useState<Repo[]>([]);
  const [path, setPath] = React.useState("");
  const [selected, setSelected] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [apiToken, setApiToken] = React.useState("");
  const [results, setResults] = React.useState<SearchResult[]>([]);
  const [message, setMessage] = React.useState("Connect to your local RepoPilot API.");
  const [busy, setBusy] = React.useState(false);
  const authHeaders = (): Record<string, string> => apiToken ? { Authorization: `Bearer ${apiToken}` } : {};

  async function refresh() {
    try {
      const response = await fetch("/api/repos", { headers: authHeaders() });
      if (!response.ok) throw new Error("API unavailable");
      const data: Repo[] = await response.json();
      setRepos(data);
      if (!selected && data[0]) setSelected(data[0].id);
      setMessage(data.length ? `${data.length} indexed repository(s)` : "No repositories indexed yet.");
    } catch {
      setMessage("API not reachable. Start the backend with: repopilot serve");
    }
  }
  React.useEffect(() => { void refresh(); }, []);

  async function addRepo(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("Indexing repository…");
    try {
      const response = await fetch("/api/repos", { method:"POST", headers:{"Content-Type":"application/json", ...authHeaders()}, body:JSON.stringify({path}) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not index repository");
      setSelected(data.id); setPath(""); await refresh(); setMessage(`Indexed ${data.file_count} files and ${data.symbol_count} Python symbols.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Index failed"); }
    finally { setBusy(false); }
  }

  async function search(event: React.FormEvent) {
    event.preventDefault();
    if (!selected || !query.trim()) return;
    setBusy(true);
    try {
      const response = await fetch(`/api/repos/${selected}/search`, { method:"POST", headers:{"Content-Type":"application/json", ...authHeaders()}, body:JSON.stringify({question:query,limit:12}) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Search failed");
      setResults(data.results); setMessage(`${data.result_count} result(s)`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Search failed"); }
    finally { setBusy(false); }
  }

  return <main className="shell">
    <header><div className="mark">RP</div><div><p className="eyebrow">CODEBASE INTELLIGENCE</p><h1>RepoPilot</h1><p className="subtitle">Understand your repository. Follow the evidence.</p></div><span className="local">LOCAL-FIRST</span></header>
    <div className="status">{message}</div>
    <section className="panel"><div className="section-head"><div><p className="eyebrow">AUTHENTICATION</p><h2>Local API token</h2></div></div><input type="password" value={apiToken} onChange={e=>setApiToken(e.target.value)} placeholder="Bearer token from Doppler" autoComplete="off" /></section>
    <section className="panel">
      <div className="section-head"><div><p className="eyebrow">01 / ONBOARD</p><h2>Your repositories</h2></div><button onClick={() => void refresh()}>Refresh</button></div>
      <form onSubmit={addRepo} className="inline-form"><input value={path} onChange={e=>setPath(e.target.value)} placeholder="Absolute local repository path" required /><button disabled={busy}>{busy ? "Working…" : "Index repository"}</button></form>
      <div className="repo-list">{repos.map(repo=><button className={`repo ${selected===repo.id?"active":""}`} key={repo.id} onClick={()=>setSelected(repo.id)}><span className="repo-icon">⌘</span><span className="repo-name"><strong>{repo.name}</strong><small>{repo.root_path}</small></span><span className="count">{repo.file_count} files · {repo.symbol_count} symbols</span></button>)}</div>
    </section>
    <section className="panel">
      <div className="section-head"><div><p className="eyebrow">02 / INVESTIGATE</p><h2>Search the codebase</h2></div><span className="pill">FTS5 SEARCH</span></div>
      <form onSubmit={search} className="inline-form"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Try a function name, error message, or identifier" required /><button disabled={busy || !selected}>Search</button></form>
      <div className="results">{results.map((item,i)=><article className="result" key={`${item.path}-${i}`}><div className="result-meta"><code>{item.path}</code><span>{item.language}</span></div><pre>{item.snippet}</pre></article>)}
      {results.length===0 && <div className="empty"><span>⌕</span><p>Search results and source evidence will appear here.</p><small>Start by indexing a local repository above.</small></div>}</div>
    </section>
    <footer><span>RepoPilot · early MVP</span><span>Evidence first. No automatic code execution.</span><a href="http://127.0.0.1:8010/docs" target="_blank" rel="noreferrer">API docs ↗</a></footer>
  </main>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
