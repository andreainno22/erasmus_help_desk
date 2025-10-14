"""Service per la gestione dei bandi Erasmus.

Questo modulo fornisce le classi e funzioni necessarie per gestire i bandi Erasmus.
La gestione avviene tramite:
1. File PDF dei bandi nella cartella data/calls/
2. File metadata.json che contiene le informazioni strutturate dei bandi
3. Funzionalità per cercare, aggiungere e recuperare i bandi
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel


class CallMetadata(BaseModel):
    """Modello Pydantic per i metadata di un bando.
    
    Attributes:
        university: Nome dell'università che ha pubblicato il bando
        academic_year: Anno accademico del bando (es. "2024/2025")
        deadline: Data di scadenza del bando
        last_updated: Data dell'ultimo aggiornamento del record
        languages_required: Lista dei requisiti linguistici (es. ["English B2"])
        type: Tipo di bando (es. "general_call")
    """
    university: str
    academic_year: str
    deadline: str
    last_updated: str
    languages_required: List[str]
    type: str


class CallService:
    """Servizio per la gestione dei bandi Erasmus.
    
    Questa classe gestisce l'accesso e la manipolazione dei bandi Erasmus,
    mantenendo le informazioni in un file metadata.json insieme ai PDF.
    
    Attributes:
        calls_dir: Path della directory contenente i bandi PDF
        metadata_path: Path del file metadata.json
        metadata: Dizionario con i metadata caricati dal JSON
    """
    
    def __init__(self, calls_dir: str = "data/calls"):
        """Inizializza il servizio.
        
        Args:
            calls_dir: Path della directory contenente i bandi (default: "data/calls")
        """
        self.calls_dir = Path(calls_dir)
        self.metadata_path = self.calls_dir / "metadata.json"
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Carica i metadata dal file JSON.
        
        Se il file non esiste, inizializza un dizionario vuoto.
        Il file metadata.json contiene un dizionario dove:
        - Le chiavi sono i nomi dei file PDF
        - I valori sono dizionari con i metadata del bando
        """
        if not self.metadata_path.exists():
            self.metadata = {}
            return
        
        with open(self.metadata_path) as f:
            self.metadata = json.load(f)

    def get_call(self, university: str) -> Optional[tuple[str, CallMetadata]]:
        """Cerca il bando più recente per una specifica università.
        
        La ricerca è case-insensitive sul nome dell'università.
        Se esistono più bandi per la stessa università, viene restituito
        quello con l'anno accademico più recente.
        
        Args:
            university: Nome dell'università da cercare
            
        Returns:
            Se trovato, una tupla con:
            - nome del file PDF del bando
            - oggetto CallMetadata con i metadata
            Se non trovato, None
        """
        # Cerca bandi per l'università (case insensitive)
        university_calls = [
            (filename, CallMetadata(**meta))
            for filename, meta in self.metadata.items()
            if meta["university"].lower() == university.lower()
        ]
        
        if not university_calls:
            return None
            
        # Ritorna il bando più recente
        return max(
            university_calls,
            key=lambda x: x[1].academic_year
        )

    def get_call_path(self, filename: str) -> Path:
        """Costruisce il path completo di un file di bando.
        
        Args:
            filename: Nome del file PDF del bando
            
        Returns:
            Path completo al file del bando
        """
        return self.calls_dir / filename

    def add_call(self, 
                 filename: str,
                 university: str,
                 academic_year: str,
                 deadline: str,
                 languages_required: List[str],
                 call_type: str = "general_call") -> None:
        """Aggiunge un nuovo bando al registro dei metadata.
        
        Questa funzione:
        1. Crea un nuovo record nei metadata per il bando
        2. Imposta la data di ultimo aggiornamento
        3. Salva il metadata.json aggiornato
        
        Args:
            filename: Nome del file PDF del bando
            university: Nome dell'università
            academic_year: Anno accademico (es. "2024/2025")
            deadline: Data di scadenza del bando
            languages_required: Lista dei requisiti linguistici
            call_type: Tipo di bando (default: "general_call")
        """
        self.metadata[filename] = {
            "university": university,
            "academic_year": academic_year,
            "deadline": deadline,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "languages_required": languages_required,
            "type": call_type
        }
        
        # Salva i metadata aggiornati
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=4)