# scripts/ingest.py
import os
from app.services.document_service import load_and_split_documents
from app.services.vector_db_service import create_vector_store

# Percorso della cartella contenente i documenti da indicizzare
DATA_PATH = "data/"
# Percorso dove salvare il database vettoriale
DB_PATH = "vector_db/chroma"

def main():
    """
    Funzione principale per eseguire il processo di "ingestion":
    1. Carica i documenti dalla cartella /data.
    2. Li divide in "chunk" (pezzi).
    3. Crea gli embeddings e li salva nel database vettoriale.
    """
    print("Avvio del processo di ingestion...")
    
    # 1 & 2: Carica e splitta i documenti
    docs = load_and_split_documents(DATA_PATH)
    print(f"Caricati e divisi {len(docs)} chunk di testo.")
    
    # 3: Crea e salva il database vettoriale
    create_vector_store(docs, DB_PATH)
    print(f"Database vettoriale creato e salvato in '{DB_PATH}'.")
    print("Processo completato.")

if __name__ == "__main__":
    main()