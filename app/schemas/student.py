# app/schemas/student.py

from pydantic import BaseModel, Field, constr
from typing import List, Optional
from enum import Enum


class Period(str, Enum):
    """Periodo di studio Erasmus."""
    FALL = "fall"
    SPRING = "spring"


# =================================================================
#               MODELLI PER LE RICHIESTE IN INPUT
# =================================================================

# STEP 1: Richiesta iniziale con università
class UniversityRequest(BaseModel):
    """Richiesta informazioni sul bando Erasmus."""
    home_university: str = Field(..., example="University of Pisa", description="Università di provenienza")

# STEP 2: Richiesta analisi destinazioni compatibili
class DepartmentAndStudyPlanRequest(BaseModel):
    """Richiesta analisi destinazioni basata su dipartimento, piano di studi e periodo."""
    home_university: str = Field(..., example="University of Pisa", description="Università di provenienza dello studente, per filtrare le destinazioni corrette.")
    department: str = Field(..., example="Computer Science", description="Dipartimento di afferenza")
    study_plan: List[str] = Field(..., example=["Algorithms", "Machine Learning", "Database"], 
                                description="Lista degli esami nel piano di studi")
    period: Period = Field(..., example="fall", description="Periodo desiderato (fall/spring)")

# STEP 3: Richiesta analisi esami per università scelta
class DestinationUniversityRequest(BaseModel):
    """Richiesta analisi esami disponibili presso università di destinazione."""
    destination_id: str = Field(..., example="uni123", description="ID dell'università di destinazione")
    study_plan: List[str] = Field(..., example=["Algorithms", "Machine Learning"], 
                                description="Piano di studi per matching con esami disponibili")

# =================================================================
#               MODELLI PER LE RISPOSTE IN OUTPUT
# =================================================================

# STEP 1: Risposta con informazioni sul bando
class ErasmusProgramResponse(BaseModel):
    """Risposta con informazioni sul bando Erasmus."""
    has_program: bool = Field(..., description="True se il bando esiste, False altrimenti")
    summary: Optional[str] = Field(None, description="Riassunto del bando se esistente")

# STEP 2: Risposta con destinazioni compatibili
class DestinationUniversity(BaseModel):
    """Rappresenta una singola università di destinazione."""
    id: str = Field(..., example="uni123", description="ID univoco dell'università")
    city_id: str = Field(..., example="city456", description="ID della città")
    name: str = Field(..., example="Technical University of Munich")
    description: str = Field(..., description="Descrizione generata da Gemini")

class DestinationsResponse(BaseModel):
    """Lista delle destinazioni compatibili."""
    destinations: List[DestinationUniversity]

# STEP 3: Risposta con analisi esami
class AvailableExam(BaseModel):
    """Rappresenta un esame disponibile presso l'università di destinazione."""
    name: str = Field(..., example="Advanced Algorithms")
    credits: int = Field(..., example=6)
    description: str = Field(..., example="Advanced course on algorithm design...")
    period: Period = Field(..., example="fall")

class ExamsAnalysisResponse(BaseModel):
    """Risposta completa con PDF esami e analisi di compatibilità."""
    pdf_url: str = Field(..., description="URL al PDF con lista completa esami")
    available_exams: List[AvailableExam] = Field(..., description="Esami compatibili con il piano di studi")
# backend invierà come risposta. FastAPI li userà per serializzare
# i dati in formato JSON.
