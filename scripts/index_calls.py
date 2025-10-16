# scripts/index_calls.py
"""Script per indicizzare i bandi Erasmus nel vector store."""

import sys
from pathlib import Path

# Aggiungi la directory root al PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.services.document_service import process_calls
from app.services.vector_db_service import create_vector_store


def main():
    """Carica i bandi PDF e crea il vector store."""
    print("Inizio indicizzazione bandi Erasmus...")
    
    try:
        # 1. Carica e processa i PDF dei bandi
        documents = process_calls()
        print(f"Caricati {len(documents)} chunks da bandi")
        
        # 2. Crea il vector store
        create_vector_store(documents, category='esami_incoming_students')
        print("Vector store creato con successo")
        
    except Exception as e:
        print(f"Errore durante l'indicizzazione: {str(e)}")
        sys.exit(1)
        
    print("Indicizzazione completata!")


if __name__ == "__main__":
    main()