async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function renderCards(container, items, builder) {
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = '<div class="card">No data to show yet.</div>';
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = builder(item);
    container.appendChild(card);
  });
}

async function loadDocuments() {
  const payload = await fetchJson("/api/documents");
  renderCards(document.getElementById("documents"), payload.documents, (doc) => `
    <strong>${doc.title}</strong>
    <p class="meta">${doc.document_id} · ${doc.category} · ${doc.audience}</p>
    <p>${doc.path}</p>
  `);
}

async function loadHealth() {
  const payload = await fetchJson("/api/health");
  const banner = document.getElementById("status-banner");
  const note = payload.note ? ` ${payload.note}` : "";
  banner.textContent =
    `Requested mode: ${payload.requested_mode} · Active mode: ${payload.active_mode} · Documents: ${payload.document_count} · Chunks: ${payload.chunk_count}.${note}`;
  banner.classList.toggle("warning", payload.requested_mode !== payload.active_mode);
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

  renderCards(document.getElementById("citations"), payload.citations || [], (citation) => `
    <strong>${citation.title}</strong>
    <p class="meta">${citation.chunk_id}</p>
    <p>${citation.snippet}</p>
  `);

  const searchPayload = await fetchJson(`/api/search?q=${encodeURIComponent(question)}&top_k=3`);
  renderCards(document.getElementById("search-results"), searchPayload.results || [], (result) => `
    <strong>${result.title}</strong>
    <p class="meta">${result.chunk_id} · score ${result.score}</p>
    <p>${result.snippet}</p>
  `);
}

async function rebuildIndex() {
  const payload = await fetchJson("/api/index/rebuild", { method: "POST" });
  document.getElementById("answer").textContent =
    `Operation completed.\n${JSON.stringify(payload, null, 2)}`;
  await loadDocuments();
  await loadHealth();
}

document.getElementById("ask-button").addEventListener("click", async () => {
  const question = document.getElementById("question").value.trim();
  if (!question) {
    return;
  }
  await askQuestion(question);
});

document.getElementById("question").addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    document.getElementById("ask-button").click();
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

loadHealth();
loadDocuments();
