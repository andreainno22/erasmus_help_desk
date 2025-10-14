"""Service per caricare e processare i documenti PDF.

Questo modulo si occupa di:
1. Caricare i PDF da una directory
2. Dividerli in chunk di testo gestibili per il vector store
"""

from pathlib import Path
from typing import List
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


def load_and_split_documents(data_path: str) -> List[Document]:
    """Carica e divide i PDF in chunks.

    Args:
        data_path: percorso alla cartella con i PDF

    Returns:
        Lista di Document con il testo diviso in chunks
    """
    data_dir = Path(data_path)
    if not data_dir.exists():
        raise ValueError(f"Directory {data_path} non trovata")

    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,        # caratteri per chunk
        chunk_overlap=200,      # overlap tra chunk
    )
    
    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"Nessun PDF trovato nella cartella {data_path}")
        return []

    # Processa ogni PDF nella directory
    for pdf_path in pdf_files:
        try:
            # Carica il PDF
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()
            
            # Aggiungi solo il nome del file come metadata
            for page in pages:
                page.metadata["source"] = pdf_path.name
            
            # Dividi in chunk
            chunks = text_splitter.split_documents(pages)
            documents.extend(chunks)
            
            print(f"Processato {pdf_path.name}: {len(chunks)} chunks creati")
            
        except Exception as e:
            print(f"Errore nel processare {pdf_path.name}: {str(e)}")
            continue
    
    return documents


def process_calls(calls_dir: str = "data/calls") -> List[Document]:
    """Funzione dedicata per processare i bandi Erasmus.

    Args:
        calls_dir: percorso alla directory dei bandi

    Returns:
        Lista di Document pronti per il vector store
    """
    return load_and_split_documents(calls_dir)

