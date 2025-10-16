# app/api/endpoints/endpoints_student.py
from fastapi import APIRouter, HTTPException, Request
from typing import List
from ...schemas.student import (
    UniversityRequest, ErasmusProgramResponse,
    DepartmentAndStudyPlanRequest, DestinationsResponse,
    DestinationUniversityRequest, ExamsAnalysisResponse
)
from ...services.rag_service import get_call_summary, get_available_universities
from uuid import uuid4

router = APIRouter()

@router.post("/step1", response_model=ErasmusProgramResponse)
async def get_erasmus_program(body: UniversityRequest, req: Request):
    """
    STEP 1: Riceve l'università di provenienza, identifica il bando specifico
    e restituisce un riassunto basato solo su quel documento.
    """
    try:
        # La logica è ora incapsulata nel servizio RAG
        result = await get_call_summary(body.home_university)

        # Crea una sessione e memorizza l'università scelta
        session_id = str(uuid4())
        req.app.state.session_store[session_id] = {"home_university": body.home_university}

        # Includi il session_id nella risposta
        return ErasmusProgramResponse(**{**result, "session_id": session_id})
    except Exception as e:
        # Log dell'errore per un debug più semplice
        print(f"Errore nell'endpoint /step1: {e}")
        raise HTTPException(status_code=500, detail=f"Si è verificato un errore interno: {e}")

@router.post("/step2", response_model=DestinationsResponse)
async def analyze_destinations(request: DepartmentAndStudyPlanRequest, req: Request):
    """
    STEP 2: Riceve dipartimento e piano di studi.
    Analizza i PDF delle destinazioni usando Gemini e restituisce le università compatibili.
    """
    try:
        # Recupera la home_university dalla sessione
        session = req.app.state.session_store.get(request.session_id)
        if not session or "home_university" not in session:
            raise HTTPException(status_code=400, detail="Sessione non valida o scaduta. Rieseguire lo Step 1.")

        home_university = session["home_university"]

        # Chiamata al servizio per analizzare le destinazioni del dipartimento
        from ...services.rag_service import analyze_destinations_for_department
        destinations_list = await analyze_destinations_for_department(home_university=home_university, department=request.department)

        return DestinationsResponse(destinations=destinations_list)
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

@router.get("/universities", response_model=List[str])
async def list_available_universities():
    """
    Restituisce la lista delle università per cui è disponibile un bando.
    Questa lista può essere usata nel frontend per popolare un menu a tendina.
    """
    try:
        universities = get_available_universities()
        return universities
    except Exception as e:
        print(f"Errore nell'endpoint /universities: {e}")
        raise HTTPException(status_code=500, detail="Errore nel recupero delle università disponibili.")