# -*- coding: utf-8 -*-

import os
from pymongo import MongoClient
import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib
import lightgbm as lgb

# ============================
# 1. Conexión a MongoDB
# ============================

MONGO_URI = os.environ["DATABASE_URL"]   # GitHub Actions lo inyecta como secret
client = MongoClient(MONGO_URI)
db = client["blog"]

po = db["ParkingOccupancy"]
p = db["Parking"]

po_data = list(po.find())
p_data = list(p.find())

df_po = pd.DataFrame(po_data)
df_p = pd.DataFrame(p_data)

# ============================
# 2. Preprocesamiento
# ============================

df_po["moment"] = pd.to_datetime(df_po["moment"])

df_po["hour"] = df_po["moment"].dt.hour
df_po["day_week"] = df_po["moment"].dt.dayofweek
df_po["is_weekend"] = df_po["day_week"] > 4
df_po["month"] = df_po["moment"].dt.month

# Capacidad por parking
capacity_by_parking = df_po.groupby("parkingId")["free"].max()
df_po["capacity"] = df_po["parkingId"].map(capacity_by_parking)

df_po = df_po.sort_values("moment")

# ============================
# 3. Generación de lags
# ============================

def compute_lags_for_group(group):
    # Ordenar por fecha dentro del parking
    group = group.sort_values("moment").set_index("moment")

    def get_prev_value(t, hours):
        target = t - timedelta(hours=hours)
        prev = group[group.index <= target]
        if len(prev) == 0:
            return None
        return prev.iloc[-1]["free"]

    group["lag_1h"] = group.index.map(lambda t: get_prev_value(t, 1))
    group["lag_2h"] = group.index.map(lambda t: get_prev_value(t, 2))
    group["lag_3h"] = group.index.map(lambda t: get_prev_value(t, 3))
    group["lag_24h"] = group.index.map(lambda t: get_prev_value(t, 24))

    group["trend_1h"] = group["free"] - group["lag_1h"]
    group["trend_3h"] = group["free"] - group["lag_3h"]
    group["trend_6h"] = group["free"] - group.index.map(lambda t: get_prev_value(t, 6))

    return group.reset_index()

def generate_lags(df):
    return df.groupby("parkingId").apply(compute_lags_for_group).reset_index(drop=True)



df_po_final = generate_lags(df_po)

# ============================
# 4. Separación X / y
# ============================

X = df_po_final.drop(columns=["free", "_id", "moment"])
y = df_po_final["free"]

# ============================
# 5. Entrenamiento del modelo
# ============================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = lgb.LGBMRegressor(
    n_estimators=600,          # más árboles pero más pequeños
    learning_rate=0.03,        # más suave, mejor generalización
    max_depth=-1,              # deja que LightGBM decida
    num_leaves=64,             # equilibrio entre precisión y tamaño
    min_child_samples=20,      # evita overfitting
    subsample=0.8,             # bagging
    subsample_freq=1,          # activa bagging
    colsample_bytree=0.8,      # reduce correlación entre árboles
    reg_alpha=0.1,             # L1 regularization
    reg_lambda=0.2,            # L2 regularization
    random_state=42
)


model.fit(X_train, y_train)

# ============================
# 6. Guardar modelo
# ============================
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/parking_rf_model.pkl")


print("Modelo entrenado y guardado correctamente.")
print(f"Precisión en el conjunto de prueba: {model.score(X_test, y_test):.4f}")

print("Validación del modelo en el conjunto de validación:")

Y_test_pred = model.predict(X_test)

rmse = np.sqrt(np.mean((Y_test_pred - y_test) ** 2))
print(f"RMSE en el conjunto de prueba: {rmse:.4f}")

mae = np.mean(np.abs(Y_test_pred - y_test))
print(f"MAE en el conjunto de prueba: {mae:.4f}")


import pandas as pd
import requests
import json

# Cargar una fila del conjunto de validación
sample = X_test.iloc[0].to_dict()   # primera fila

# Endpoint de Render
url = "https://maestropixel-api.onrender.com/predict_now"

# Enviar la petición
response = requests.post(url, json=sample)

print("Input enviado:", sample)
print("Predicción:", response.json())

# ============================
# 7. Creación de modelo predictor
# ============================


# ============================
# 8. Feature engineering para el modelo predictor
# ============================

# Suponemos que tu df tiene:
# parkingId, moment, free, day_week, hour

# 1) Media por parking y hora
mean_hour = (
    df_po.groupby(["parkingId", "hour"])["free"]
      .agg(["mean", "std"])
      .reset_index()
      .rename(columns={"mean": "mean_free_hour_parking",
                       "std": "std_free_hour_parking"})
)

# 2) Media por parking, día de semana y hora
mean_dow_hour = (
    df_po.groupby(["parkingId", "day_week", "hour"])["free"]
      .agg(["mean", "std"])
      .reset_index()
      .rename(columns={"mean": "mean_free_hour_dow_parking",
                       "std": "std_free_hour_dow_parking"})
)

# 3) Unimos estas medias al dataset original
df_po_final_predictor = df_po.merge(mean_hour, on=["parkingId", "hour"], how="left")
df_po_final_predictor = df_po.merge(mean_dow_hour, on=["parkingId", "day_week", "hour"], how="left")


X_2 = df_po_final_predictor.drop(columns=["free", "_id", "moment"])
y_2 = df_po_final_predictor["free"]

X2_train, X2_test, y2_train, y2_test = train_test_split(
    X_2, y_2, test_size=0.2, random_state=42
)

model2 = lgb.LGBMRegressor(
    n_estimators=600,          # más árboles pero más pequeños
    learning_rate=0.03,        # más suave, mejor generalización
    max_depth=-1,              # deja que LightGBM decida
    num_leaves=64,             # equilibrio entre precisión y tamaño
    min_child_samples=20,      # evita overfitting
    subsample=0.8,             # bagging
    subsample_freq=1,          # activa bagging
    colsample_bytree=0.8,      # reduce correlación entre árboles
    reg_alpha=0.1,             # L1 regularization
    reg_lambda=0.2,            # L2 regularization
    random_state=42
)


print(f"Entrenando modelo predictor con {X2_train.iloc[0].to_dict()}")

model2.fit(X2_train, y2_train)

joblib.dump(model2, "models/parking_rf_model_predictor.pkl")

print("Modelo entrenado y guardado correctamente.")
print(f"Precisión en el conjunto de prueba: {model2.score(X2_test, y2_test):.4f}")

print("Validación del modelo en el conjunto de validación:")

Y2_test_pred = model2.predict(X2_test)

rmse = np.sqrt(np.mean((Y2_test_pred - y2_test) ** 2))
print(f"RMSE en el conjunto de prueba del modelo predictor: {rmse:.4f}")

mae = np.mean(np.abs(Y2_test_pred - y2_test))
print(f"MAE en el conjunto de prueba del modelo predictor: {mae:.4f}")

# Cargar una fila del conjunto de validación
sample2 = X2_test.iloc[0].to_dict()   # primera fila

url2 = "https://maestropixel-api.onrender.com/predict_future"

# Enviar la petición
response = requests.post(url2, json=sample2)

print("Input enviado:", sample2)
print("Predicción:", response.json())
