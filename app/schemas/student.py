# app/schemas/student.py

from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(extra='forbid')
    home_university: str = Field(..., example="University of Pisa", description="Università di provenienza")

# STEP 1.5: Richiesta lista dipartimenti disponibili
class DepartmentsListRequest(BaseModel):
    """Richiesta lista dipartimenti disponibili per l'università."""
    model_config = ConfigDict(extra='forbid')
    session_id: str = Field(..., example="6f1d2c9e-9a3b-4a9e-94a1-3e2f8c5d9b1a", description="ID di sessione restituito dallo step 1")

# STEP 2: Richiesta analisi destinazioni compatibili
class DepartmentAndStudyPlanRequest(BaseModel):
    """Richiesta analisi destinazioni basata su dipartimento, piano di studi e periodo."""
    model_config = ConfigDict(extra='forbid')
    session_id: str = Field(..., example="6f1d2c9e-9a3b-4a9e-94a1-3e2f8c5d9b1a", description="ID di sessione restituito dallo step 1")
    department: str = Field(..., example="Computer Science", description="Dipartimento di afferenza")
    period: Period = Field(..., example="fall", description="Periodo desiderato (fall/spring)")

# STEP 3: Richiesta analisi esami per università scelta
class DestinationUniversityRequest(BaseModel):
    """Richiesta analisi esami disponibili presso università di destinazione."""
    session_id: str = Field(..., example="6f1d2c9e-9a3b-4a9e-94a1-3e2f8c5d9b1a", description="ID di sessione")
    destination_university_name: str = Field(..., example="TECHNICAL UNIVERSITY OF MUNICH", description="Nome dell'università di destinazione")
    # Il file PDF del piano di studi sarà gestito tramite FastAPI File upload nell'endpoint

# =================================================================
#               MODELLI PER LE RISPOSTE IN OUTPUT
# =================================================================

# STEP 1: Risposta con informazioni sul bando
class ErasmusProgramResponse(BaseModel):
    """Risposta con informazioni sul bando Erasmus."""
    has_program: bool = Field(..., description="True se il bando esiste, False altrimenti")
    summary: Optional[str] = Field(None, description="Riassunto del bando se esistente")
    session_id: Optional[str] = Field(None, description="ID di sessione da usare negli step successivi")

# STEP 1.5: Risposta con lista dipartimenti disponibili
class DepartmentsListResponse(BaseModel):
    """Risposta con lista dei dipartimenti disponibili."""
    departments: List[str] = Field(..., description="Lista dei nomi dei dipartimenti disponibili")

# STEP 2: Risposta con destinazioni compatibili
class DestinationUniversity(BaseModel):
    """Rappresenta una singola università di destinazione."""
    name: str = Field(..., example="TECHNICAL UNIVERSITY OF MUNICH")
    description: str = Field(..., description="Descrizione generata da Gemini")
    
    # Campi specifici del bando Erasmus
    codice_europeo: Optional[str] = Field(None, example="D MUNCHEN02", description="Codice europeo dell'istituzione")
    nome_istituzione: Optional[str] = Field(None, example="TECHNICAL UNIVERSITY OF MUNICH", description="Nome completo dell'istituzione")
    codice_area: Optional[str] = Field(None, example="0732", description="Codice area disciplinare")
    posti: Optional[str] = Field(None, example="2", description="Numero di posti disponibili")
    durata_per_posto: Optional[str] = Field(None, example="5", description="Durata in mesi per posto")
    livello: Optional[str] = Field(None, example="U", description="Livello di studio (U=Undergraduate, etc.)")
    dettagli_livello: Optional[str] = Field(None, example="", description="Dettagli aggiuntivi sul livello")
    requisiti_linguistici: Optional[str] = Field(None, example="German B2", description="Requisiti linguistici richiesti")

class DestinationsResponse(BaseModel):
    """Lista delle destinazioni compatibili."""
    destinations: List[DestinationUniversity]

# STEP 3: Risposta con analisi esami
class MatchedExam(BaseModel):
    """Rappresenta un esame dello studente con corrispondenza nell'università di destinazione."""
    student_exam: str = Field(..., example="Algoritmi e Strutture Dati")
    destination_course: str = Field(..., example="Advanced Algorithms")
    compatibility: str = Field(..., example="alta", description="alta/media/bassa")
    credits_student: str = Field(..., example="6 CFU")
    credits_destination: str = Field(..., example="6 ECTS")
    notes: Optional[str] = Field(None, example="Ottima corrispondenza di contenuti")

class SuggestedExam(BaseModel):
    """Rappresenta un esame suggerito da prendere nell'università di destinazione."""
    course_name: str = Field(..., example="Machine Learning")
    credits: str = Field(..., example="6 ECTS")
    reason: str = Field(..., example="Complementare al tuo percorso di studi")
    category: Optional[str] = Field(None, example="Computer Science")

class ExamsAnalysisResponse(BaseModel):
    """Risposta completa con PDF esami e analisi di compatibilità."""
    matched_exams: List[MatchedExam] = Field(..., description="Esami dello studente con corrispondenze trovate")
    suggested_exams: List[SuggestedExam] = Field(..., description="Esami suggeriti aggiuntivi")
    compatibility_score: float = Field(..., example=85.0, description="Punteggio di compatibilità 0-100")
    analysis_summary: str = Field(..., description="Riassunto dell'analisi di compatibilità")
    exams_pdf_url: str = Field(..., example="/api/student/files/exams/EETAC_Erasmus_Courses_2025-26.pdf", description="URL per scaricare il PDF completo dei corsi")
    exams_pdf_filename: str = Field(..., example="EETAC_Erasmus_Courses_2025-26.pdf", description="Nome del file PDF")
# backend invierà come risposta. FastAPI li userà per serializzare
# i dati in formato JSON.
