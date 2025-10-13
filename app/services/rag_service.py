# app/services/rag_service.py
from .vector_db_service import get_retriever
from ..core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
import json

# Percorso del database vettoriale creato dallo script ingest.py
DB_PATH = "vector_db/chroma"

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