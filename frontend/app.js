/* -------------------------------------------------------
   Erasmus Help Desk – HTML + JS (no framework)
   Replica flusso: bando → mete → esami con Mock mode.
-------------------------------------------------------- */

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

// ------- Utils: API base resolution (query → window → localStorage → process → default)
function resolveApiBase() {
  // 1) from URL query
  try {
    const search = window.location.search || "";
    if (search.includes("api_base")) {
      const q = new URLSearchParams(search).get("api_base");
      if (q && q.trim()) return q.trim();
    }
  } catch {}
  // 2) from window
  try {
    const w = window;
    const candidate =
      w.__API_BASE__ ||
      w.ENV?.NEXT_PUBLIC_API_BASE ||
      w.__ENV__?.NEXT_PUBLIC_API_BASE;
    if (candidate && typeof candidate === "string" && candidate.trim()) return candidate.trim();
  } catch {}
  // 3) from localStorage
  try {
    const v = localStorage.getItem("api_base");
    if (v && v.trim()) return v.trim();
  } catch {}
  // 4) from process.env (guarded – browsers usually don't have this)
  try {
    // eslint-disable-next-line no-undef
    if (typeof process !== "undefined") {
      // eslint-disable-next-line no-undef
      const env = process?.env?.NEXT_PUBLIC_API_BASE;
      if (env && env.trim()) return env.trim();
    }
  } catch {}
  // 5) default
  return DEFAULT_API_BASE;
}

// ------- Mock payloads
const mockBando = {
  university_from: "Università di Pisa",
  status: "found",
  summary: {
    eligibility: "Requisiti CFU min 24, lingua EN/IT B2, finestre di candidatura trimestrali.",
    departments: ["Informatica", "AI & Data Eng.", "Telecomunicazioni"],
    periods: ["Fall", "Spring"],
    notes: "Equivalenza ECTS per esami a scelta e vincoli propedeuticità.",
  },
  citations: [
    { doc_id: "pisa_bando_2025.pdf", page: 3, url: "#" },
    { doc_id: "pisa_bando_2025.pdf", page: 7, url: "#" },
  ],
};

const mockShortlist = {
  items: [
    {
      id_university: "UPC-EETAC",
      id_city: "Barcelona",
      description:
        "Rete solida di corsi ML/Networks, insegnamento EN, corsi Spring/Fall, requisiti lingua EN B2.",
      citations: [{ doc_id: "upc_eetac_guide_2025.pdf", page: 12, url: "#" }],
    },
    {
      id_university: "TUM",
      id_city: "Munich",
      description: "Offerta avanzata DL/CV, progetti industry, lingua EN B2.",
      citations: [{ doc_id: "tum_catalog_2025.pdf", page: 5, url: "#" }],
    },
  ],
};

const mockExams = {
  download_pdf: "https://cdn.example.com/incoming/UPC-EETAC-exams-2025.pdf",
  incoming_exams_full: [
    { name: "Wireless Communications", ects: 6, semester: "Fall/Spring", lang: "EN" },
    { name: "Big Data and Data Mining", ects: 6, semester: "Spring", lang: "EN" },
  ],
  compatible_exams: [
    {
      name: "Big Data and Data Mining",
      reason: "Allineato a Data Mining del piano; prerequisiti soddisfatti.",
      citations: [{ doc_id: "upc_eetac_catalog.pdf", page: 9, url: "#" }],
    },
  ],
};

// ------- State (semplicissimo)
const state = {
  step: 1,
  apiBase: resolveApiBase(),
  useMock: false,
  loading: false,
  error: null,

  // form
  universityFrom: "",
  department: "",
  period: "Fall",
  studyPlanText: "",

  // results
  bando: null,
  shortlist: null,
  selectedMeta: null,
  exams: null,
};

// ------- DOM refs
const $ = (q) => document.querySelector(q);
const stepperEl = $("#stepper");
const bandoBox = $("#bando_box");
const shortlistBox = $("#shortlist_box");
const examsBox = $("#exams_box");
const errorBox = $("#error_box");
const spinner = $("#global_spinner");

// Header controls
const apiInput = $("#api_base");
const saveApiBtn = $("#save_api_btn");
const savedFlag = $("#saved_flag");
const mockCheckbox = $("#mock_mode");
const resetBtn = $("#reset_btn");

// Form controls
const univInput = $("#university");
const deptInput = $("#dept");
const periodSelect = $("#period");
const studyInput = $("#study");
const findBandoBtn = $("#find_bando_btn");
const shortlistBtn = $("#shortlist_btn");

// ------- Rendering
function renderStepper() {
  const items = [
    { n: 1, label: "Bando" },
    { n: 2, label: "Mete" },
    { n: 3, label: "Esami" },
  ];
  stepperEl.innerHTML = "";
  items.forEach((it, idx) => {
    const wrap = document.createElement("div");
    wrap.className = "item" + (state.step >= it.n ? " active" : "");
    wrap.innerHTML = `
      <div class="dot">${it.n}</div>
      <span class="label">${it.label}</span>
      ${idx < items.length - 1 ? '<div class="line"></div>' : ""}
    `;
    stepperEl.appendChild(wrap);
  });
}

function renderCitations(list) {
  if (!list || !list.length) return "";
  const links = list
    .map(
      (c, i) =>
        `<a href="${c.url || "#"}" target="_blank" rel="noreferrer" title="${(c.doc_id || "doc") + (c.page ? " – p." + c.page : "")}">
          ${c.doc_id || "Fonte " + (i + 1)}
        </a>`
    )
    .join("");
  return `<div class="citations"><span class="label">Fonti:</span> ${links}</div>`;
}

function renderBando() {
  if (!state.bando) {
    bandoBox.className = "text-muted";
    bandoBox.innerHTML = "Inserisci l'ateneo e clicca “Cerca bando”.";
    return;
  }
  if (state.bando.status === "not_found") {
    bandoBox.className = "";
    bandoBox.innerHTML = `<p class="label">Bando non presente nei documenti indicizzati.</p>${
      state.bando.message ? `<p class="text-muted">${state.bando.message}</p>` : ""
    }`;
    return;
  }
  const s = state.bando.summary || {};
  bandoBox.className = "";
  bandoBox.innerHTML = `
    <div class="space-y-xxs">
      <div><span class="label">Requisiti:</span> ${s.eligibility || "—"}</div>
      <div><span class="label">Dipartimenti:</span> ${(s.departments || []).join(", ") || "—"}</div>
      <div><span class="label">Periodi:</span> ${(s.periods || []).join(", ") || "—"}</div>
      <div><span class="label">Note:</span> ${s.notes || "—"}</div>
      ${renderCitations(state.bando.citations)}
    </div>
  `;
}

function renderShortlist() {
  if (!state.shortlist) {
    shortlistBox.className = "text-muted";
    shortlistBox.innerHTML = "Compila dipartimento/semestre/piano di studi e genera la shortlist.";
    return;
  }
  if (!state.shortlist.items || state.shortlist.items.length === 0) {
    shortlistBox.className = "";
    shortlistBox.textContent = "Nessuna meta trovata che rispetti i vincoli del bando.";
    return;
  }
  shortlistBox.className = "";
  shortlistBox.innerHTML = `
    <ul class="space-y">
      ${state.shortlist.items
        .map(
          (it) => `
        <li class="card" style="border-color:${state.selectedMeta?.id_university === it.id_university ? '#000' : 'var(--border)'}">
          <div style="display:flex; gap:12px; justify-content:space-between; align-items:flex-start;">
            <div>
              <div class="label">${it.id_university} – ${it.id_city}</div>
              <p class="text-muted" style="margin-top:4px">${it.description}</p>
              ${renderCitations(it.citations)}
            </div>
            <button class="btn" data-university="${it.id_university}">Vedi esami</button>
          </div>
        </li>`
        )
        .join("")}
    </ul>
  `;

  // wire buttons
  shortlistBox.querySelectorAll("button[data-university]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const uni = btn.getAttribute("data-university");
      const meta = state.shortlist.items.find((x) => x.id_university === uni);
      fetchExams(meta);
    });
  });
}

function renderExams() {
  if (!state.exams) {
    examsBox.className = "text-muted";
    examsBox.innerHTML = "Seleziona una meta per vedere gli esami.";
    return;
  }
  const ex = state.exams;
  examsBox.className = "";
  examsBox.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between;">
      <div>
        <div class="text-muted">Meta selezionata</div>
        <div class="card-title">${state.selectedMeta?.id_university} • ${state.selectedMeta?.id_city}</div>
      </div>
      <a href="${ex.download_pdf}" target="_blank" rel="noreferrer" class="linklike" style="text-decoration:underline;">
        Scarica elenco esami (PDF)
      </a>
    </div>

    <div style="margin-top:12px">
      <h3 class="card-title">Esami compatibili</h3>
      ${
        ex.compatible_exams?.length
          ? `<ul class="space-y" style="margin-top:8px">
              ${ex.compatible_exams
                .map(
                  (c) => `
                <li class="card">
                  <div class="label">${c.name}</div>
                  <p class="text-muted" style="margin-top:6px">${c.reason}</p>
                  ${renderCitations(c.citations)}
                </li>`
                )
                .join("")}
            </ul>`
          : `<p class="text-muted">Nessun esame trovato per il semestre selezionato. Mostro alternative del semestre opposto, se disponibili.</p>`
      }
    </div>

    <div style="margin-top:12px">
      <h3 class="card-title">Tutti gli esami (incoming)</h3>
      <div style="overflow:auto">
        <table class="table">
          <thead>
            <tr>
              <th>Nome</th><th>ECTS</th><th>Semestre</th><th>Lingua</th>
            </tr>
          </thead>
          <tbody>
            ${ex.incoming_exams_full
              .map(
                (e) => `
              <tr>
                <td>${e.name}</td><td>${e.ects}</td><td>${e.semester}</td><td>${e.lang}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderError() {
  if (state.error) {
    errorBox.hidden = false;
    errorBox.textContent = state.error;
  } else {
    errorBox.hidden = true;
    errorBox.textContent = "";
  }
}

function renderAll() {
  apiInput.value = state.apiBase;
  mockCheckbox.checked = state.useMock;
  univInput.value = state.universityFrom;
  deptInput.value = state.department;
  periodSelect.value = state.period;
  studyInput.value = state.studyPlanText;

  renderStepper();
  renderBando();
  renderShortlist();
  renderExams();
  renderError();

  spinner.hidden = !state.loading;
  findBandoBtn.disabled = state.loading || !state.universityFrom.trim();
  shortlistBtn.disabled = state.loading || !state.bando || state.bando.status !== "found" || !state.department.trim();
}

// ------- Actions
function setLoading(v) { state.loading = v; renderAll(); }
function setError(msg) { state.error = msg || null; renderAll(); }

function resetFromStep(n) {
  if (n <= 1) {
    state.bando = null; state.shortlist = null; state.selectedMeta = null; state.exams = null; state.step = 1;
  } else if (n === 2) {
    state.shortlist = null; state.selectedMeta = null; state.exams = null; state.step = 2;
  } else if (n === 3) {
    state.selectedMeta = null; state.exams = null; state.step = 3;
  }
  renderAll();
}

async function fetchBando() {
  setLoading(true); setError(null);
  try {
    let payload;
    if (state.useMock) {
      await new Promise((r) => setTimeout(r, 350));
      payload = mockBando;
    } else {
      const res = await fetch(`${state.apiBase}/bandi/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ university_from: state.universityFrom.trim() }),
      });
      if (!res.ok) throw new Error(`Errore ${res.status}`);
      payload = await res.json();
    }
    state.bando = payload;
    state.step = 1;
  } catch (e) {
    setError(e?.message || "Errore sconosciuto");
  } finally {
    setLoading(false);
  }
}

async function fetchShortlist() {
  setLoading(true); setError(null);
  try {
    let payload;
    if (state.useMock) {
      await new Promise((r) => setTimeout(r, 450));
      payload = mockShortlist;
    } else {
      const res = await fetch(`${state.apiBase}/mete/shortlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          university_from: state.universityFrom.trim(),
          department: state.department.trim(),
          study_plan_text: state.studyPlanText.trim(),
          period: state.period,
        }),
      });
      if (!res.ok) throw new Error(`Errore ${res.status}`);
      payload = await res.json();
    }
    state.shortlist = payload;
    state.step = 2;
  } catch (e) {
    setError(e?.message || "Errore sconosciuto");
  } finally {
    setLoading(false);
  }
}

async function fetchExams(meta) {
  setLoading(true); setError(null);
  try {
    let payload;
    if (state.useMock) {
      await new Promise((r) => setTimeout(r, 450));
      payload = mockExams;
    } else {
      const res = await fetch(`${state.apiBase}/mete/${encodeURIComponent(meta.id_university)}/exams`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ study_plan_text: state.studyPlanText.trim(), period: state.period }),
      });
      if (!res.ok) throw new Error(`Errore ${res.status}`);
      payload = await res.json();
    }
    state.selectedMeta = meta;
    state.exams = payload;
    state.step = 3;
  } catch (e) {
    setError(e?.message || "Errore sconosciuto");
  } finally {
    setLoading(false);
  }
}

// ------- Events & boot
function wireEvents() {
  apiInput.addEventListener("input", () => (state.apiBase = apiInput.value));
  saveApiBtn.addEventListener("click", () => {
    try {
      localStorage.setItem("api_base", state.apiBase || "");
      savedFlag.hidden = false;
      setTimeout(() => (savedFlag.hidden = true), 1500);
    } catch {}
  });

  mockCheckbox.addEventListener("change", () => {
    state.useMock = mockCheckbox.checked;
    renderAll();
  });

  resetBtn.addEventListener("click", () => resetFromStep(1));

  univInput.addEventListener("input", () => (state.universityFrom = univInput.value));
  deptInput.addEventListener("input", () => (state.department = deptInput.value));
  periodSelect.addEventListener("change", () => (state.period = periodSelect.value));
  studyInput.addEventListener("input", () => (state.studyPlanText = studyInput.value));

  findBandoBtn.addEventListener("click", () => fetchBando());
  shortlistBtn.addEventListener("click", () => fetchShortlist());
}

function init() {
  wireEvents();
  renderAll();
}

document.addEventListener("DOMContentLoaded", init);
