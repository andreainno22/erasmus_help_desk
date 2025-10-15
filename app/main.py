# app/main.py
from fastapi import FastAPI
from .api.endpoints import endpoints_student

app = FastAPI(
    title="Erasmus Suggester API",
    description="Un'API per suggerire la meta Erasmus perfetta usando l'IA Generativa.",
    version="1.0.0"
)

# In-memory session store (simple, volatile). Use a proper store for production.
app.state.session_store = {}

app.include_router(endpoints_student.router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def read_root():
    print("ciao")
    return {"message": "Benvenuto nell'API di Erasmus Suggester!"}