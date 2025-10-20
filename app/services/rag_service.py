# app/services/rag_service.py
import os
import json
import google.generativeai as genai
import fitz  # PyMuPDF
import pdfplumber
import re
from pathlib import Path

from .vector_db_service import get_retriever
from ..core.config import settings

def clean_and_parse_json_response(response_text: str, expected_type: str = "array") -> any:
    """
    Utility per pulire e parsare le risposte JSON dai modelli AI.
    
    Args:
        response_text: Il testo della risposta dal modello
        expected_type: "array" o "object" per validare il tipo di ritorno
        
    Returns:
        Il JSON parsato o None se il parsing fallisce
        
    Raises:
        ValueError: Se il JSON non è valido o non corrisponde al tipo atteso
    """
    if not response_text or not response_text.strip():
        raise ValueError("Risposta vuota dal modello AI")
    
    # Pulisci il testo della risposta
    cleaned_text = response_text.strip()
    
    # Rimuovi eventuali backticks e marcatori di codice
    if cleaned_text.startswith('```json'):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith('```'):
        cleaned_text = cleaned_text[3:]
    
    if cleaned_text.endswith('```'):
        cleaned_text = cleaned_text[:-3]
    
    cleaned_text = cleaned_text.strip()
    
    # Cerca il pattern JSON appropriato
    if expected_type == "array":
        json_match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
    else:
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
    
    if not json_match:
        raise ValueError(f"Nessun JSON {expected_type} trovato nella risposta: {cleaned_text[:200]}...")
    
    try:
        parsed_data = json.loads(json_match.group(0))
        
        # Valida il tipo
        if expected_type == "array" and not isinstance(parsed_data, list):
            raise ValueError(f"JSON parsato non è un array: {type(parsed_data)}")
        elif expected_type == "object" and not isinstance(parsed_data, dict):
            raise ValueError(f"JSON parsato non è un oggetto: {type(parsed_data)}")
            
        return parsed_data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Errore nel parsing JSON: {e}. Testo: {json_match.group(0)[:200]}...")

def extract_department_section(full_text: str, department: str) -> str:
    """
    Estrae solo la sezione specifica del dipartimento dal testo completo del bando.
    
    Args:
        full_text: Il testo completo del bando delle destinazioni
        department: Il nome del dipartimento da cercare
        
    Returns:
        La sezione di testo relativa al dipartimento specificato
        
    Raises:
        ValueError: Se il dipartimento non viene trovato
    """
    lines = full_text.split('\n')
    department_start_line = None
    department_end_line = None
    
    # Trova la linea di inizio del dipartimento
    for i, line in enumerate(lines):
        # Cerca una linea che contiene il nome del dipartimento e "n° borse:"
        if department.lower() in line.lower() and "n° borse:" in line:
            department_start_line = i
            break
    
    if department_start_line is None:
        # Prova una ricerca più flessibile se la prima non ha funzionato
        for i, line in enumerate(lines):
            if department.lower() in line.lower() and ("|" in line or "borse" in line.lower()):
                department_start_line = i
                break
    
    if department_start_line is None:
        raise ValueError(f"Dipartimento '{department}' non trovato nel file delle destinazioni")
    
    # Trova la linea di fine del dipartimento (inizio del prossimo dipartimento o fine file)
    for i in range(department_start_line + 1, len(lines)):
        line = lines[i]
        # Se troviamo un'altra linea che sembra essere l'intestazione di un altro dipartimento
        if ("Dipartiment" in line and "n° borse:" in line) or line.strip() == "":
            # Se è una linea vuota, continua a cercare
            if line.strip() == "":
                continue
            else:
                department_end_line = i
                break
    
    # Se non troviamo la fine, prendiamo tutto fino alla fine del file
    if department_end_line is None:
        department_end_line = len(lines)
    
    # Estrai la sezione del dipartimento
    department_section = '\n'.join(lines[department_start_line:department_end_line])
    
    if not department_section.strip():
        raise ValueError(f"Sezione vuota per il dipartimento '{department}'")
    
    print(f"✅ Estratta sezione per '{department}': {len(department_section)} caratteri")
    return department_section.strip()

# --- CONFIGURAZIONE DI GOOGLE AI ---
# Questa parte viene eseguita una sola volta quando il servizio viene importato.
# Configura la libreria con la chiave API caricata da .env
try:
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY non è impostato nel file .env o non è stato caricato.")
    genai.configure(api_key=settings.GOOGLE_API_KEY)
except Exception as e:
    print(f"ATTENZIONE: Errore durante la configurazione di Google AI: {e}")
    pass

async def get_call_summary(university_name: str) -> dict:
    """
    Identifica il bando, recupera i dati e genera un riassunto
    utilizzando il Google AI Python SDK (genai).
    """
    try:
        # --- 1. IDENTIFICA IL FILE DEL BANDO SPECIFICO ---
        calls_dir = "data/calls"
        
        target_filename = None
        if os.path.exists(calls_dir):
            for filename in os.listdir(calls_dir):
                if university_name in filename.lower() and filename.endswith(".pdf"):
                    target_filename = filename
                    break

        if not target_filename:
            return {"has_program": False, "summary": f"Nessun bando trovato per '{university_name}'."}

        # --- 2. RECUPERA I CHUNK SOLO DA QUEL FILE ---
        K_VALUE = 5
        retriever = get_retriever(settings.DB_PATH, category='calls', top_k=K_VALUE)
        
        retriever.search_kwargs = {'filter': {'source': target_filename}}

        query = "riassunto completo del bando erasmus: requisiti, scadenze e procedura"
        docs = retriever.get_relevant_documents(query)
        
        if not docs:
            return {
                "has_program": True, 
                "summary": f"Bando '{target_filename}' trovato, ma non è stato possibile estrarre informazioni pertinenti."
            }

        # --- 3. GENERA IL RIASSUNTO CON GEMINI (Google AI SDK) ---
        full_context = "\n\n---\n\n".join([doc.page_content for doc in docs])
        
        template = f"""
        Sei un assistente specializzato in programmi Erasmus. 
        Analizza il seguente testo estratto da un bando Erasmus e creane un riassunto conciso 
        evidenziando:
        - Periodo di apertura del bando
        - Requisiti principali (inclusi i requisiti linguistici)
        - Scadenze importanti
        - Processo di candidatura
        
        Contesto estratto dal bando:
        {full_context}
        """

        model = genai.GenerativeModel("gemini-2.0-flash")
        #response = await model.generate_content_async(template)
        # summary_text = response.text

        summary_text = "test"

        return {"has_program": True, "summary": summary_text}
        
    except Exception as e:
        print(f"Errore in get_call_summary: {e}")
        raise e

async def get_available_departments(home_university: str) -> list[str]:
    """
    Estrae tutti i dipartimenti disponibili dal file delle destinazioni dell'università.
    
    Args:
        home_university: Nome dell'università di origine
        
    Returns:
        Lista dei nomi dei dipartimenti disponibili
        
    Raises:
        FileNotFoundError: Se il file delle destinazioni non esiste
        ValueError: Se non è possibile estrarre i dipartimenti
    """
    try:
        # --- 1. IDENTIFICA IL FILE PDF DELLE DESTINAZIONI ---
        pdf_dir = "data/destinazioni"
        target_filename = f"destinazioni_bando_{home_university}"
        pdf_path = os.path.join(pdf_dir, target_filename)

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Il file delle destinazioni non è stato trovato: {pdf_path}")

        # --- 2. VERIFICA SE ESISTE GIÀ IL FILE TXT PROCESSATO ---
        txt_file = Path(f"data/destinazioni/processed/destinazioni_{home_university}_LLM_ready.txt")
        
        if not txt_file.exists():
            # Se non esiste, lo creiamo processando il PDF
            full_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Estrai tabelle strutturate
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            cleaned_row = [
                                cell.replace('\n', ' ').strip() if cell is not None else "" 
                                for cell in row
                            ]
                            line = " | ".join(cleaned_row)
                            full_text += line + "\n"
                    
                    # Estrai anche testo normale (non in tabelle)
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
            
            if not full_text.strip():
                raise ValueError("Il PDF è vuoto o non è stato possibile estrarre il testo.")

            # Pulisci e salva il testo
            cleaned_text = re.sub(r'\s+', ' ', full_text).strip()
            
            output_dir = Path("data/destinazioni/processed/")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            print(f"✅ Testo estratto e salvato in: {txt_file}")

        # --- 3. LEGGI IL FILE TXT ---
        with open(txt_file, 'r', encoding='utf-8') as f:
            llm_ready_text = f.read()

        # --- 4. ESTRAI I DIPARTIMENTI CON REGEX ---
        # Cerca tutte le linee che contengono "n° borse:" che indicano l'inizio di una sezione dipartimento
        department_pattern = r'([^|]+)\s*\|\s*n°\s*borse:'
        matches = re.findall(department_pattern, llm_ready_text, re.IGNORECASE)
        
        departments = []
        for match in matches:
            dept_name = match.strip()
            if dept_name and dept_name not in departments:
                departments.append(dept_name)
        
        if not departments:
            # Fallback: prova una ricerca più ampia
            lines = llm_ready_text.split('\n')
            for line in lines:
                if 'borse' in line.lower() and '|' in line:
                    # Estrai la prima parte prima del primo "|"
                    dept_candidate = line.split('|')[0].strip()
                    if dept_candidate and len(dept_candidate) > 3 and dept_candidate not in departments:
                        departments.append(dept_candidate)
        
        if not departments:
            raise ValueError("Nessun dipartimento trovato nel file delle destinazioni")
        
        print(f"✅ Trovati {len(departments)} dipartimenti: {departments}")
        return sorted(departments)
        
    except FileNotFoundError as e:
        print(f"Errore file in get_available_departments: {e}")
        raise e
    except Exception as e:
        print(f"Errore generico in get_available_departments: {e}")
        raise e

def get_erasmus_suggestions(course: str, preferences: str) -> list:
    """
    Orchestra il processo RAG per generare i suggerimenti.
    """
    # 1. Recupero (Retrieval)
    retriever = get_retriever(settings.DB_PATH, category='calls')
    
    # 2. Prompt
    context_docs = retriever.get_relevant_documents(f"Corso: {course}, Preferenze: {preferences}")
    context = "\n\n---\n\n".join([doc.page_content for doc in context_docs])

    template = f"""
    Sei un assistente esperto per studenti che devono scegliere una meta Erasmus.
    Il tuo compito è analizzare le preferenze dello studente e le informazioni estratte dai documenti per creare una classifica personalizzata delle 3 migliori destinazioni.
    Per ogni destinazione, fornisci: nome università, città, corsi consigliati, una motivazione chiara e un punteggio di affinità da 1 a 100.
    Basati ESCLUSIVAMENTE sul contesto fornito. Non inventare informazioni. Restituisci il risultato in formato JSON.

    --- CONTESTO RECUPERATO DAI DOCUMENTI ---
    {context}
    
    --- RICHIESTA DELLO STUDENTE ---
    Corso di studio: {course}
    Preferenze: {preferences}
    
    --- OUTPUT RICHIESTO (FORMATO JSON) ---
    """
    
    # 3. Generazione (Generation)
    model = genai.GenerativeModel("gemini-2.0-flash")
    #response = model.generate_content(template)
    response = "test"
    
    try:
        # Se la risposta è ancora "test", restituisci un array vuoto
        if response == "test":
            print("⚠️ Risposta di test rilevata, restituisco array vuoto")
            return []
            
        # Prova a parsare come JSON
        return json.loads(response.text)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"❌ Errore nel parsing JSON in get_erasmus_suggestions: {e}")
        print(f"❌ Risposta ricevuta: {response if isinstance(response, str) else getattr(response, 'text', 'N/A')[:200]}...")
        return []

def get_available_universities() -> list[str]:
    """
    Scansiona la cartella 'data/calls' e restituisce una lista di nomi di università
    basata sui file PDF dei bandi trovati.
    """
    calls_dir = "data/calls"
    universities = []
    
    if not os.path.exists(calls_dir):
        return []

    for filename in os.listdir(calls_dir):
        if filename.lower().endswith(".pdf"):
            # Estrae il nome dell'università dal nome del file
            # Esempio: "bando_erasmus_pisa_24-25.pdf" -> "pisa"
            try:
                # Capitalizza e sostituisce i trattini per una migliore leggibilità
                universities.append(filename)
            except IndexError:
                # Se il formato del file non è quello atteso, lo ignora
                continue
                
    return sorted(list(set(universities)))

async def analyze_destinations_for_department(home_university: str, department: str, period: str) -> list:
    """
    Analizza il PDF delle destinazioni per un'università specifica:
    1. Estrae il testo con pdfplumber
    2. Pulisce e salva il testo in un file .txt
    3. Estrae solo la sezione del dipartimento specificato
    4. Usa Gemini per analizzare solo quella sezione e trovare le destinazioni
    """
    try:
        # --- 1. IDENTIFICA IL FILE PDF DELLE DESTINAZIONI ---
        # Converte "University of Pisa" in "unipi" per matchare il nome del file
        pdf_dir = "data/destinazioni"
        target_filename = f"destinazioni_bando_{home_university}"
        pdf_path = os.path.join(pdf_dir, target_filename)

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Il file delle destinazioni non è stato trovato: {pdf_path}")

        if Path(f"data/destinazioni/processed/destinazioni_{home_university}_LLM_ready.txt").exists():
            txt_file = Path(f"data/destinazioni/processed/destinazioni_{home_university}_LLM_ready.txt")
            # Salta l'estrazione se il file esiste già
            print(f"✅ File di testo già esistente per {home_university}, salto l'estrazione.")
        else:
            # --- 2. ESTRAI IL TESTO DAL PDF USANDO PDFPLUMBER ---
            full_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Estrai tabelle strutturate
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            cleaned_row = [
                                cell.replace('\n', ' ').strip() if cell is not None else "" 
                                for cell in row
                            ]
                            line = " | ".join(cleaned_row)
                            full_text += line + "\n"
                    
                    # Estrai anche testo normale (non in tabelle)
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
            
            if not full_text.strip():
                raise ValueError("Il PDF è vuoto o non è stato possibile estrarre il testo.")

            # --- 3. PULISCI IL TESTO ---
            cleaned_text = re.sub(r'\s+', ' ', full_text).strip()
            
            # --- 4. SALVA IL TESTO PULITO IN UN FILE .TXT ---
            output_dir = Path("data/destinazioni/processed/")
            output_dir.mkdir(parents=True, exist_ok=True)
            txt_file = output_dir / f"destinazioni_{home_university}_LLM_ready.txt"
            
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            print(f"✅ Testo estratto e salvato in: {txt_file}")

        # --- 5. LEGGI IL FILE TXT PER PASSARLO ALL'LLM ---
        with open(txt_file, 'r', encoding='utf-8') as f:
            llm_ready_text = f.read()

        # --- 6. ESTRAI SOLO LA SEZIONE DEL DIPARTIMENTO SPECIFICO ---
        try:
            department_section = extract_department_section(llm_ready_text, department)
            print(f"📋 Sezione del dipartimento estratta: {len(department_section)} caratteri")
        except ValueError as e:
            print(f"❌ Errore nell'estrazione della sezione del dipartimento: {e}")
            raise e

        # --- 7. GENERA L'ANALISI CON GEMINI USANDO SOLO LA SEZIONE SPECIFICA ---
        template = f"""
        Sei un assistente universitario esperto nell'analisi di bandi Erasmus.
        Il tuo compito è analizzare la sezione specifica del dipartimento "{department}" fornita di seguito.
        Considera il periodo "{period}" per filtrare le destinazioni. Se non ci sono info sul periodo ignoralo.
        
        Estrai TUTTE le università partner elencate nella sezione, mantenendo ESATTAMENTE i campi come sono scritti nel file originale.

        Per ogni università partner trovata, crea un oggetto JSON con i seguenti campi:
        - "name": il nome dell'università estratto dal campo "NOME ISTITUZIONE"
        - "codice_europeo": valore del campo "CODICE EUROPEO"
        - "nome_istituzione": valore del campo "NOME ISTITUZIONE"
        - "codice_area": valore del campo "CODICE AREA"
        - "posti": valore del campo "POSTI"
        - "durata_per_posto": valore del campo "DURATA PER POSTO"
        - "livello": valore del campo "LIVELLO"
        - "dettagli_livello": valore del campo "DETTAGLI LIVELLO"
        - "requisiti_linguistici": valore del campo "REQUISITI LINGUISTICI"
        - "description": una breve descrizione accattivante di 1-2 frasi sull'università

        IMPORTANTE: 
        - Restituisci ESCLUSIVAMENTE un array JSON valido
        - Non aggiungere testo, spiegazioni o commenti prima o dopo l'array
        - Se un campo è vuoto nel file, inserisci una stringa vuota "" o null
        - Se non trovi destinazioni per il dipartimento, restituisci un array vuoto: []
        - Assicurati che il JSON sia sintatticamente corretto
        - Mantieni i valori dei campi esattamente come appaiono nel file
        - I campi devono corrispondere esattamente a quelli del file: CODICE EUROPEO | NOME ISTITUZIONE | CODICE AREA | DESCRIZIONE AREA ISCED | POSTI | DURATA PER POSTO | LIVELLO | DETTAGLI LIVELLO | REQUISITI LINGUISTICI | BLENDED | SHORT MOBILITY | BIP | CIRCLE U | SOTTO CONDIZIONE | NOTE PER GLI STUDENTI

        Esempio di formato richiesto:
        [
          {{
            "name": "UNIVERSIDAD DE BARCELONA",
            "codice_europeo": "E BARCELO01",
            "nome_istituzione": "UNIVERSIDAD DE BARCELONA",
            "codice_area": "0732",
            "posti": "2",
            "durata_per_posto": "5",
            "livello": "U",
            "dettagli_livello": "",
            "requisiti_linguistici": "Spanish B2",
            "description": "Prestigiosa università catalana con forti programmi in ingegneria civile."
          }}
        ]

        --- SEZIONE DEL DIPARTIMENTO "{department}" ---
        {department_section}
        """

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = await model.generate_content_async(template)
        
        print(f"🔍 Risposta di Gemini (primi 500 caratteri): {response.text[:500]}")
        
        try:
            destinations_data = clean_and_parse_json_response(response.text, "array")
            print(f"✅ Trovate {len(destinations_data)} destinazioni per {department}")
            return destinations_data
        except ValueError as e:
            print(f"❌ Errore nel parsing della risposta di Gemini: {e}")
            raise e

    except FileNotFoundError as e:
        print(f"Errore file in analyze_destinations: {e}")
        # Restituisce un errore specifico che l'endpoint può gestire
        raise e
    except Exception as e:
        print(f"Errore generico in analyze_destinations: {e}")
        raise e

async def analyze_exams_compatibility(destination_university_name: str, student_study_plan_text: str) -> dict:
    """
    Analizza la compatibilità degli esami tra il piano di studi dello studente 
    e gli esami disponibili presso l'università di destinazione.
    
    Args:
        destination_university_name: Nome dell'università di destinazione
        student_study_plan_text: Testo del piano di studi dello studente (estratto dal PDF)
        
    Returns:
        Dizionario con:
        - matched_exams: Lista degli esami con corrispondenze
        - suggested_exams: Lista degli esami suggeriti
        - compatibility_score: Punteggio di compatibilità 0-100
        - analysis_summary: Riassunto dell'analisi
        - exams_pdf_url: URL per scaricare il PDF completo
        - exams_pdf_filename: Nome del file PDF
        
    Raises:
        FileNotFoundError: Se il file degli esami dell'università non esiste
        ValueError: Se non è possibile analizzare la compatibilità
    """
    try:
        # --- 1. CERCA IL FILE PDF DEGLI ESAMI DELL'UNIVERSITÀ ---
        exams_dir = "data/corsi_erasmus"
        
        # Cerca il file PDF che corrisponde all'università di destinazione
        target_filename = None
        if os.path.exists(exams_dir):
            for filename in os.listdir(exams_dir):
                if filename.lower().endswith(".pdf"):
                    # Controlla se il nome dell'università è contenuto nel nome del file
                    # o se il nome del file è contenuto nel nome dell'università
                    if (destination_university_name.lower() in filename.lower() or 
                        any(word.lower() in destination_university_name.lower() 
                            for word in filename.replace('.pdf', '').split('_') if len(word) > 3)):
                        target_filename = filename
                        break

        if not target_filename:
            raise FileNotFoundError(f"Nessun file di esami trovato per '{destination_university_name}' nella cartella {exams_dir}")

        exam_pdf_path = os.path.join(exams_dir, target_filename)
        
        # --- 2. ESTRAI IL TESTO DAL PDF DEGLI ESAMI ---
        exam_text = extract_text_from_pdf(exam_pdf_path)

        print(f"✅ Estratto testo da {target_filename} ({len(exam_text)} caratteri)")
        print(f"🎓 Piano di studi studente ({len(student_study_plan_text)} caratteri)")

        # --- 3. ANALIZZA LA COMPATIBILITÀ CON GEMINI ---
        template = f"""
        Sei un esperto consulente universitario specializzato in programmi Erasmus.
        Il tuo compito è analizzare la compatibilità tra il piano di studi di uno studente 
        e gli esami disponibili presso un'università di destinazione Erasmus.

        **PIANO DI STUDI DELLO STUDENTE:**
        {student_study_plan_text}

        **ESAMI DISPONIBILI PRESSO L'UNIVERSITÀ DI DESTINAZIONE ({destination_university_name}):**
        {exam_text}

        **ISTRUZIONI:**
        1. Analizza il piano di studi dello studente per identificare gli esami
        2. Trova corrispondenze tra esami dello studente e corsi dell'università di destinazione
        3. Suggerisci esami aggiuntivi interessanti per il profilo dello studente
        4. Calcola un punteggio di compatibilità complessivo (0-100)
        5. Fornisci un riassunto dell'analisi

        **FORMATO DI RISPOSTA RICHIESTO (JSON):**
        {{
            "matched_exams": [
                {{
                    "student_exam": "Nome esame dello studente",
                    "destination_course": "Nome corso di destinazione corrispondente",
                    "compatibility": "alta",
                    "credits_student": "6 CFU",
                    "credits_destination": "6 ECTS",
                    "notes": "Descrizione della corrispondenza"
                }}
            ],
            "suggested_exams": [
                {{
                    "course_name": "Nome corso suggerito",
                    "credits": "6 ECTS",
                    "reason": "Motivo del suggerimento",
                    "category": "Computer Science"
                }}
            ],
            "compatibility_score": 85.0,
            "analysis_summary": "Riassunto dettagliato dell'analisi di compatibilità..."
        }}

        IMPORTANTE: 
        - Restituisci SOLO il JSON, senza testo aggiuntivo prima o dopo
        - Se non trovi corrispondenze, lascia gli array vuoti ma mantieni la struttura
        - Il punteggio deve essere un numero tra 0 e 100
        """

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = await model.generate_content_async(template)
        
        print(f"🔍 Risposta di Gemini per analisi esami (primi 500 caratteri): {response.text[:500]}")
        
        try:
            analysis_result = clean_and_parse_json_response(response.text, "object")
            print(f"✅ Analisi completata: {len(analysis_result.get('matched_exams', []))} corrispondenze, score: {analysis_result.get('compatibility_score', 0)}")
            
            # Aggiungi le informazioni del PDF al risultato
            analysis_result["exams_pdf_url"] = f"/api/student/files/exams/{target_filename}"
            analysis_result["exams_pdf_filename"] = target_filename
            
            return analysis_result
            
        except ValueError as e:
            print(f"❌ Errore nel parsing della risposta di Gemini: {e}")
            # Restituisce una risposta di fallback
            return {
                "matched_exams": [],
                "suggested_exams": [],
                "compatibility_score": 0.0,
                "analysis_summary": f"Errore nell'analisi automatica. Si prega di consultare manualmente il PDF dei corsi disponibili.",
                "exams_pdf_url": f"/api/student/files/exams/{target_filename}",
                "exams_pdf_filename": target_filename
            }
            
    except FileNotFoundError as e:
        print(f"Errore file in analyze_exams_compatibility: {e}")
        raise e
    except Exception as e:
        print(f"Errore generico in analyze_exams_compatibility: {e}")
        raise e
        raise e

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Utility per estrarre testo da un file PDF.
    
    Args:
        pdf_path: Percorso al file PDF
        
    Returns:
        Testo estratto dal PDF
        
    Raises:
        ValueError: Se il PDF è vuoto o non leggibile
    """
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            raise ValueError(f"Il PDF '{pdf_path}' è vuoto o non è stato possibile estrarre il testo.")
            
        return text.strip()
        
    except Exception as e:
        raise ValueError(f"Errore nell'estrazione del testo dal PDF '{pdf_path}': {e}")