Setup Conda per questo progetto (Windows PowerShell)

Questi sono i passi consigliati per creare e collegare il progetto a un ambiente Conda su Windows (PowerShell). Il repository contiene un file `environment.yml` che usa `app/requirements.txt` per installare le dipendenze pip.

1) Apri PowerShell e assicurati che conda sia installato e raggiungibile (Anaconda o Miniconda).

2) (Opzionale) Se PowerShell non riconosce `conda`, esegui:

```powershell
# Esegui solo se non hai abilitato conda per PowerShell
conda init powershell; # poi chiudi e riapri PowerShell
```

3) Crea l'ambiente da `environment.yml` (nella root del progetto):

```powershell
# dalla cartella del progetto
conda env create -f .\environment.yml
```

4) Attiva l'ambiente:

```powershell
conda activate progetto-env
```

5) Verifica l'interprete e le dipendenze:

```powershell
python -V
pip list
```

Alternative: se preferisci non usare `environment.yml`, puoi creare un ambiente e installare le dipendenze con pip:

```powershell
conda create -n progetto-env python=3.11 pip -y
conda activate progetto-env
pip install -r .\app\requirements.txt
```

Configurare VS Code per usare l'ambiente Conda

- Apri VS Code nella cartella del progetto.
- Premi Ctrl+Shift+P e cerca "Python: Select Interpreter".
- Seleziona l'interprete che corrisponde a `progetto-env` (di solito in `C:\Users\<tuo_utente>\anaconda3\envs\progetto-env\python.exe` o percorso equivalente).

Verifiche rapide per l'app

- Avvia lo script principale o il server FastAPI (se usi `uvicorn`):

```powershell
uvicorn app.main:app --reload
```

Nota: se incontri problemi con permessi o con PATH, assicurati che la Shell sia stata chiusa e riaperta dopo `conda init powershell`.
