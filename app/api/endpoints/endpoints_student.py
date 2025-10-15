# app/api/endpoints/endpoints_student.py
from fastapi import APIRouter, HTTPException
from ...schemas.student import (
    UniversityRequest, ErasmusProgramResponse,
    DepartmentAndStudyPlanRequest, DestinationsResponse,
    DestinationUniversityRequest, ExamsAnalysisResponse
)
from ...services.rag_service import get_call_summary

router = APIRouter()

@router.post("/step1", response_model=ErasmusProgramResponse)
async def get_erasmus_program(request: UniversityRequest):
    """
    STEP 1: Riceve l'università di provenienza, identifica il bando specifico
    e restituisce un riassunto basato solo su quel documento.
    """
    try:
        # La logica è ora incapsulata nel servizio RAG
        result = await get_call_summary(request.home_university)
        return ErasmusProgramResponse(**result)
    except Exception as e:
        # Log dell'errore per un debug più semplice
        print(f"Errore nell'endpoint /step1: {e}")
        raise HTTPException(status_code=500, detail=f"Si è verificato un errore interno: {e}")

@router.post("/step2", response_model=DestinationsResponse)
async def analyze_destinations(request: DepartmentAndStudyPlanRequest):
    """
    STEP 2: Riceve dipartimento e piano di studi.
    Analizza i PDF delle destinazioni usando Gemini e restituisce le università compatibili.
    """
    try:
        # TODO: Implementare analisi con Gemini dei PDF delle destinazioni. 
        # Attenzione che il file delle destinazioni deve essere interamente analizzato da gemini
        # non solo alcuni chunks

        destinations = [
            {
                "id": "uni123",
                "city_id": "city456",
                "name": "Technical University of Munich",
                "description": "Università tecnica con forte focus su..."
            }
        ]
        return DestinationsResponse(destinations=destinations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step3", response_model=ExamsAnalysisResponse)
async def analyze_exams(request: DestinationUniversityRequest):
    """
    STEP 3: Riceve l'università di destinazione scelta e il piano di studi.
    Restituisce il PDF degli esami disponibili e l'analisi di compatibilità.
    """
    try:
        # TODO: Implementare recupero PDF esami e analisi con Gemini
        response = {
            "pdf_url": "https://example.com/exams.pdf",
            "available_exams": [
                {
                    "name": "Advanced Algorithms",
                    "credits": 6,
                    "description": "Advanced course on algorithm design...",
                    "period": "fall"
                }
            ]
        }
        return ExamsAnalysisResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))