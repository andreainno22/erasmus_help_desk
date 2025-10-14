# app/api/endpoints/endpoints_student.py
from fastapi import APIRouter, HTTPException
from ...schemas.student import (
    UniversityRequest, ErasmusProgramResponse,
    DepartmentAndStudyPlanRequest, DestinationsResponse,
    DestinationUniversityRequest, ExamsAnalysisResponse
)
from ...services.vector_db_service import get_retriever
from langchain_google_genai import ChatGoogleGenerativeAI
from ...core.config import settings, DB_PATH
from typing import Optional
from ...services.vector_db_service import get_retriever
DB_PATH = "vector_db/chroma"

router = APIRouter()

@router.post("/step1", response_model=ErasmusProgramResponse)
async def get_erasmus_program(request: UniversityRequest):
    """
    STEP 1: Riceve università di provenienza.
    Restituisce il riassunto del bando Erasmus se disponibile.
    """
    try:
        # Recupera il contenuto dal vector store
        retriever = get_retriever(DB_PATH, category='calls')
        docs = retriever.get_relevant_documents(
            f"informazioni e riassunto del bando erasmus per {request.home_university}"
        )
        
        if not docs:
            return ErasmusProgramResponse(has_program=False)

        # Unisci il contenuto di tutti i chunk trovati per dare a Gemini il contesto completo.
        full_context = "\n\n---\n\n".join([doc.page_content for doc in docs])
        
        # Genera riassunto con Gemini
        template = """
        Sei un assistente specializzato in programmi Erasmus. 
        Analizza il seguente bando Erasmus e creane un riassunto conciso, 
        senza inventare informazioni, ma basandoti solo sul documento allegato, 
        evidenziando:
        - Periodo di apertura del bando
        - Requisiti principali (inclusi i requisiti linguistici)
        - Scadenze importanti
        - Processo di candidatura
        
        Bando:
        {content}
        """
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro-latest",
            google_api_key=settings.GOOGLE_API_KEY
        )
        
        summary = await llm.invoke(
            template.format(content=full_context)
        )
        
        return ErasmusProgramResponse(has_program=True, summary=str(summary))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step2", response_model=DestinationsResponse)
async def analyze_destinations(request: DepartmentAndStudyPlanRequest):
    """
    STEP 2: Riceve dipartimento e piano di studi.
    Analizza i PDF delle destinazioni usando Gemini e restituisce le università compatibili.
    """
    try:
        # TODO: Implementare analisi con Gemini dei PDF delle destinazioni
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