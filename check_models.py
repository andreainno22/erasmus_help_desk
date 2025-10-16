import google.generativeai as genai
from dotenv import load_dotenv
import os

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Configura l'API di Google
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Errore: GOOGLE_API_KEY non trovata nel file .env")
else:
    genai.configure(api_key=api_key)

    print("--- Modelli disponibili che supportano 'generateContent' ---\n")
    
    # Itera su tutti i modelli e stampa quelli pertinenti
    for model in genai.list_models():
        # Controlliamo se il metodo 'generateContent' è supportato dal modello
        if 'generateContent' in model.supported_generation_methods:
            print(f"- {model.name}")
