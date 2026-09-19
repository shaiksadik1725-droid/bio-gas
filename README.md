# LSTM-Based Biogas Monitoring & Feeding Control

An embedded-AI project that reads temperature, pH, and gas measurements from a microcontroller, trains an LSTM time-series model, predicts future gas behavior, and returns control decisions to the embedded system.

## Workflow
1. Sensor data is streamed through serial communication.
2. Temperature, pH, and gas readings are collected.
3. A MinMax scaler prepares the time series.
4. An LSTM learns recent gas behavior.
5. The saved model predicts the next gas value.
6. Rule-based logic converts measurements and predictions into control commands.

## Technology
Python, TensorFlow/Keras, Pandas, NumPy, scikit-learn, Joblib, PySerial, ESP32/Arduino firmware.

## Structure
```text
bio-gas/
├── ESP32/
├── LSTM_AI.py
├── predict.py
├── biogas_lstm_model.h5
└── biogas_scaler.pkl
```

## Training
Connect the sensor system to the configured serial port, then:

```bash
python LSTM_AI.py
```

## Prediction
```bash
python predict.py
```

## Future Improvements
- Move COM-port settings to configuration
- Save training datasets for reproducibility
- Add train/test evaluation rather than online-only fitting
- Add dashboard visualization
- Add safety interlocks and actuator acknowledgements

## Author
**Sadik Shaik**
