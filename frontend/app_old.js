/* -------------------------------------------------------
   Erasmus Help Desk – HTML + JS (no framework)
   Replica flusso: bando → mete → esami con Mock mode.
   Modifiche:
   - Step 2: PDF del piano di studi OBBLIGATORIO per generare la shortlist
   - Invio a backend in multipart/form-data (con campo file `study_plan_pdf`)
   - Shortlist: link "Sito Erasmus" per ogni meta
-------------------------------------------------------- */

const DEFAULT_API_BASE = "http://127.0.0.1:8000/api/student";


const SESSION_KEYS = {
  UNIVERSITY_FROM: "EHD_university_from",
  SESSION_ID: "EHD_session_id",
};

function setSession(key, value) {
  try { sessionStorage.setItem(key, value ?? ""); } catch {}
}
function getSession(key) {
  try { return sessionStorage.getItem(key) || ""; } catch { return ""; }
}
function clearSession(key) {
  try { sessionStorage.removeItem(key); } catch {}
}


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
    if (typeof process !== "undefined") {
      const env = process?.env?.NEXT_PUBLIC_API_BASE;
      if (env && env.trim()) return env.trim();
    }
  } catch {}
  // 5) default
  return DEFAULT_API_BASE;
}

// ------- Mock payloads
const mockBando = {
  has_program: true,
  summary: "Requisiti CFU min 24, lingua EN/IT B2, finestre di candidatura trimestrali. Equivalenza ECTS per esami a scelta e vincoli propedeuticità.",
  session_id: "mock-session-" + Date.now(),
};

const mockShortlist = {
  destinations: [
    {
      name: "UNIVERSITAT POLITECNICA DE CATALUNYA",
      description: "Rete solida di corsi ML/Networks, insegnamento EN, corsi Spring/Fall, requisiti lingua EN B2.",
      codice_europeo: "E BARCELO03",
      posti: "2",
      durata_per_posto: "5",
      requisiti_linguistici: "EN B2",
    },
    {
      name: "TECHNICAL UNIVERSITY OF MUNICH",
      description: "Offerta avanzata DL/CV, progetti industry, lingua EN B2.",
      codice_europeo: "D MUNCHEN02",
      posti: "1",
      durata_per_posto: "6",
      requisiti_linguistici: "EN B2",
    },
  ],
};

const mockExams = {
  matched_exams: [
    {
      student_exam: "Algoritmi e Strutture Dati",
      destination_course: "Advanced Algorithms",
      compatibility: "alta",
      credits_student: "6 CFU",
      credits_destination: "6 ECTS",
      notes: "Ottima corrispondenza di contenuti",
    },
  ],
  suggested_exams: [
    {
      course_name: "Machine Learning",
      credits: "6 ECTS",
      reason: "Complementare al percorso di studi",
      category: "Computer Science",
    },
  ],
  compatibility_score: 85.0,
  analysis_summary: "Il piano di studi mostra una buona compatibilità con i corsi disponibili.",
  exams_pdf_url: "/api/student/files/exams/EETAC_Erasmus_Courses_2025-26.pdf",
  exams_pdf_filename: "EETAC_Erasmus_Courses_2025-26.pdf",
};

// ------- State (aggiunti campi file)
const state = {
  step: 1,
  apiBase: resolveApiBase(),
  useMock: false,
  loading: false,
  error: null,

  sessionId: null, // NUOVO: gestione session_id

  // form
  universityFrom: "",
  department: "",
  period: "Fall",
  studyPlanFile: null,
  studyPlanFileName: "",

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
// const studyInput = $("#study");
const findBandoBtn = $("#find_bando_btn");
const shortlistBtn = $("#shortlist_btn");
const studyPdfInput = $("#study_pdf");
const studyPdfNameEl = $("#study_pdf_name");
const studyPdfDropzone = $("#study_pdf_dropzone");
const selectPdfBtn = $("#select_pdf_btn");


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

function renderErasmusLink(item) {
  if (item.site_url) {
    return `<div style="margin-top:6px"><a class="linklike" href="${item.site_url}" target="_blank" rel="noopener">Sito Erasmus</a></div>`;
  }
  const q = encodeURIComponent(`Erasmus ${item.id_university || ""} ${item.id_city || ""}`.trim());
  return q
    ? `<div style="margin-top:6px"><a class="linklike text-muted" href="https://www.google.com/search?q=${q}" target="_blank" rel="noopener">Cerca info Erasmus</a></div>`
    : "";
}

function renderShortlist() {
  if (!state.shortlist) {
    shortlistBox.className = "text-muted";
    shortlistBox.innerHTML = "Carica il PDF del piano di studi, compila dipartimento/semestre e genera la shortlist.";
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
          <div style="display:flex; gap:12px; justify-content:space-between; align-items:flex-start; width:100%">
            <div>
              <div class="label">${it.id_university} – ${it.id_city}</div>
              <p class="text-muted" style="margin-top:4px">${it.description}</p>
              ${renderCitations(it.citations)}
              ${renderErasmusLink(it)}
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
  if (studyPdfNameEl) studyPdfNameEl.textContent = state.studyPlanFileName ? `Caricato: ${state.studyPlanFileName}` : "";

  // studyInput.value = state.studyPlanText;
  // if (studyPdfNameEl) studyPdfNameEl.textContent = state.studyPlanFileName ? `Caricato: ${state.studyPlanFileName}` : ""; // NEW

  renderStepper();
  renderBando();
  renderShortlist();
  renderExams();
  renderError();

  spinner.hidden = !state.loading;
  findBandoBtn.disabled = !!(state.loading || !state.universityFrom.trim());
  // NEW: richiede PDF oltre a bando found + department non vuoto
  shortlistBtn.disabled = !!(
    state.loading ||
    !state.bando ||
    state.bando.status !== "found" ||
    !state.department.trim() ||
    !state.period ||
    !state.studyPlanFile
  ); // PDF obbligatorio
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
      state.sessionId = payload.session_id;
    } else {
      const res = await fetch(`${state.apiBase}/step1`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ home_university: state.universityFrom.trim() }),
      });
      if (!res.ok) throw new Error(`Errore ${res.status}`);
      payload = await res.json();
      
      // Salva il session_id restituito dal backend
      state.sessionId = payload.session_id;
      setSession(SESSION_KEYS.SESSION_ID, payload.session_id);
    }
    state.bando = payload;
    // Persist university in session after a successful Step 1
    setSession(SESSION_KEYS.UNIVERSITY_FROM, state.universityFrom.trim());
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
      const fd = new FormData();
      fd.append("session_id", state.sessionId);
      fd.append("department", state.department.trim());
      fd.append("period", state.period);

      const res = await fetch(`${state.apiBase}/step2`, {
        method: "POST",
        body: fd,
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
      const fd = new FormData();
      fd.append("session_id", state.sessionId);
      fd.append("destination_university_name", meta.name);
      if (state.studyPlanFile) {
        fd.append("study_plan_file", state.studyPlanFile);
      }

      const res = await fetch(`${state.apiBase}/step3`, {
        method: "POST",
        body: fd,
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

function handlePdfFile(file) {
  if (!file) {
    state.studyPlanFile = null;
    state.studyPlanFileName = "";
    renderAll();
    return;
  }
  if (file.type !== "application/pdf") {
    alert("Per favore carica un file PDF valido.");
    return;
  }
  if (file.size > 10 * 1024 * 1024) { // 10 MB
    alert("Il PDF supera i 10 MB.");
    return;
  }
  state.studyPlanFile = file;
  state.studyPlanFileName = file.name;
  renderAll();
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

  resetBtn.addEventListener("click", () => { clearSession(SESSION_KEYS.UNIVERSITY_FROM); resetFromStep(1); });
  univInput.addEventListener("input", () => {
    state.universityFrom = univInput.value;
    setSession(SESSION_KEYS.UNIVERSITY_FROM, state.universityFrom.trim());
    renderAll();
  });
  deptInput.addEventListener("input", () => {
    state.department = deptInput.value;
    renderAll();
  });
  periodSelect.addEventListener("change", () => {
    state.period = periodSelect.value;
    renderAll();
  });
  // studyInput.addEventListener("input", () => {
  //   state.studyPlanText = studyInput.value;
  //   renderAll();
  // });

  // Gestione upload PDF obbligatorio
  if (studyPdfInput) {
    studyPdfInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      handlePdfFile(file);
    });
  }

  // Pulsante "Seleziona PDF" -> apre il file picker dell'input nascosto
  if (selectPdfBtn) {
    selectPdfBtn.addEventListener("click", () => studyPdfInput?.click());
  }

  // Dropzone: click e tastiera per accessibilità
  if (studyPdfDropzone) {
    studyPdfDropzone.addEventListener("click", () => studyPdfInput?.click());
    studyPdfDropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); studyPdfInput?.click(); }
    });

    // Evidenzia durante drag
    ["dragenter", "dragover"].forEach((ev) =>
      studyPdfDropzone.addEventListener(ev, (e) => {
        e.preventDefault(); e.stopPropagation();
        studyPdfDropzone.classList.add("dragover");
      })
    );
    ["dragleave", "dragend"].forEach((ev) =>
      studyPdfDropzone.addEventListener(ev, (e) => {
        e.preventDefault(); e.stopPropagation();
        studyPdfDropzone.classList.remove("dragover");
      })
    );

    // Drop del file
    studyPdfDropzone.addEventListener("drop", (e) => {
      e.preventDefault(); e.stopPropagation();
      studyPdfDropzone.classList.remove("dragover");
      const file = e.dataTransfer?.files?.[0];
      handlePdfFile(file);
    });
  }

  findBandoBtn.addEventListener("click", () => { if (findBandoBtn.disabled) return; fetchBando(); });
  shortlistBtn.addEventListener("click", () => {
    if (shortlistBtn.disabled) return;
    if (!state.studyPlanFile) {
      alert("Carica il PDF del piano di studi.");
      return;
    }
    fetchShortlist();
  });
}

function init() {
  // Prefill from session if present
  const savedUni = getSession(SESSION_KEYS.UNIVERSITY_FROM);
  if (savedUni && !state.universityFrom) state.universityFrom = savedUni;
  wireEvents();
  renderAll();
}

document.addEventListener("DOMContentLoaded", init);
