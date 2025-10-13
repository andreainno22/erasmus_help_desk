# app/schemas/student.py

from pydantic import BaseModel, Field
from typing import List

# =================================================================
#               MODELLO PER LA RICHIESTA IN INPUT
# =================================================================
# Questo modello definisce la struttura dei dati che il frontend
# invierà al nostro backend. FastAPI lo userà per validare
# che la richiesta sia formata correttamente.

class StudentRequest(BaseModel):
    """
    Schema per i dati in input: le preferenze dello studente.
    """
    course_of_study: str = Field(
        ..., 
        example="Ingegneria Informatica",
        description="Il corso di studio attuale dello studente."
    )
    preferences: str = Field(
        ..., 
        example="Mi piacerebbe studiare AI in una città grande con un clima mite e un basso costo della vita.",
        description="Descrizione in linguaggio naturale delle preferenze per la meta Erasmus."
    )

    class Config:
        # Aggiunge un esempio che sarà visibile nella documentazione automatica di FastAPI (/docs)
        json_schema_extra = {
            "example": {
                "course_of_study": "Economia e Management",
                "preferences": "Vorrei un'università prestigiosa in una capitale europea, possibilmente dove posso migliorare il mio inglese."
            }
        }


# =================================================================
#               MODELLI PER LA RISPOSTA IN OUTPUT
# =================================================================
# Questi modelli definiscono la struttura dei dati che il nostro
# backend invierà come risposta. FastAPI li userà per serializzare
# i dati in formato JSON.

class DestinationSuggestion(BaseModel):
    """
    Schema per una singola destinazione suggerita.
    """
    university_name: str = Field(..., example="Universidad Politécnica de Valencia")
    city: str = Field(..., example="Valencia, Spagna")
    recommended_courses: List[str] = Field(..., example=["Machine Learning", "Data Science Fundamentals"])
    reasoning: str = Field(..., description="Spiegazione del perché questa meta è un buon match.")
    affinity_score: int = Field(..., ge=1, le=100, description="Punteggio di affinità da 1 a 100.")


class StudentResponse(BaseModel):
    """
    Schema per la risposta finale, che contiene una lista di destinazioni.
    """
    destinations: List[DestinationSuggestion]