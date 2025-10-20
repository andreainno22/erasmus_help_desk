/* -------------------------------------------------------
   Erasmus Help Desk – HTML + JS (no framework)
   Frontend adattato per backend FastAPI
   Step 1: Bando → Step 2: Destinazioni → Step 3: Esami
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

// ------- Utils: API base resolution
function resolveApiBase() {
  try {
    const search = window.location.search || "";
    if (search.includes("api_base")) {
      const q = new URLSearchParams(search).get("api_base");
      if (q && q.trim()) return q.trim();
    }
  } catch {}
  try {
    const v = localStorage.getItem("api_base");
    if (v && v.trim()) return v.trim();
  } catch {}
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
      description: "Eccellente programma in Computer Science con corsi in inglese, requisiti lingua EN B2.",
      codice_europeo: "E BARCELO03",
      posti: "2",
      durata_per_posto: "5",
      requisiti_linguistici: "EN B2",
    },
    {
      name: "TECHNICAL UNIVERSITY OF MUNICH",
      description: "Offerta avanzata in AI e Machine Learning, progetti industry, lingua EN B2.",
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
      notes: "Ottima corrispondenza di contenuti e prerequisiti",
    },
    {
      student_exam: "Basi di Dati",
      destination_course: "Database Systems",
      compatibility: "alta",
      credits_student: "9 CFU",
      credits_destination: "9 ECTS",
      notes: "Perfetta equivalenza",
    },
  ],
  suggested_exams: [
    {
      course_name: "Machine Learning",
      credits: "6 ECTS",
      reason: "Complementare al percorso di studi in informatica",
      category: "Computer Science",
    },
    {
      course_name: "Cloud Computing",
      credits: "6 ECTS",
      reason: "Competenza richiesta nel mercato del lavoro",
      category: "Distributed Systems",
    },
  ],
  compatibility_score: 85.0,
  analysis_summary: "Il piano di studi mostra un'ottima compatibilità con i corsi disponibili. Gli esami fondamentali trovano corrispondenza diretta.",
  exams_pdf_url: "/api/student/files/exams/EETAC_Erasmus_Courses_2025-26.pdf",
  exams_pdf_filename: "EETAC_Erasmus_Courses_2025-26.pdf",
};

// ------- State
const state = {
  step: 1,
  apiBase: resolveApiBase(),
  useMock: false,
  loading: false,
  error: null,

  sessionId: null, // Session ID dal backend

  // form
  universityFrom: "",
  department: "",
  period: "fall",
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
    { n: 2, label: "Destinazioni" },
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

function renderBando() {
  if (!state.bando) {
    bandoBox.className = "text-muted";
    bandoBox.innerHTML = "Inserisci l'ateneo e clicca 'Cerca bando'.";
    return;
  }
  if (!state.bando.has_program) {
    bandoBox.className = "";
    bandoBox.innerHTML = `<p class="label">❌ Bando non trovato per questa università.</p>`;
    return;
  }
  bandoBox.className = "";
  bandoBox.innerHTML = `
    <div class="space-y-xxs">
      <div class="label">✅ Bando trovato!</div>
      <p style="margin-top:8px">${state.bando.summary || "Nessun riassunto disponibile."}</p>
      ${state.useMock ? `<div class="text-muted" style="margin-top:8px; font-size:12px">Session ID: ${state.sessionId}</div>` : ''}
    </div>
  `;
}

function renderShortlist() {
  if (!state.shortlist) {
    shortlistBox.className = "text-muted";
    shortlistBox.innerHTML = "Completa il form (dipartimento, periodo, PDF piano studi) e genera la lista delle destinazioni.";
    return;
  }
  if (!state.shortlist.destinations || state.shortlist.destinations.length === 0) {
    shortlistBox.className = "";
    shortlistBox.textContent = "Nessuna destinazione trovata che rispetti i criteri.";
    return;
  }
  shortlistBox.className = "";
  shortlistBox.innerHTML = `
    <div class="label" style="margin-bottom:12px">
      ${state.shortlist.destinations.length} destinazione/i trovata/e
    </div>
    <ul class="space-y">
      ${state.shortlist.destinations
        .map(
          (dest) => `
        <li class="card" style="border-color:${state.selectedMeta?.name === dest.name ? '#007bff' : 'var(--border)'}">
          <div style="display:flex; gap:12px; justify-content:space-between; align-items:flex-start">
            <div style="flex:1">
              <div class="label">${dest.name}</div>
              ${dest.codice_europeo ? `<div class="text-muted" style="font-size:12px">Codice: ${dest.codice_europeo}</div>` : ''}
              <p class="text-muted" style="margin-top:6px">${dest.description || ''}</p>
              <div style="margin-top:8px; font-size:13px">
                ${dest.posti ? `<span>📍 Posti: ${dest.posti}</span> • ` : ''}
                ${dest.durata_per_posto ? `<span>⏱️ Durata: ${dest.durata_per_posto} mesi</span> • ` : ''}
                ${dest.requisiti_linguistici ? `<span>🗣️ ${dest.requisiti_linguistici}</span>` : ''}
              </div>
            </div>
            <button class="btn" data-university-name="${dest.name}">Vedi esami</button>
          </div>
        </li>`
        )
        .join("")}
    </ul>
  `;

  // Wire buttons
  shortlistBox.querySelectorAll("button[data-university-name]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.getAttribute("data-university-name");
      const meta = state.shortlist.destinations.find((x) => x.name === name);
      if (meta) fetchExams(meta);
    });
  });
}

function renderExams() {
  if (!state.exams) {
    examsBox.className = "text-muted";
    examsBox.innerHTML = "Seleziona una destinazione per vedere l'analisi degli esami.";
    return;
  }
  const ex = state.exams;
  examsBox.className = "";
  examsBox.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px">
      <div>
        <div class="text-muted" style="font-size:12px">Destinazione selezionata</div>
        <div class="card-title">${state.selectedMeta?.name || 'N/A'}</div>
      </div>
      ${ex.exams_pdf_url ? `
        <a href="${state.apiBase.replace('/api/student', '')}${ex.exams_pdf_url}" 
           target="_blank" 
           rel="noreferrer" 
           class="btn"
           style="text-decoration:none">
          📄 Scarica PDF completo
        </a>
      ` : ''}
    </div>

    <!-- Punteggio di compatibilità -->
    <div class="card" style="background:#f0f9ff; border-color:#0891b2; margin-bottom:16px">
      <div style="display:flex; align-items:center; gap:12px">
        <div style="font-size:32px; font-weight:bold; color:#0891b2">
          ${ex.compatibility_score || 0}%
        </div>
        <div>
          <div class="label">Punteggio di compatibilità</div>
          <p class="text-muted" style="margin-top:4px">${ex.analysis_summary || ''}</p>
        </div>
      </div>
    </div>

    <!-- Esami con corrispondenza -->
    <div style="margin-bottom:20px">
      <h3 class="card-title">🎯 Esami con corrispondenza (${ex.matched_exams?.length || 0})</h3>
      ${
        ex.matched_exams && ex.matched_exams.length > 0
          ? `<ul class="space-y" style="margin-top:8px">
              ${ex.matched_exams
                .map(
                  (match) => {
                    // Determine colors based on compatibility level
                    let bgColor, textColor, arrowColor;
                    const compat = (match.compatibility || '').toLowerCase();
                    
                    if (compat === 'alta' || compat === 'high') {
                      bgColor = '#d1fae5';  // light green
                      textColor = '#065f46'; // dark green
                      arrowColor = '#059669'; // green
                    } else if (compat === 'media' || compat === 'medium') {
                      bgColor = '#fef3c7';  // light yellow
                      textColor = '#92400e'; // dark yellow/brown
                      arrowColor = '#d97706'; // orange/yellow
                    } else if (compat === 'bassa' || compat === 'low') {
                      bgColor = '#fee2e2';  // light red
                      textColor = '#991b1b'; // dark red
                      arrowColor = '#dc2626'; // red
                    } else {
                      // Default colors for unknown compatibility
                      bgColor = '#f3f4f6';
                      textColor = '#374151';
                      arrowColor = '#6b7280';
                    }
                    
                    return `
                <li class="card">
                  <div style="display:flex; justify-content:space-between; align-items:start; gap:12px">
                    <div style="flex:1">
                      <div class="label">${match.student_exam}</div>
                      <div style="margin:6px 0; color:${arrowColor}">
                        ↓ <strong>${match.destination_course}</strong>
                      </div>
                      <div class="text-muted" style="font-size:13px">
                        ${match.credits_student} → ${match.credits_destination}
                      </div>
                      ${match.notes ? `<p class="text-muted" style="margin-top:6px; font-size:13px">${match.notes}</p>` : ''}
                    </div>
                    <div style="padding:4px 12px; background:${bgColor}; color:${textColor}; border-radius:4px; font-size:12px; font-weight:600">
                      ${match.compatibility || 'N/A'}
                    </div>
                  </div>
                </li>`;
                  }
                )
                .join("")}
            </ul>`
          : `<p class="text-muted" style="margin-top:8px">Nessuna corrispondenza diretta trovata.</p>`
      }
    </div>

    <!-- Esami suggeriti -->
    ${ex.suggested_exams && ex.suggested_exams.length > 0 ? `
    <div>
      <h3 class="card-title">💡 Esami suggeriti (${ex.suggested_exams.length})</h3>
      <ul class="space-y" style="margin-top:8px">
        ${ex.suggested_exams
          .map(
            (sugg) => `
          <li class="card" style="background:#fefce8; border-color:#facc15">
            <div class="label">${sugg.course_name}</div>
            <div class="text-muted" style="font-size:13px; margin-top:4px">
              ${sugg.credits} • ${sugg.category || 'Varie'}
            </div>
            <p class="text-muted" style="margin-top:6px; font-size:13px">${sugg.reason || ''}</p>
          </li>`
          )
          .join("")}
      </ul>
    </div>
    ` : ''}
  `;
}

function renderError() {
  if (state.error) {
    errorBox.hidden = false;
    errorBox.textContent = "⚠️ " + state.error;
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
  if (studyPdfNameEl) {
    studyPdfNameEl.textContent = state.studyPlanFileName 
      ? `✅ ${state.studyPlanFileName}` 
      : "Nessun file selezionato";
  }

  renderStepper();
  renderBando();
  renderShortlist();
  renderExams();
  renderError();

  spinner.hidden = !state.loading;
  findBandoBtn.disabled = !!(state.loading || !state.universityFrom.trim());
  
  // Abilita shortlist solo se: bando trovato + dipartimento + periodo
  shortlistBtn.disabled = !!(
    state.loading ||
    !state.bando ||
    !state.bando.has_program ||
    !state.department.trim() ||
    !state.period
  );
}

// ------- Actions
function setLoading(v) { 
  state.loading = v; 
  renderAll(); 
}

function setError(msg) { 
  state.error = msg || null; 
  renderAll(); 
}

function resetFromStep(n) {
  if (n <= 1) {
    state.bando = null;
    state.shortlist = null;
    state.selectedMeta = null;
    state.exams = null;
    state.sessionId = null;
    state.step = 1;
  } else if (n === 2) {
    state.shortlist = null;
    state.selectedMeta = null;
    state.exams = null;
    state.step = 2;
  } else if (n === 3) {
    state.selectedMeta = null;
    state.exams = null;
    state.step = 3;
  }
  renderAll();
}

// ------- API Calls
async function loadUniversities() {
  try {
    const res = await fetch(`${state.apiBase}/universities`, {
      method: "GET",
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `Errore ${res.status}`);
    }
    const universities = await res.json();
    
    // Popola il select con le università
    univInput.innerHTML = '<option value="">-- Seleziona un\'università --</option>';
    if (universities && universities.length > 0) {
      universities.forEach(uni => {
        const option = document.createElement('option');
        option.value = uni;
        option.textContent = uni;
        univInput.appendChild(option);
      });
    }
  } catch (err) {
    console.error(`Errore nel caricamento delle università: ${err.message}`);
    // Mantieni l'opzione di default se c'è un errore
  }
}

async function loadDepartments() {
  if (!state.sessionId) {
    console.warn("Session ID non disponibile, impossibile caricare i dipartimenti");
    deptInput.innerHTML = '<option value="">-- Seleziona prima un\'università --</option>';
    deptInput.disabled = true;
    return;
  }

  try {
    const res = await fetch(`${state.apiBase}/departments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId }),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `Errore ${res.status}`);
    }
    const data = await res.json();
    
    // Popola il select con i dipartimenti
    deptInput.innerHTML = '<option value="">-- Seleziona un dipartimento --</option>';
    deptInput.disabled = false;
    
    if (data.departments && data.departments.length > 0) {
      data.departments.forEach(dept => {
        const option = document.createElement('option');
        option.value = dept;
        option.textContent = dept;
        deptInput.appendChild(option);
      });
    }
  } catch (err) {
    console.error(`Errore nel caricamento dei dipartimenti: ${err.message}`);
    deptInput.innerHTML = '<option value="">-- Errore caricamento dipartimenti --</option>';
    deptInput.disabled = true;
  }
}

async function fetchBando() {
  setLoading(true);
  setError(null);
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
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Errore ${res.status}`);
      }
      payload = await res.json();
      
      // Salva session_id
      state.sessionId = payload.session_id;
      setSession(SESSION_KEYS.SESSION_ID, payload.session_id);
    }
    
    state.bando = payload;
    setSession(SESSION_KEYS.UNIVERSITY_FROM, state.universityFrom.trim());
    state.step = 1;
    
    // Carica i dipartimenti disponibili dopo aver ottenuto il session_id
    await loadDepartments();
  } catch (e) {
    setError(e?.message || "Errore sconosciuto");
  } finally {
    setLoading(false);
  }
}

async function fetchShortlist() {
  setLoading(true);
  setError(null);
  try {
    let payload;
    if (state.useMock) {
      await new Promise((r) => setTimeout(r, 450));
      payload = mockShortlist;
    } else {
      if (!state.sessionId) {
        throw new Error("Session ID mancante. Rifare lo Step 1.");
      }

      const res = await fetch(`${state.apiBase}/step2`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          department: state.department.trim(),
          period: state.period
        }),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Errore ${res.status}`);
      }
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
  setLoading(true);
  setError(null);
  try {
    let payload;
    if (state.useMock) {
      await new Promise((r) => setTimeout(r, 450));
      payload = mockExams;
    } else {
      if (!state.sessionId) {
        throw new Error("Session ID mancante. Rifare lo Step 1.");
      }
      if (!state.studyPlanFile) {
        throw new Error("File PDF del piano di studi mancante.");
      }

      const fd = new FormData();
      fd.append("session_id", state.sessionId);
      fd.append("destination_university_name", meta.name);
      fd.append("study_plan_file", state.studyPlanFile);

      const res = await fetch(`${state.apiBase}/step3`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Errore ${res.status}`);
      }
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
  if (file.size > 10 * 1024 * 1024) {
    alert("Il PDF supera i 10 MB.");
    return;
  }
  state.studyPlanFile = file;
  state.studyPlanFileName = file.name;
  renderAll();
}

// ------- Events & boot
function wireEvents() {
  // API base
  apiInput.addEventListener("input", () => (state.apiBase = apiInput.value));
  saveApiBtn.addEventListener("click", () => {
    try {
      localStorage.setItem("api_base", state.apiBase || "");
      savedFlag.hidden = false;
      setTimeout(() => (savedFlag.hidden = true), 1500);
    } catch {}
  });

  // Mock mode
  mockCheckbox.addEventListener("change", () => {
    state.useMock = mockCheckbox.checked;
    renderAll();
  });

  // Reset
  resetBtn.addEventListener("click", () => {
    clearSession(SESSION_KEYS.UNIVERSITY_FROM);
    clearSession(SESSION_KEYS.SESSION_ID);
    resetFromStep(1);
  });

  // Form inputs
  univInput.addEventListener("change", () => {
    state.universityFrom = univInput.value;
    setSession(SESSION_KEYS.UNIVERSITY_FROM, univInput.value);
    
    // Reset dipartimento quando si cambia università
    state.department = "";
    deptInput.innerHTML = '<option value="">-- Seleziona prima un\'università --</option>';
    deptInput.disabled = true;
    
    renderAll();
  });
  
  deptInput.addEventListener("change", () => {
    state.department = deptInput.value;
    renderAll();
  });
  
  periodSelect.addEventListener("change", () => {
    state.period = periodSelect.value;
    renderAll();
  });

  // PDF upload
  if (studyPdfInput) {
    studyPdfInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      handlePdfFile(file);
    });
  }

  if (selectPdfBtn) {
    selectPdfBtn.addEventListener("click", () => studyPdfInput?.click());
  }

  if (studyPdfDropzone) {
    studyPdfDropzone.addEventListener("click", () => studyPdfInput?.click());
    studyPdfDropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        studyPdfInput?.click();
      }
    });

    ["dragenter", "dragover"].forEach((ev) =>
      studyPdfDropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        studyPdfDropzone.classList.add("dragover");
      })
    );
    
    ["dragleave", "dragend"].forEach((ev) =>
      studyPdfDropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        studyPdfDropzone.classList.remove("dragover");
      })
    );

    studyPdfDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      studyPdfDropzone.classList.remove("dragover");
      const file = e.dataTransfer?.files?.[0];
      handlePdfFile(file);
    });
  }

  // Action buttons
  findBandoBtn.addEventListener("click", () => {
    if (findBandoBtn.disabled) return;
    fetchBando();
  });
  
  shortlistBtn.addEventListener("click", () => {
    if (shortlistBtn.disabled) return;
    fetchShortlist();
  });
}

async function init() {
  // Carica le università disponibili
  await loadUniversities();
  
  // Ripristina dati dalla sessione
  const savedUni = getSession(SESSION_KEYS.UNIVERSITY_FROM);
  const savedSessionId = getSession(SESSION_KEYS.SESSION_ID);
  
  if (savedUni && !state.universityFrom) {
    state.universityFrom = savedUni;
    univInput.value = savedUni;
  }
  if (savedSessionId && !state.sessionId) {
    state.sessionId = savedSessionId;
    // Carica i dipartimenti se c'è un session_id salvato
    await loadDepartments();
  }
  
  wireEvents();
  renderAll();
}

document.addEventListener("DOMContentLoaded", init);
