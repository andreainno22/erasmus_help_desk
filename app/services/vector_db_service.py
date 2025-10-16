"""Service per gestire il database vettoriale dei documenti.

Questo modulo gestisce:
1. Creazione del database vettoriale da documenti (create_vector_store)
2. Caricamento e ricerca nei documenti (get_retriever)

Il database usa Chroma come backend e SentenceTransformers per gli embeddings.
"""

import os
from typing import Iterable, List, Optional
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from pathlib import Path


class VectorStoreService:
    """Gestore del database vettoriale."""
    
    def __init__(self, base_path: str = "vector_db"):
        """Inizializza il servizio.
        
        Args:
            base_path: Directory base per i database vettoriali
        """
        self.base_path = Path(base_path)
        self._embeddings = None
    
    @property
    def embeddings(self):
        """Lazy loading del modello di embeddings."""
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'}  # usa CPU, cambia in 'cuda' se hai GPU
            )
        return self._embeddings

    def create_vector_store(self, docs: List[Document], category: str) -> None:
        """Crea un nuovo database vettoriale per una categoria di documenti.
        
        Args:
            docs: Lista di Document Langchain con testo e metadati
            category: Categoria dei documenti (es. 'calls', 'courses')
        """
        # Percorso per questa categoria
        db_path = self.base_path / category
        
        # Crea database Chroma
        db = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            persist_directory=str(db_path)
        )
        
        # Salva su disco
        db.persist()
        
    def get_retriever(self, category: str, top_k: int = 5):
        """Carica il retriever per una categoria di documenti.
        
        Args:
            category: Categoria (es. 'calls', 'courses')
            top_k: Numero di risultati da restituire per query
            
        Returns:
            Retriever configurato per la categoria
            
        Raises:
            ValueError: se la categoria non esiste
        """
        db_path = self.base_path / category
        
        if not db_path.exists():
            raise ValueError(
                f"Database '{category}' non trovato. "
                f"Esegui prima create_vector_store per la categoria '{category}'"
            )
        
        # Carica database esistente
        db = Chroma(
            persist_directory=str(db_path),
            embedding_function=self.embeddings
        )
        
        # Configura e restituisci retriever
        return db.as_retriever(
            search_kwargs={
                "k": top_k,  # numero risultati
                "include_metadata": True  # include metadati nei risultati
            }
        )

    def search(self, 
               category: str,
               query: str,
               top_k: int = 5,
               filter_metadata: Optional[dict] = None) -> List[Document]:
        """Esegue una ricerca diretta nel database.
        
        Args:
            category: Categoria in cui cercare
            query: Testo della query
            top_k: Numero massimo di risultati
            filter_metadata: Filtro sui metadati (es. {"type": "call"})
            
        Returns:
            Lista di Document con i risultati più rilevanti
        """
        retriever = self.get_retriever(category, top_k)
        return retriever.get_relevant_documents(
            query,
            filter=filter_metadata
        )

# Istanza globale del servizio
vector_store_service = VectorStoreService()

# Funzioni di comodo che usano l'istanza globale
def create_vector_store(docs: List[Document], category: str) -> None:
    """Wrapper per VectorStoreService.create_vector_store."""
    vector_store_service.create_vector_store(docs, category)

def get_retriever(db_path: str, category: str, top_k: int = 5):
    """Wrapper per VectorStoreService.get_retriever.
    
    Args:
        db_path: Path base del database (ignorato, mantenuto per compatibilità)
        category: Categoria di documenti
        top_k: Numero di risultati
    """
    return vector_store_service.get_retriever(category, top_k)

