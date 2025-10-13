# app/api/endpoints/matching.py
from fastapi import APIRouter, HTTPException
from ...schemas.student import StudentRequest, StudentResponse
from ...services.rag_service import get_erasmus_suggestions

router = APIRouter()

@router.post("/match", response_model=StudentResponse)
def get_matches(request: StudentRequest):
    """
    Riceve le preferenze dello studente, interroga il sistema RAG 
    e restituisce una classifica delle 3 migliori destinazioni.
    """
    try:
        suggestions = get_erasmus_suggestions(request.course_of_study, request.preferences)
        return StudentResponse(destinations=suggestions)
    except Exception as e:
        # Gestione generica degli errori
        raise HTTPException(status_code=500, detail=str(e))