# app/services/rag_service.py
from .vector_db_service import get_retriever
from ..core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
import json
import os

# Percorso del database vettoriale creato dallo script ingest.py
DB_PATH = "vector_db/chroma"

async def get_call_summary(university_name: str) -> dict:
    """
    Identifica il bando di una specifica università, recupera i dati pertinenti
    e ne genera un riassunto utilizzando un LLM.
    """
    try:
        # --- 1. IDENTIFICA IL FILE DEL BANDO SPECIFICO ---
        university_slug = university_name.lower().replace(" ", "_").replace("di_", "")
        calls_dir = "data/calls"
        
        target_filename = None
        if os.path.exists(calls_dir):
            for filename in os.listdir(calls_dir):
                if university_slug in filename.lower() and filename.endswith(".pdf"):
                    target_filename = filename
                    break

        if not target_filename:
            return {"has_program": False, "summary": f"Nessun bando trovato per '{university_name}'."}

        # --- 2. RECUPERA I CHUNK SOLO DA QUEL FILE ---
        K_VALUE = 5  # Aumentato per avere più contesto
        retriever = get_retriever(DB_PATH, category='calls', top_k=K_VALUE)
        
        # Filtra la ricerca per i chunk provenienti solo dal file corretto
        retriever.search_kwargs = {'filter': {'source': target_filename}}

        query = "riassunto completo del bando erasmus: requisiti, scadenze e procedura"
        docs = retriever.get_relevant_documents(query)
        
        if not docs:
            return {
                "has_program": True, 
                "summary": f"Bando '{target_filename}' trovato, ma non è stato possibile estrarre informazioni pertinenti."
            }

        # --- 3. GENERA IL RIASSUNTO CON GEMINI ---
        full_context = "\n\n---\n\n".join([doc.page_content for doc in docs])
        
        template = """
        Sei un assistente specializzato in programmi Erasmus. 
        Analizza il seguente testo estratto da un bando Erasmus e creane un riassunto conciso 
        evidenziando:
        - Periodo di apertura del bando
        - Requisiti principali (inclusi i requisiti linguistici)
        - Scadenze importanti
        - Processo di candidatura
        
        Contesto estratto dal bando:
        {content}
        """
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro-latest",
            google_api_key=settings.GOOGLE_API_KEY
        )
        
        summary_result = await llm.invoke(template.format(content=full_context))
        
        # L'output di invoke è un AIMessage, ne estraiamo il contenuto
        summary_text = summary_result.content if hasattr(summary_result, 'content') else str(summary_result)

        return {"has_program": True, "summary": summary_text}
        
    except Exception as e:
        # Log dell'errore per debug
        print(f"Errore in get_call_summary: {e}")
        # Rilancia l'eccezione o restituisce un errore strutturato
        raise e

def get_erasmus_suggestions(course: str, preferences: str) -> list:
    """
    Orchestra il processo RAG per generare i suggerimenti.
    """
    # 1. Recupero (Retrieval)
    retriever = get_retriever(DB_PATH)
    
    # 2. Prompt Engineering [cite: 56]
    template = """
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
    prompt = PromptTemplate.from_template(template)
    
    # 3. Generazione (Generation) [cite: 34]
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=settings.GOOGLE_API_KEY)
    
    # 4. Creazione della "Chain" LangChain
    rag_chain = (
        {"context": retriever, "course": RunnablePassthrough(), "preferences": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    # Combinazione degli input per la chain
    user_input = {"course": course, "preferences": preferences}
    
    # Esecuzione della chain e parsing della risposta
    response_str = rag_chain.invoke(f"Corso: {course}, Preferenze: {preferences}")
    
    try:
        # Gemini dovrebbe restituire un JSON valido come da istruzioni [cite: 61, 64]
        return json.loads(response_str)
    except json.JSONDecodeError:
        # Gestione nel caso l'output non sia un JSON valido
        print("Errore: L'output del modello non è un JSON valido.")
        return []