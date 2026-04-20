function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function renderCards(container, items, builder, emptyMessage = "No data to show yet.") {
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = `<div class="card">${escapeHtml(emptyMessage)}</div>`;
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = builder(item);
    container.appendChild(card);
  });
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
}

function scoreWidth(score) {
  const normalized = Math.max(8, Math.min(Number(score || 0) * 9, 100));
  return `${normalized}%`;
}

function updateLastResponseMetrics({ citations = 0, safetyLabel = "waiting for query" } = {}) {
  setText("metric-citations", `${citations} citation${citations === 1 ? "" : "s"}`);
  setText("metric-safety", safetyLabel);
  setText("citation-count", `${citations} result${citations === 1 ? "" : "s"}`);
}

async function loadDocuments() {
  const payload = await fetchJson("/api/documents");
  renderCards(
    document.getElementById("documents"),
    payload.documents,
    (doc) => `
      <div class="card-row">
        <p class="card-title">${escapeHtml(doc.title)}</p>
        <span class="accent-chip teal">${escapeHtml(doc.category)}</span>
      </div>
      <p class="meta">${escapeHtml(doc.document_id)} · ${escapeHtml(doc.audience)}</p>
      <p class="snippet">${escapeHtml(doc.path)}</p>
    `,
    "No indexed documents are visible yet."
  );
}

async function loadHealth() {
  const payload = await fetchJson("/api/health");
  const banner = document.getElementById("status-banner");
  const note = payload.note ? ` ${payload.note}` : "";
  banner.textContent =
    `Requested mode: ${payload.requested_mode} · Active mode: ${payload.active_mode} · Documents: ${payload.document_count} · Chunks: ${payload.chunk_count}.${note}`;
  banner.classList.toggle("warning", payload.requested_mode !== payload.active_mode);

  setText("metric-active-mode", String(payload.active_mode || "unknown").toUpperCase());
  setText("metric-requested-mode", `requested ${payload.requested_mode || "unknown"}`);
  setText("metric-documents", `${payload.document_count} docs`);
  setText("metric-chunks", `${payload.chunk_count} chunks`);
}

async function askQuestion(question) {
  const payload = await fetchJson("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: 3 }),
  });

  const answerNode = document.getElementById("answer");
  answerNode.textContent = payload.safety_allowed
    ? payload.answer
    : `${payload.answer}\n\nReason: ${payload.safety_reason}`;

  const citations = payload.citations || [];
  renderCards(
    document.getElementById("citations"),
    citations,
    (citation) => `
      <div class="card-row">
        <p class="card-title">${escapeHtml(citation.title)}</p>
        <span class="accent-chip blue">${escapeHtml(citation.chunk_id)}</span>
      </div>
      <p class="snippet">${escapeHtml(citation.snippet)}</p>
    `,
    "Run a query to see supporting evidence here."
  );

  const searchPayload = await fetchJson(`/api/search?q=${encodeURIComponent(question)}&top_k=3`);
  const results = searchPayload.results || [];
  renderCards(
    document.getElementById("search-results"),
    results,
    (result) => `
      <div class="card-row">
        <p class="card-title">${escapeHtml(result.title)}</p>
        <span class="accent-chip orange">score ${escapeHtml(Number(result.score).toFixed(1))}</span>
      </div>
      <p class="meta">${escapeHtml(result.chunk_id)} · ${escapeHtml(result.heading)} · ${escapeHtml(result.category)}</p>
      <p class="snippet">${escapeHtml(result.snippet)}</p>
      <div class="score-track"><div class="score-bar" style="width:${scoreWidth(result.score)}"></div></div>
    `,
    "Search traces will appear after you ask a question."
  );

  setText("search-count", `${results.length} ranked chunk${results.length === 1 ? "" : "s"}`);
  updateLastResponseMetrics({
    citations: citations.length,
    safetyLabel: payload.safety_allowed ? "response allowed" : "blocked by safety policy",
  });
}

async function rebuildIndex() {
  const payload = await fetchJson("/api/index/rebuild", { method: "POST" });
  document.getElementById("answer").textContent =
    `Operation completed.\n\n${JSON.stringify(payload, null, 2)}`;
  await loadDocuments();
  await loadHealth();
  updateLastResponseMetrics({
    citations: 0,
    safetyLabel: payload.mode === "azure" ? "azure sync attempted" : "local index rebuilt",
  });
  setText("search-count", "0 ranked chunks");
  document.getElementById("citations").innerHTML = '<div class="card">Run a query to see supporting evidence here.</div>';
  document.getElementById("search-results").innerHTML = '<div class="card">Search traces will appear after you ask a question.</div>';
}

async function runQuestionFromInput() {
  const question = document.getElementById("question").value.trim();
  if (!question) {
    return;
  }
  await askQuestion(question);
}

document.getElementById("ask-button").addEventListener("click", runQuestionFromInput);

document.getElementById("hero-ask-button").addEventListener("click", async () => {
  const demoQuestion = "How do I pair the oven with Wi-Fi?";
  document.getElementById("question").value = demoQuestion;
  await askQuestion(demoQuestion);
});

document.getElementById("hero-sync-button").addEventListener("click", rebuildIndex);

document.getElementById("question").addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    await runQuestionFromInput();
  }
});

document.querySelectorAll(".chip").forEach((button) => {
  button.addEventListener("click", async () => {
    const question = button.textContent.trim();
    document.getElementById("question").value = question;
    await askQuestion(question);
  });
});

document.getElementById("rebuild-button").addEventListener("click", rebuildIndex);

updateLastResponseMetrics();
setText("search-count", "0 ranked chunks");
loadHealth();
loadDocuments();
