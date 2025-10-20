# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .api.endpoints import endpoints_student
import os

app = FastAPI(
    title="Erasmus Help Desk API",
    description="API per assistenza studenti Erasmus con suggerimenti personalizzati",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (simple, volatile). Use a proper store for production.
app.state.session_store = {}

# Include router con prefisso corretto
app.include_router(endpoints_student.router, prefix="/api/student", tags=["student"])

# Serve static files (frontend)
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    
    @app.get("/", tags=["Root"])
    async def read_root():
        """Serve la homepage del frontend"""
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Erasmus Help Desk API - Frontend not found"}
else:
    @app.get("/", tags=["Root"])
    def read_root():
        return {
            "message": "Erasmus Help Desk API",
            "version": "1.0.0",
            "docs": "/docs",
            "endpoints": {
                "step1": "POST /api/student/step1",
                "departments": "POST /api/student/departments",
                "step2": "POST /api/student/step2",
                "step3": "POST /api/student/step3",
                "universities": "GET /api/student/universities",
                "exam_files": "GET /api/student/files/exams/{filename}"
            }
        }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Server is running"}