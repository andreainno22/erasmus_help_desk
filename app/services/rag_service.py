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
        
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = await model.generate_content_async(template)
        
        summary_text = response.text

        return {"has_program": True, "summary": summary_text}
        
    except Exception as e:
        print(f"Errore in get_call_summary: {e}")
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
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    response = model.generate_content(template)
    
    try:
        return json.loads(response.text)
    except (json.JSONDecodeError, AttributeError):
        print("Errore: L'output del modello non è un JSON valido o la risposta è vuota.")
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

async def analyze_destinations_for_department(home_university: str, department: str) -> list:
    """
    Analizza il PDF delle destinazioni per un'università specifica:
    1. Estrae il testo con pdfplumber
    2. Pulisce e salva il testo in un file .txt
    3. Usa Gemini per trovare le destinazioni del dipartimento specifico
    """
    try:
        # --- 1. IDENTIFICA IL FILE PDF DELLE DESTINAZIONI ---
        # Converte "University of Pisa" in "unipi" per matchare il nome del file
        pdf_dir = "data/destinazioni"
        target_filename = f"destinazioni_bando_{home_university}.pdf"
        pdf_path = os.path.join(pdf_dir, target_filename)

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Il file delle destinazioni non è stato trovato: {pdf_path}")

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

        # --- 6. GENERA L'ANALISI CON GEMINI ---
        template = f"""
        Sei un assistente universitario esperto nell'analisi di bandi Erasmus.
        Il tuo compito è analizzare il testo completo di un bando di destinazioni fornito di seguito.
        Devi trovare la sezione specifica per il dipartimento di "{department}".
        Una volta trovata, estrai TUTTE le università partner elencate in quella sezione.

        Per ogni università partner trovata, crea un oggetto JSON con i seguenti campi:
        - "id": un ID univoco generato da te (es. "uni_01", "uni_02").
        - "city_id": un ID per la città (es. "city_01", "city_02").
        - "name": il nome completo e corretto dell'università.
        - "description": una breve descrizione accattivante di 1-2 frasi sull'università, evidenziando i suoi punti di forza o la sua localizzazione.

        Restituisci ESCLUSIVAMENTE un array JSON contenente questi oggetti. Non aggiungere testo o spiegazioni prima o dopo l'array.

        --- TESTO COMPLETO DEL BANDO ---
        {llm_ready_text}
        """

        model = genai.GenerativeModel("gemini-2.5-pro-latest")
        response = await model.generate_content_async(template)
        
        # Pulisce la risposta per estrarre solo il JSON
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if not json_match:
            raise ValueError("Gemini non ha restituito un array JSON valido.")
            
        destinations_data = json.loads(json_match.group(0))
        return destinations_data

    except FileNotFoundError as e:
        print(f"Errore file in analyze_destinations: {e}")
        # Restituisce un errore specifico che l'endpoint può gestire
        raise e
    except Exception as e:
        print(f"Errore generico in analyze_destinations: {e}")
        raise e