# app/main.py
from fastapi import FastAPI
from .api.endpoints import matching

app = FastAPI(
    title="Erasmus Suggester API",
    description="Un'API per suggerire la meta Erasmus perfetta usando l'IA Generativa.",
    version="1.0.0"
)

# Include il router con l'endpoint /match
app.include_router(matching.router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Benvenuto nell'API di Erasmus Suggester!"}