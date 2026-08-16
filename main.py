from fastapi import FastAPI
import joblib
import pandas as pd
import os

app = FastAPI()

MODEL_PATH = "models/parking_rf_model.pkl"
MODEL_PATH_FUTURE = "models/parking_rf_model_predictor.pkl"

# Cargar el modelo al arrancar el servidor
if os.path.exists(MODEL_PATH):
    model_now = joblib.load(MODEL_PATH)
else:
    raise FileNotFoundError(f"Modelo no encontrado en {MODEL_PATH}")
    
if os.path.exists(MODEL_PATH_FUTURE):
    model_future = joblib.load(MODEL_PATH_FUTURE)
else:
    raise FileNotFoundError(f"Modelo no encontrado en {MODEL_PATH_FUTURE}")

@app.post("/predict_now")
def predict_now(data: dict):
    df = pd.DataFrame([data])
    pred = model_now.predict(df)[0]
    return {"prediction": float(pred)}

@app.post("/predict_future")
def predict_future(features: dict):
    df = pd.DataFrame([features])
    pred = model_future.predict(df)[0]
    return {"prediction": float(pred)}
