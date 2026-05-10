import numpy as np
import pandas as pd
import serial
import time
import joblib
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

PORT = 'COM3'
BAUD = 9600
SEQ_LEN = 20
TRAIN_SAMPLES = 120
MAX_BUFFER = 300
INVALID_TEMP = -127.0

MODEL_PATH = "biogas_lstm_model.h5"
SCALER_PATH = "biogas_scaler.pkl"

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

data_buffer = []

def create_sequences(data, seq_length=20):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length][2])
    return np.array(X), np.array(y)

def build_model():
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(SEQ_LEN, 3)),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

print("Training data collection started...")

while len(data_buffer) < TRAIN_SAMPLES:
    try:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()
            print("RAW:", line)

            if line.count(",") != 2:
                continue

            parts = line.split(",")

            try:
                temp = float(parts[0])
                ph = float(parts[1])
                gas = float(parts[2])
            except:
                continue

            if temp == INVALID_TEMP:
                print("Skipping invalid temp sample")
                continue

            data_buffer.append([temp, ph, gas])

            if len(data_buffer) > MAX_BUFFER:
                data_buffer.pop(0)

            print(f"Collected {len(data_buffer)}/{TRAIN_SAMPLES} -> Temp: {temp:.2f}, pH: {ph:.2f}, Gas: {gas:.2f}")

        time.sleep(0.2)

    except Exception as e:
        print("Error:", e)
        time.sleep(1)

print("Training model...")

df = pd.DataFrame(data_buffer, columns=['temp', 'ph', 'gas'])

scaler = MinMaxScaler()
scaled = scaler.fit_transform(df)

X, y = create_sequences(scaled, SEQ_LEN)

if len(X) == 0:
    print("Not enough sequence data to train.")
    ser.close()
    exit()

model = build_model()
model.fit(X, y, epochs=20, batch_size=16, verbose=1)

model.save(MODEL_PATH)
joblib.dump(scaler, SCALER_PATH)

print(f"Model saved to {MODEL_PATH}")
print(f"Scaler saved to {SCALER_PATH}")

ser.close()
