# app/api/endpoints/endpoints_student.py
import os
from fastapi import APIRouter, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import FileResponse
from typing import List
from ...schemas.student import (
    UniversityRequest, ErasmusProgramResponse,
    DepartmentsListRequest, DepartmentsListResponse,
    DepartmentAndStudyPlanRequest, DestinationsResponse,
    DestinationUniversityRequest, ExamsAnalysisResponse
)
from ...services.rag_service import get_call_summary, get_available_universities, get_available_departments
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

@router.post("/departments", response_model=DepartmentsListResponse)
async def get_departments_list(request: DepartmentsListRequest, req: Request):
    """
    STEP 1.5: Riceve il session_id e restituisce la lista dei dipartimenti disponibili
    per l'università dell'utente.
    """
    try:
        # Recupera la home_university dalla sessione
        session = req.app.state.session_store.get(request.session_id)
        if not session or "home_university" not in session:
            raise HTTPException(status_code=400, detail="Sessione non valida o scaduta. Rieseguire lo Step 1.")

        home_university = session["home_university"]

        # Chiamata al servizio per recuperare i dipartimenti
        departments = await get_available_departments(home_university=home_university)

        return DepartmentsListResponse(departments=departments)
    except Exception as e:
        print(f"Errore nell'endpoint /departments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        destinations_list = await analyze_destinations_for_department(home_university=home_university, department=request.department, period=request.period)

        return DestinationsResponse(destinations=destinations_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step3", response_model=ExamsAnalysisResponse)
async def analyze_exams(
    session_id: str = Form(...),
    destination_university_name: str = Form(...),
    study_plan_file: UploadFile = File(...),
    req: Request = None
):
    """
    STEP 3: Riceve l'università di destinazione scelta e il piano di studi (PDF).
    Restituisce il PDF degli esami disponibili e l'analisi di compatibilità.
    """
    try:
        # Verifica la sessione
        session = req.app.state.session_store.get(session_id)
        if not session or "home_university" not in session:
            raise HTTPException(status_code=400, detail="Sessione non valida o scaduta.")

        # Verifica che il file sia un PDF
        if not study_plan_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Il piano di studi deve essere un file PDF.")

        # Salva temporaneamente il file del piano di studi
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await study_plan_file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Estrai il testo dal PDF del piano di studi
            from ...services.rag_service import extract_text_from_pdf, analyze_exams_compatibility
            
            study_plan_text = extract_text_from_pdf(tmp_file_path)
            print(f"📚 Piano di studi estratto: {len(study_plan_text)} caratteri")
            
            # Analizza la compatibilità degli esami
            analysis_result = await analyze_exams_compatibility(
                destination_university_name=destination_university_name,
                student_study_plan_text=study_plan_text
            )
            
            return ExamsAnalysisResponse(**analysis_result)
            
        finally:
            # Rimuovi il file temporaneo
            os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Errore in analyze_exams: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nell'analisi degli esami: {str(e)}")

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

@router.get("/files/exams/{filename}")
async def download_exam_pdf(filename: str):
    """
    Serve i file PDF degli esami delle università di destinazione.
    Permette agli utenti di scaricare o visualizzare il PDF completo dei corsi disponibili.
    """
    try:
        file_path = os.path.join("data/corsi_erasmus", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File non trovato")
        
        # Verifica che il file sia effettivamente un PDF
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Il file richiesto non è un PDF valido")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Errore nel download del PDF: {e}")
        raise HTTPException(status_code=500, detail="Errore nel download del file")