from fastapi import FastAPI
import joblib
import pandas as pd
import os

app = FastAPI()

MODEL_PATH = "models/parking_rf_model.pkl"

# Cargar el modelo al arrancar el servidor
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    raise FileNotFoundError(f"Modelo no encontrado en {MODEL_PATH}")

@app.post("/predict")
def predict(data: dict):
    df = pd.DataFrame([data])
    pred = model.predict(df)[0]
    return {"prediction": float(pred)}
