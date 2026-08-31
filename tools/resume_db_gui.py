import argparse
import base64
import json
import os
import re
import sqlite3
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from build_resume_search_db import extract_text, normalize_text


DEFAULT_DB = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite"


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resume Search</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #64748b;
      --line: #d9e2ec;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --bad: #b91c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      letter-spacing: 0;
    }
    header {
      height: 72px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 0 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 {
      font-size: 22px;
      line-height: 1.2;
      margin: 0;
      font-weight: 650;
    }
    .stats {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
      color: var(--muted);
      font-size: 13px;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 6px 10px;
      background: #fbfcfe;
      white-space: nowrap;
    }
    main {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      min-height: calc(100vh - 72px);
    }
    aside {
      border-right: 1px solid var(--line);
      background: var(--panel);
      padding: 18px;
    }
    section {
      padding: 18px 22px 28px;
      min-width: 0;
    }
    label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin: 14px 0 6px;
      font-weight: 600;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 11px;
      font: inherit;
      background: #fff;
      color: var(--text);
    }
    textarea {
      min-height: 104px;
      resize: vertical;
    }
    .row {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    button {
      border: 0;
      border-radius: 8px;
      padding: 10px 12px;
      background: var(--accent);
      color: #fff;
      font-weight: 650;
      cursor: pointer;
      min-height: 40px;
    }
    button.secondary { background: var(--accent-2); }
    button.ghost {
      background: transparent;
      color: var(--accent-2);
      border: 1px solid var(--line);
    }
    button:disabled {
      opacity: .55;
      cursor: not-allowed;
    }
    .hint {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin-top: 10px;
    }
    .status {
      color: var(--muted);
      margin: 0 0 12px;
      font-size: 14px;
    }
    .result {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-bottom: 10px;
      padding: 13px 14px;
    }
    .result-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: start;
    }
    .title {
      font-weight: 650;
      overflow-wrap: anywhere;
    }
    .path {
      color: var(--muted);
      font-size: 12px;
      margin-top: 4px;
      overflow-wrap: anywhere;
    }
    .snippet {
      font-size: 14px;
      line-height: 1.45;
      margin-top: 10px;
      color: #334155;
    }
    .snippet b, .snippet mark {
      background: #fff2a8;
      padding: 0 2px;
      border-radius: 3px;
    }
    .tags {
      margin-top: 9px;
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .tag {
      font-size: 12px;
      color: #155e75;
      background: #ecfeff;
      border: 1px solid #bae6fd;
      border-radius: 999px;
      padding: 3px 8px;
    }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 24px;
      color: var(--muted);
      background: #fff;
    }
    .analysis {
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
    }
    .small {
      font-size: 12px;
      color: var(--muted);
    }
    @media (max-width: 850px) {
      header {
        height: auto;
        align-items: flex-start;
        flex-direction: column;
        padding: 18px;
      }
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <header>
    <h1>Resume Search</h1>
    <div class="stats" id="stats"></div>
  </header>
  <main>
    <aside>
      <label for="q">Search</label>
      <div class="row">
        <input id="q" placeholder="skills, name, company, title">
        <button id="searchBtn">Search</button>
      </div>
      <label for="mode">Search mode</label>
      <select id="mode">
        <option value="candidates" selected>Candidates</option>
        <option value="chunks">Best snippets</option>
        <option value="files">Whole files</option>
      </select>
      <label for="source">Source</label>
      <select id="source">
        <option value="all">All local indexes</option>
        <option value="resumes">Resumes</option>
        <option value="krisp">Krisp meetings</option>
        <option value="profiles">Public profiles</option>
      </select>
      <label for="limit">Results</label>
      <select id="limit">
        <option>10</option>
        <option selected>25</option>
        <option>50</option>
        <option>100</option>
      </select>
      <div class="hint">
        Use normal words like <strong>python engineer</strong>, exact phrases like
        <strong>"project manager"</strong>, or multiple skills. Results stay local.
      </div>

      <div class="analysis">
        <label for="jobFile">Job description</label>
        <input id="jobFile" type="file" accept=".pdf,.docx,.doc,.txt,.md,.rtf,.html,.htm">
        <label for="jobText">Or paste JD text</label>
        <textarea id="jobText" placeholder="Paste a job description or upload one above"></textarea>
        <button class="secondary" id="jobSearchBtn" style="margin-top:10px;width:100%;">Match Job</button>
        <div class="hint" id="jobStatus">Upload or paste a job description to search candidates and prepare public-source searches.</div>
      </div>

      <div class="analysis">
        <label for="llmPrompt">Local LLM prompt draft</label>
        <textarea id="llmPrompt" placeholder="Example: rank selected candidates for a senior embedded software role"></textarea>
        <label for="llmUrl">LM Studio endpoint</label>
        <input id="llmUrl" value="http://127.0.0.1:1234/v1">
        <label for="llmModel">Model name</label>
        <input id="llmModel" placeholder="leave blank to use first loaded model">
        <div class="row" style="margin-top:10px;">
          <button class="secondary" id="analyzeBtn">Analyze Selected</button>
          <button class="ghost" id="copyPromptBtn">Copy Context</button>
        </div>
        <div class="hint" id="llmStatus">LM Studio status not checked yet.</div>
        <div class="hint">
          Select search results, describe the role or question, then analyze locally through LM Studio.
        </div>
      </div>
    </aside>
    <section>
      <p class="status" id="status">Enter a search to begin.</p>
      <div class="result" id="analysisOutput" style="display:none;"></div>
      <div id="results"></div>
    </section>
  </main>
  <script>
    const q = document.getElementById('q');
    const mode = document.getElementById('mode');
    const source = document.getElementById('source');
    const limit = document.getElementById('limit');
    const status = document.getElementById('status');
    const results = document.getElementById('results');
    const selected = new Map();

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c]));
    }

    async function loadStats() {
      const res = await fetch('/api/stats');
      const data = await res.json();
      document.getElementById('stats').innerHTML = [
        `${data.candidates || 0} candidates`,
        `${data.files} files`,
        `${data.chunks} chunks`,
        `${data.krisp_documents || 0} Krisp meetings`,
        `${data.krisp_chunks || 0} Krisp chunks`,
        `${data.public_profile_notes || 0} profile notes`,
        `${data.ok_text} text-readable`,
        `${data.size_mb} MB`
      ].map(x => `<span class="stat">${escapeHtml(x)}</span>`).join('');
    }

    async function checkLlm() {
      const url = document.getElementById('llmUrl').value.trim();
      const res = await fetch('/api/llm/status?url=' + encodeURIComponent(url));
      const data = await res.json();
      const el = document.getElementById('llmStatus');
      if (data.ok) {
        el.textContent = `LM Studio connected. Loaded/available models: ${data.models.join(', ') || 'unknown'}`;
        if (!document.getElementById('llmModel').value && data.models.length) {
          document.getElementById('llmModel').value = data.models.includes('qwen/qwen3-8b') ? 'qwen/qwen3-8b' : data.models[0];
        }
      } else {
        el.textContent = data.error || 'LM Studio is not reachable yet.';
      }
    }

    async function runSearch() {
      const query = q.value.trim();
      if (!query) return;
      status.textContent = 'Searching...';
      results.innerHTML = '';
      const params = new URLSearchParams({
        q: query,
        mode: mode.value,
        source: source.value,
        limit: limit.value
      });
      const res = await fetch('/api/search?' + params.toString());
      const data = await res.json();
      if (!res.ok) {
        status.textContent = data.error || 'Search failed.';
        return;
      }
      status.textContent = `${data.results.length} result${data.results.length === 1 ? '' : 's'}`;
      if (!data.results.length) {
        results.innerHTML = '<div class="empty">No matches.</div>';
        return;
      }
      results.innerHTML = data.results.map(item => {
        const id = item.source_id || String(item.id);
        const checked = selected.has(id) ? 'checked' : '';
        const tags = (item.tags || '').split(',').filter(Boolean).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('');
        return `
          <article class="result" data-id="${escapeHtml(id)}">
            <div class="result-head">
              <div>
                <label class="small"><input type="checkbox" class="pick" data-id="${escapeHtml(id)}" ${checked}> include for LLM</label>
                <div class="title">${escapeHtml(item.filename)}</div>
                <div class="path">${escapeHtml(item.path)}</div>
              </div>
              <button class="ghost open" data-id="${escapeHtml(id)}">Open</button>
            </div>
            ${tags ? `<div class="tags">${tags}</div>` : ''}
            <div class="snippet">${item.snippet || ''}</div>
          </article>`;
      }).join('');
      for (const item of data.results) {
        const id = item.source_id || String(item.id);
        if (selected.has(id)) selected.set(id, item);
      }
    }

    function readFileAsBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const value = String(reader.result || '');
          resolve(value.includes(',') ? value.split(',')[1] : value);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    }

    async function runJobSearch() {
      const jobStatus = document.getElementById('jobStatus');
      const file = document.getElementById('jobFile').files[0];
      const pasted = document.getElementById('jobText').value.trim();
      if (!file && !pasted) {
        jobStatus.textContent = 'Upload or paste a job description first.';
        return;
      }
      jobStatus.textContent = 'Reading job description...';
      results.innerHTML = '';
      const payload = { text: pasted, limit: Number(limit.value || 25) };
      if (file) {
        payload.filename = file.name;
        payload.content_base64 = await readFileAsBase64(file);
      }
      const res = await fetch('/api/job/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        jobStatus.textContent = data.error || 'Job matching failed.';
        return;
      }
      q.value = data.query || q.value;
      mode.value = 'candidates';
      source.value = 'resumes';
      status.textContent = `${data.results.length} candidate match${data.results.length === 1 ? '' : 'es'} for the job description`;
      jobStatus.textContent = `${data.text_status}. Search terms: ${data.query || 'none'}`;
      const publicLinks = (data.public_searches || []).map(item =>
        `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.label)}</a>`
      ).join(' · ');
      const publicBlock = publicLinks ? `<div class="result"><div class="title">Public Source Searches</div><div class="snippet">${publicLinks}</div></div>` : '';
      results.innerHTML = publicBlock + data.results.map(item => {
        const id = item.source_id || String(item.id);
        const tags = (item.tags || '').split(',').filter(Boolean).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('');
        return `
          <article class="result" data-id="${escapeHtml(id)}">
            <div class="result-head">
              <div>
                <label class="small"><input type="checkbox" class="pick" data-id="${escapeHtml(id)}"> include for LLM</label>
                <div class="title">${escapeHtml(item.filename)}</div>
                <div class="path">${escapeHtml(item.path)}</div>
              </div>
              <button class="ghost open" data-id="${escapeHtml(id)}">Open</button>
            </div>
            ${tags ? `<div class="tags">${tags}</div>` : ''}
            <div class="snippet">${item.snippet || ''}</div>
          </article>`;
      }).join('');
    }

    results.addEventListener('change', event => {
      if (!event.target.classList.contains('pick')) return;
      const card = event.target.closest('.result');
      const id = event.target.dataset.id;
      if (event.target.checked) {
        selected.set(id, {
          id,
          filename: card.querySelector('.title').textContent,
          path: card.querySelector('.path').textContent,
          snippet: card.querySelector('.snippet').textContent
        });
      } else {
        selected.delete(id);
      }
    });

    results.addEventListener('click', async event => {
      if (!event.target.classList.contains('open')) return;
      const id = event.target.dataset.id;
      await fetch('/api/open?id=' + encodeURIComponent(id), { method: 'POST' });
    });

    document.getElementById('searchBtn').addEventListener('click', runSearch);
    document.getElementById('jobSearchBtn').addEventListener('click', runJobSearch);
    q.addEventListener('keydown', event => {
      if (event.key === 'Enter') runSearch();
    });

    document.getElementById('copyPromptBtn').addEventListener('click', async () => {
      const instruction = document.getElementById('llmPrompt').value.trim() || 'Analyze these resume search results.';
      const body = Array.from(selected.values()).map((item, i) =>
        `Candidate result ${i + 1}\nFile: ${item.filename}\nPath: ${item.path}\nSnippet: ${item.snippet}`
      ).join('\n\n');
      const text = `${instruction}\n\nUse only the local resume context below. Cite file paths when making claims.\n\n${body}`;
      await navigator.clipboard.writeText(text);
      status.textContent = `Copied ${selected.size} selected result${selected.size === 1 ? '' : 's'} for local LLM analysis.`;
    });

    document.getElementById('analyzeBtn').addEventListener('click', async () => {
      const output = document.getElementById('analysisOutput');
      if (!selected.size) {
        status.textContent = 'Select at least one result first.';
        return;
      }
      output.style.display = 'block';
      output.textContent = 'Analyzing locally...';
      const payload = {
        endpoint: document.getElementById('llmUrl').value.trim(),
        model: document.getElementById('llmModel').value.trim(),
        instruction: document.getElementById('llmPrompt').value.trim(),
        results: Array.from(selected.values())
      };
      const res = await fetch('/api/llm/analyze', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        output.textContent = data.error || 'Analysis failed.';
      } else {
        output.innerHTML = `<div class="title">Local LLM Analysis</div><div class="snippet">${escapeHtml(data.text).replace(/\n/g, '<br>')}</div>`;
      }
    });

    loadStats().catch(() => {});
    checkLlm().catch(() => {});
  </script>
</body>
</html>
"""


def fts_query(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if '"' in raw or " OR " in raw.upper() or " AND " in raw.upper() or "*" in raw:
        return raw
    terms = [term.replace('"', "") for term in raw.split() if term.strip()]
    return " AND ".join(f'"{term}"' for term in terms)


DOCUMENT_TYPE_NOISE_RE = re.compile(
    r"(?i)\b("
    r"employment\s+verification|reference\s+check|"
    r"job\s+description|position\s+description|role\s+description|"
    r"jd(?:\b|[-_ ]posting)|job\s+posting|"
    r"independent\s+contractor\s+agreement|contractor\s+agreement|"
    r"signed\s+agreement|new\s+agreement|employment\s+agreement|"
    r"offer\s+signed|signed\s+offer|offer\s+letter"
    r")\b"
)


def candidate_search_query(raw: str) -> str:
    cleaned = DOCUMENT_TYPE_NOISE_RE.sub(" ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


JOB_STOPWORDS = {
    "about",
    "across",
    "also",
    "and",
    "are",
    "based",
    "business",
    "candidate",
    "candidates",
    "company",
    "description",
    "develop",
    "development",
    "engineer",
    "engineering",
    "experience",
    "for",
    "from",
    "global",
    "have",
    "including",
    "job",
    "lead",
    "looking",
    "manager",
    "must",
    "our",
    "position",
    "product",
    "required",
    "requirements",
    "responsibilities",
    "role",
    "senior",
    "skills",
    "team",
    "technical",
    "technology",
    "that",
    "the",
    "this",
    "with",
    "work",
    "working",
    "years",
}

JD_SKILL_TERMS = [
    "aws",
    "azure",
    "gcp",
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node",
    "golang",
    "go",
    ".net",
    "c#",
    "c++",
    "sql",
    "postgres",
    "snowflake",
    "redshift",
    "databricks",
    "spark",
    "pyspark",
    "etl",
    "kafka",
    "rabbitmq",
    "mqtt",
    "iot",
    "iiot",
    "embedded",
    "firmware",
    "plc",
    "codesys",
    "security",
    "cybersecurity",
    "grc",
    "compliance",
    "architecture",
    "architect",
    "serverless",
    "lambda",
    "microservices",
    "docker",
    "kubernetes",
    "linux",
    "devops",
    "ci/cd",
    "api",
    "apis",
    "rest",
    "graphql",
    "erp",
    "plm",
    "infor",
    "sap",
    "salesforce",
    "cpq",
    "bom",
    "data",
    "analytics",
    "machine learning",
    "ml",
    "ai",
    "llm",
]


def derive_job_query(text: str, max_terms: int = 10) -> str:
    lower = text.lower()
    found: list[str] = []
    for term in JD_SKILL_TERMS:
        pattern = r"(?<![a-z0-9+#.])" + re.escape(term) + r"(?![a-z0-9+#.])"
        if re.search(pattern, lower):
            found.append(term)
    words = [
        word
        for word in re.findall(r"[a-z][a-z0-9+#.]{2,}", lower)
        if word not in JOB_STOPWORDS and not word.isdigit()
    ]
    for word, _count in Counter(words).most_common(80):
        if word not in found:
            found.append(word)
        if len(found) >= max_terms:
            break
    return " ".join(found[:max_terms])


def public_job_searches(query: str) -> list[dict[str, str]]:
    if not query:
        return []
    searches = [
        ("LinkedIn public", f'site:linkedin.com/in {query}'),
        ("GitHub", f'site:github.com {query}'),
        ("Stack Overflow", f'site:stackoverflow.com/users {query}'),
        ("Google Scholar", f'site:scholar.google.com {query}'),
        ("Portfolio sites", f'({query}) portfolio developer engineer'),
    ]
    return [
        {
            "label": label,
            "query": search,
            "url": "https://www.google.com/search?q=" + urllib.parse.quote_plus(search),
        }
        for label, search in searches
    ]


class ResumeSearchServer(BaseHTTPRequestHandler):
    db_path: Path

    def db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/stats":
            return self.handle_stats()
        if parsed.path == "/api/search":
            return self.handle_search(parsed)
        if parsed.path == "/api/llm/status":
            return self.handle_llm_status(parsed)
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/open":
            return self.handle_open(parsed)
        if parsed.path == "/api/llm/analyze":
            return self.handle_llm_analyze()
        if parsed.path == "/api/job/search":
            return self.handle_job_search()
        self.send_error(404)

    def handle_stats(self) -> None:
        with self.db() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS files,
                    ROUND(SUM(bytes) / 1048576.0, 2) AS size_mb,
                    SUM(CASE WHEN text_status = 'ok' THEN 1 ELSE 0 END) AS ok_text
                FROM files
                """
            ).fetchone()
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            has_krisp = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='krisp_documents'"
            ).fetchone()
            has_candidates = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='candidates'"
            ).fetchone()
            krisp_documents = 0
            krisp_chunks = 0
            candidates = 0
            if has_krisp:
                krisp_documents = conn.execute("SELECT COUNT(*) FROM krisp_documents").fetchone()[0]
                krisp_chunks = conn.execute("SELECT COUNT(*) FROM krisp_chunks").fetchone()[0]
            if has_candidates:
                candidates = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            public_profile_notes = conn.execute(
                "SELECT COUNT(*) FROM files WHERE lower(path) LIKE '%public profile notes%'"
            ).fetchone()[0]
        self.send_json(
            {
                "files": int(row["files"]),
                "size_mb": float(row["size_mb"] or 0),
                "ok_text": int(row["ok_text"] or 0),
                "chunks": int(chunks),
                "krisp_documents": int(krisp_documents),
                "krisp_chunks": int(krisp_chunks),
                "candidates": int(candidates),
                "public_profile_notes": int(public_profile_notes),
            }
        )

    def handle_search(self, parsed) -> None:
        params = urllib.parse.parse_qs(parsed.query)
        query = params.get("q", [""])[0]
        mode = params.get("mode", ["chunks"])[0]
        source = params.get("source", ["all"])[0]
        limit = min(max(int(params.get("limit", ["25"])[0]), 1), 100)
        effective_query = candidate_search_query(query) if mode == "candidates" and source in {"all", "resumes", "profiles"} else query
        match = fts_query(effective_query)
        if not match:
            return self.send_json({"results": [], "ignored_query": query})
        try:
            with self.db() as conn:
                rows = []
                if source == "profiles" and mode == "candidates":
                    rows = conn.execute(
                        """
                        SELECT 'candidate:' || candidates.id AS source_id,
                               'candidate' AS source,
                               candidates.id,
                               candidates.canonical_name AS filename,
                               files.path,
                               candidates.file_count || ' files' AS relative_path,
                               candidates.tags,
                               candidates.emails,
                               snippet(candidates_fts, 4, '<mark>', '</mark>', ' ... ', 38) AS snippet,
                               bm25(candidates_fts) AS rank
                        FROM candidates_fts
                        JOIN candidates ON candidates.id = candidates_fts.rowid
                        LEFT JOIN files ON files.id = candidates.best_file_id
                        WHERE candidates_fts MATCH ?
                          AND EXISTS (
                              SELECT 1
                              FROM candidate_files
                              JOIN files profile_files ON profile_files.id = candidate_files.file_id
                              WHERE candidate_files.candidate_id = candidates.id
                                AND lower(profile_files.path) LIKE '%public profile notes%'
                          )
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (match, limit),
                    ).fetchall()
                elif source == "profiles" and mode == "files":
                    rows = conn.execute(
                        """
                        SELECT 'resume:' || files.id AS source_id,
                               'profile' AS source,
                               files.id, files.filename, files.path, files.relative_path,
                               files.tags, files.emails,
                               snippet(files_fts, 3, '<mark>', '</mark>', ' ... ', 28) AS snippet,
                               bm25(files_fts) AS rank
                        FROM files_fts
                        JOIN files ON files.id = files_fts.rowid
                        WHERE files_fts MATCH ?
                          AND lower(files.path) LIKE '%public profile notes%'
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (match, limit),
                    ).fetchall()
                elif source == "profiles":
                    rows = conn.execute(
                        """
                        SELECT 'resume:' || files.id AS source_id,
                               'profile' AS source,
                               files.id, files.filename, files.path, files.relative_path,
                               files.tags, files.emails, chunks.chunk_index,
                               snippet(chunks_fts, 0, '<mark>', '</mark>', ' ... ', 38) AS snippet,
                               bm25(chunks_fts) AS rank
                        FROM chunks_fts
                        JOIN chunks ON chunks.id = chunks_fts.rowid
                        JOIN files ON files.id = chunks.file_id
                        WHERE chunks_fts MATCH ?
                          AND lower(files.path) LIKE '%public profile notes%'
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (match, limit),
                    ).fetchall()
                elif source in {"all", "resumes"} and mode == "candidates":
                    has_candidates = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='candidates'"
                    ).fetchone()
                    if has_candidates:
                        rows = conn.execute(
                            """
                            SELECT 'candidate:' || candidates.id AS source_id,
                                   'candidate' AS source,
                                   candidates.id,
                                   candidates.canonical_name AS filename,
                                   files.path,
                                   candidates.file_count || ' files' AS relative_path,
                                   candidates.tags,
                                   candidates.emails,
                                   snippet(candidates_fts, 4, '<mark>', '</mark>', ' ... ', 38) AS snippet,
                                   bm25(candidates_fts) AS rank
                            FROM candidates_fts
                            JOIN candidates ON candidates.id = candidates_fts.rowid
                            LEFT JOIN files ON files.id = candidates.best_file_id
                            WHERE candidates_fts MATCH ?
                            ORDER BY rank
                            LIMIT ?
                            """,
                            (match, limit),
                        ).fetchall()
                elif source in {"all", "resumes"} and mode == "files":
                    rows = conn.execute(
                        """
                        SELECT 'resume:' || files.id AS source_id,
                               'resume' AS source,
                               files.id, files.filename, files.path, files.relative_path,
                               files.tags, files.emails,
                               snippet(files_fts, 3, '<mark>', '</mark>', ' ... ', 28) AS snippet,
                               bm25(files_fts) AS rank
                        FROM files_fts
                        JOIN files ON files.id = files_fts.rowid
                        WHERE files_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (match, limit),
                    ).fetchall()
                elif source in {"all", "resumes"}:
                    rows = conn.execute(
                        """
                        SELECT 'resume:' || files.id AS source_id,
                               'resume' AS source,
                               files.id, files.filename, files.path, files.relative_path,
                               files.tags, files.emails, chunks.chunk_index,
                               snippet(chunks_fts, 0, '<mark>', '</mark>', ' ... ', 38) AS snippet,
                               bm25(chunks_fts) AS rank
                        FROM chunks_fts
                        JOIN chunks ON chunks.id = chunks_fts.rowid
                        JOIN files ON files.id = chunks.file_id
                        WHERE chunks_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (match, limit),
                    ).fetchall()
                results = [dict(row) for row in rows]
                if source in {"all", "krisp"}:
                    has_krisp = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='krisp_documents'"
                    ).fetchone()
                    if has_krisp:
                        krisp_limit = limit if source == "krisp" else max(1, limit - len(results))
                        if krisp_limit > 0:
                            if mode == "files":
                                krisp_rows = conn.execute(
                                    """
                                    SELECT 'krisp:' || krisp_documents.id AS source_id,
                                           'krisp' AS source,
                                           krisp_documents.id AS id,
                                           krisp_documents.title AS filename,
                                           krisp_documents.url AS path,
                                           krisp_documents.date AS relative_path,
                                           'krisp,meeting' AS tags,
                                           '' AS emails,
                                           snippet(krisp_documents_fts, 4, '<mark>', '</mark>', ' ... ', 28) AS snippet,
                                           bm25(krisp_documents_fts) AS rank
                                    FROM krisp_documents_fts
                                    JOIN krisp_documents ON krisp_documents.id = krisp_documents_fts.document_id
                                    WHERE krisp_documents_fts MATCH ?
                                    ORDER BY rank
                                    LIMIT ?
                                    """,
                                    (match, krisp_limit),
                                ).fetchall()
                            else:
                                krisp_rows = conn.execute(
                                    """
                                    SELECT 'krisp:' || krisp_documents.id AS source_id,
                                           'krisp' AS source,
                                           krisp_documents.id AS id,
                                           krisp_documents.title AS filename,
                                           krisp_documents.url AS path,
                                           krisp_documents.date AS relative_path,
                                           'krisp,meeting' AS tags,
                                           '' AS emails,
                                           krisp_chunks.chunk_index,
                                           snippet(krisp_chunks_fts, 0, '<mark>', '</mark>', ' ... ', 38) AS snippet,
                                           bm25(krisp_chunks_fts) AS rank
                                    FROM krisp_chunks_fts
                                    JOIN krisp_chunks ON krisp_chunks.id = krisp_chunks_fts.rowid
                                    JOIN krisp_documents ON krisp_documents.id = krisp_chunks.document_id
                                    WHERE krisp_chunks_fts MATCH ?
                                    ORDER BY rank
                                    LIMIT ?
                                    """,
                                    (match, krisp_limit),
                                ).fetchall()
                            results.extend(dict(row) for row in krisp_rows)
                results.sort(key=lambda item: item.get("rank", 0))
                self.send_json({"results": results[:limit]})
        except sqlite3.Error as exc:
            self.send_json({"error": f"Search failed: {exc}"}, 400)

    def handle_open(self, parsed) -> None:
        params = urllib.parse.parse_qs(parsed.query)
        raw_id = params.get("id", ["0"])[0]
        if raw_id.startswith("candidate:"):
            candidate_id = raw_id.removeprefix("candidate:")
            with self.db() as conn:
                row = conn.execute(
                    """
                    SELECT files.path
                    FROM candidates
                    JOIN files ON files.id = candidates.best_file_id
                    WHERE candidates.id = ?
                    """,
                    (candidate_id,),
                ).fetchone()
            if not row:
                return self.send_json({"error": "Candidate not found"}, 404)
            path = row["path"]
            if not os.path.exists(path):
                return self.send_json({"error": "Candidate file no longer exists"}, 404)
            os.startfile(path)
            return self.send_json({"ok": True})
        if raw_id.startswith("krisp:"):
            meeting_id = raw_id.removeprefix("krisp:")
            with self.db() as conn:
                row = conn.execute("SELECT url FROM krisp_documents WHERE id = ?", (meeting_id,)).fetchone()
            if not row:
                return self.send_json({"error": "Krisp meeting not found"}, 404)
            os.startfile(row["url"])
            return self.send_json({"ok": True})
        if raw_id.startswith("resume:"):
            raw_id = raw_id.removeprefix("resume:")
        try:
            file_id = int(raw_id)
        except ValueError:
            return self.send_json({"error": "Invalid file id"}, 400)
        with self.db() as conn:
            row = conn.execute("SELECT path FROM files WHERE id = ?", (file_id,)).fetchone()
        if not row:
            return self.send_json({"error": "File not found"}, 404)
        path = row["path"]
        if not os.path.exists(path):
            return self.send_json({"error": "File no longer exists"}, 404)
        os.startfile(path)
        self.send_json({"ok": True})

    def handle_llm_status(self, parsed) -> None:
        params = urllib.parse.parse_qs(parsed.query)
        endpoint = params.get("url", ["http://127.0.0.1:1234/v1"])[0].rstrip("/")
        try:
            req = urllib.request.Request(f"{endpoint}/models", headers={"Authorization": "Bearer lm-studio"})
            with urllib.request.urlopen(req, timeout=5) as res:
                payload = json.loads(res.read().decode("utf-8"))
            models = [item.get("id", "") for item in payload.get("data", []) if item.get("id")]
            self.send_json({"ok": True, "models": models})
        except Exception as exc:
            self.send_json({"ok": False, "error": f"LM Studio is not reachable at {endpoint}: {exc}"})

    def handle_job_search(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        filename = data.get("filename") or "pasted-job-description.txt"
        pasted_text = str(data.get("text") or "").strip()
        uploaded = data.get("content_base64") or ""
        limit = min(max(int(data.get("limit") or 25), 1), 100)
        extracted_status = "pasted text"
        extracted_error = ""
        extracted_text = ""

        if uploaded:
            suffix = Path(filename).suffix or ".txt"
            try:
                raw = base64.b64decode(uploaded)
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                    temp.write(raw)
                    temp_path = Path(temp.name)
                try:
                    extracted = extract_text(temp_path)
                    extracted_text = extracted.text
                    extracted_status = f"uploaded {filename}: {extracted.status}"
                    extracted_error = extracted.error
                finally:
                    temp_path.unlink(missing_ok=True)
            except Exception as exc:
                return self.send_json({"error": f"Could not read uploaded job description: {exc}"}, 400)

        job_text = normalize_text(" ".join(part for part in [pasted_text, extracted_text] if part))
        if len(job_text) < 20:
            message = extracted_error or "No readable job-description text was found."
            return self.send_json({"error": message}, 400)

        query = derive_job_query(job_text)
        query_terms = query.split()
        if not query_terms:
            return self.send_json({"error": "Could not derive enough useful search terms from the job description."}, 400)

        with self.db() as conn:
            has_candidates = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='candidates'"
            ).fetchone()
            if not has_candidates:
                return self.send_json({"error": "Candidate rollups have not been built yet."}, 400)
            rows = []
            used_query = query
            for term_count in range(len(query_terms), 1, -1):
                used_query = " ".join(query_terms[:term_count])
                match = fts_query(used_query)
                rows = conn.execute(
                    """
                    SELECT 'candidate:' || candidates.id AS source_id,
                           'candidate' AS source,
                           candidates.id,
                           candidates.canonical_name AS filename,
                           files.path,
                           candidates.file_count || ' files' AS relative_path,
                           candidates.tags,
                           candidates.emails,
                           snippet(candidates_fts, 4, '<mark>', '</mark>', ' ... ', 48) AS snippet,
                           bm25(candidates_fts) AS rank
                    FROM candidates_fts
                    JOIN candidates ON candidates.id = candidates_fts.rowid
                    LEFT JOIN files ON files.id = candidates.best_file_id
                    WHERE candidates_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (match, limit),
                ).fetchall()
                if len(rows) >= min(5, limit):
                    break

        self.send_json(
            {
                "filename": filename,
                "text_status": extracted_status,
                "text_error": extracted_error,
                "query": used_query,
                "full_query": query,
                "results": [dict(row) for row in rows],
                "public_searches": public_job_searches(used_query),
            }
        )

    def handle_llm_analyze(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        endpoint = (data.get("endpoint") or "http://127.0.0.1:1234/v1").rstrip("/")
        model = data.get("model") or ""
        instruction = data.get("instruction") or "Analyze these resume snippets for recruiting use."
        results = data.get("results") or []
        if not results:
            return self.send_json({"error": "No selected results were provided."}, 400)
        if not model:
            try:
                req = urllib.request.Request(f"{endpoint}/models", headers={"Authorization": "Bearer lm-studio"})
                with urllib.request.urlopen(req, timeout=5) as res:
                    payload = json.loads(res.read().decode("utf-8"))
                models = [item.get("id", "") for item in payload.get("data", []) if item.get("id")]
                model = "qwen/qwen3-8b" if "qwen/qwen3-8b" in models else (models[0] if models else "")
            except Exception:
                model = ""
        if not model:
            return self.send_json({"error": "No LM Studio model is loaded or available."}, 400)
        context = "\n\n".join(
            f"Result {i + 1}\nSource: {item.get('source', 'resume')}\nTitle: {item.get('filename')}\nPath or URL: {item.get('path')}\nSnippet: {item.get('snippet')}"
            for i, item in enumerate(results[:20])
        )
        prompt = (
            "/no_think\n"
            f"{instruction}\n\n"
            "Use only the local resume snippets below. Cite file paths when making claims. "
            "If the snippets are insufficient, say what is missing. "
            "Return the answer as plain text in the response content.\n\n"
            f"{context}"
        )
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a careful recruiting research assistant. Be concise, evidence-based, and cite file paths. Put the final answer in normal message content."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 900,
            "stream": False,
        }
        try:
            req = urllib.request.Request(
                f"{endpoint}/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer lm-studio",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as res:
                payload = json.loads(res.read().decode("utf-8"))
            message = payload["choices"][0].get("message", {})
            text = message.get("content") or message.get("reasoning_content") or ""
            if not text.strip():
                raise RuntimeError("LM Studio returned an empty response.")
            self.send_json({"ok": True, "model": model, "text": text})
        except Exception as exc:
            self.send_json({"error": f"LM Studio analysis failed: {exc}"}, 502)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    ResumeSearchServer.db_path = Path(args.db)
    server = ThreadingHTTPServer((args.host, args.port), ResumeSearchServer)
    print(f"Resume search GUI: http://{args.host}:{args.port}")
    print(f"Database: {ResumeSearchServer.db_path}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
