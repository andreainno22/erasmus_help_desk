"""Service per creare e salvare il database vettoriale (stub).

Espone `create_vector_store(docs, db_path)` per ingest. Al momento è uno stub
con corpo vuoto (pass) come richiesto.
"""

from typing import Iterable


def create_vector_store(docs: Iterable[str], db_path: str) -> None:
    """Crea e salva un database vettoriale dai documenti forniti.

    Args:
        docs: iterable di chunk/testi.
        db_path: percorso dove salvare il database.

    Returns:
        None
    """
    # TODO: implementare creazione del vector store
    pass


def get_retriever(db_path: str, top_k: int = 5):
    """Carica il vector store da disco e ritorna un retriever.

    Questa implementazione usa Chroma + HuggingFace embeddings. Se i pacchetti
    non sono installati solleverà un ImportError con istruzioni di installazione.

    Args:
        db_path: percorso del vector store persistente.
        top_k: numero di risultati da restituire per query.

    Returns:
        un retriever compatibile con LangChain (es. .as_retriever()).
    """
    try:
        from langchain.vectorstores import Chroma
        from langchain.embeddings import HuggingFaceEmbeddings
    except ImportError as e:
        raise ImportError(
            "Pacchetti mancanti: esegui\n"
            "python -m pip install langchain chromadb sentence-transformers\n"
            "nel terminale del progetto."
        ) from e

    # embedding model (sentence-transformers)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # carica la collezione Chroma persistente
    db = Chroma(persist_directory=db_path, embedding_function=embeddings)

    # restituisce un retriever configurabile
    return db.as_retriever(search_kwargs={"k": top_k})

