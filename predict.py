import numpy as np
import pandas as pd
import serial
import time
import joblib
from tensorflow.keras.models import load_model

# ----------------- CONFIG -----------------
PORT = 'COM3'
BAUD = 9600
SEQ_LEN = 20

TEMP_THRESHOLD = 30.0
PH_THRESHOLD = 3
GAS_THRESHOLD = 0.2
INVALID_TEMP = -127.0

MODEL_PATH = "biogas_lstm_model.h5"
SCALER_PATH = "biogas_scaler.pkl"

SERVO_DELAY = 5  # seconds delay before opening servo if GAS_DETECTED

# ----------------- INIT -----------------
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

# Load trained model (compile=False avoids version mismatch errors)
model = load_model(MODEL_PATH, compile=False)
scaler = joblib.load(SCALER_PATH)


data_buffer = []
last_gas_detected_time = None
servo_opened = False

# ----------------- DECISION FUNCTION -----------------
def feeding_decision(temp, ph, current_gas, predicted_gas):
    global last_gas_detected_time, servo_opened

    # Handle invalid sensor
    if temp == INVALID_TEMP:
        return "TEMP_SENSOR_ERROR"

    # GAS detected logic with delay
    if current_gas >= GAS_THRESHOLD:
        if last_gas_detected_time is None:
            last_gas_detected_time = time.time()
            servo_opened = False
            return "GAS_DETECTED"
        elif not servo_opened and time.time() - last_gas_detected_time >= SERVO_DELAY:
            servo_opened = True
            return "GAS_DETECTED_OPEN"
        else:
            return "GAS_DETECTED"

    # Temperature / pH checks
    if temp > TEMP_THRESHOLD:
        return "WAIT_LOW_TEMP"
    if ph < PH_THRESHOLD:
        return "ACIDIC_STOP"

    # Predicted gas check
    if predicted_gas < GAS_THRESHOLD:
        return "FEED_NOW"

    return "OPTIMAL"

# ----------------- MAIN LOOP -----------------
print("Live prediction started...")

while True:
    try:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()
            # print raw for debugging
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

            print(f"Temp: {temp:.2f}, pH: {ph:.2f}, Gas: {gas:.2f}")

            # Skip invalid temp sensor
            if temp == INVALID_TEMP:
                decision = "TEMP_SENSOR_ERROR"
                print(f"Decision: {decision}")
                ser.write((decision + "\n").encode())
                print("-------------")
                time.sleep(1)
                continue

            data_buffer.append([temp, ph, gas])
            if len(data_buffer) > SEQ_LEN:
                data_buffer.pop(0)

            # If not enough data for LSTM, use current reading
            if len(data_buffer) < SEQ_LEN:
                decision = feeding_decision(temp, ph, gas, gas)
                print(f"Decision (Warmup): {decision}")
                ser.write((decision + "\n").encode())
                print("-------------")
                time.sleep(1)
                continue

            # Prepare LSTM input
            recent_df = pd.DataFrame(data_buffer, columns=['temp', 'ph', 'gas'])
            scaled_recent = scaler.transform(recent_df)
            scaled_recent = np.expand_dims(scaled_recent, axis=0)

            pred = model.predict(scaled_recent, verbose=0)
            pred_scaled = float(pred[0][0])

            dummy_df = pd.DataFrame([[0, 0, pred_scaled]], columns=['temp', 'ph', 'gas'])
            predicted_gas = scaler.inverse_transform(dummy_df)[0, 2]

            decision = feeding_decision(temp, ph, gas, predicted_gas)

            print(f"Predicted Gas: {predicted_gas:.2f}")
            print(f"Decision: {decision}")

            ser.write((decision + "\n").encode())
            print("-------------")

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
