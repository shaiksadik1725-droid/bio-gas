#define BLYNK_TEMPLATE_ID "TMPL6MSOO_3rv"
#define BLYNK_TEMPLATE_NAME "BioGas"

#include <WiFi.h>
#include <ESP32Servo.h>
#include <BlynkSimpleEsp32.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define TEMP_PIN   14
#define PH_PIN     35
#define GAS_PIN    32
#define GREEN_LED  2
#define RED_LED    5
#define SERVO_PIN  15

Servo myServo;

char auth[] = "jLTk4opnRl5S1NFJpzz5vOBKq1XtOjgl";
char ssid[] = "JAZ_LR";
char pass[] = "55512006";

float gasThreshold  = 1.5;
float tempThreshold = 30.0;
float phThreshold   = 6.5;

unsigned long lastAlertTime = 0;
unsigned long alertCooldown = 10000;
unsigned long lastSensorTime = 0;

bool gasDetectedPending = false;
unsigned long gasDetectedTime = 0;

OneWire oneWire(TEMP_PIN);
DallasTemperature tempSensor(&oneWire);

void setup() {
  Serial.begin(9600);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, 500, 2400);
  myServo.write(0);
  tempSensor.begin();
  Blynk.begin(auth, ssid, pass);
}

float readTemperature() {
  tempSensor.requestTemperatures();
  float temp = tempSensor.getTempCByIndex(0);
  if (temp == DEVICE_DISCONNECTED_C) return -127.0;
  return temp;
}
float readPH() {
  int val = analogRead(PH_PIN);
  float voltage = val * (3.3 / 4095.0);
  float ph = 3 + ((2.5 - voltage) * 3.5);
  return ph;
}
float readGas() {
  int val = analogRead(GAS_PIN);
  return (val / 4095.0) * 5.0;
}

void sendAlert(String eventName, String message) {
  if (millis() - lastAlertTime > alertCooldown) {
    Blynk.logEvent(eventName, message);
    lastAlertTime = millis();
  }
}

void loop() {
  Blynk.run();

  if (millis() - lastSensorTime >= 1000) {
    lastSensorTime = millis();
    float temp = readTemperature();
    float ph = readPH();
    float gas = readGas();
    Serial.print(temp, 2);
    Serial.print(",");
    Serial.print(ph, 2);
    Serial.print(",");
    Serial.println(gas, 2);
    Blynk.virtualWrite(V0, temp);
    Blynk.virtualWrite(V1, ph);
    Blynk.virtualWrite(V2, gas);
    if (temp == -127.0) sendAlert("red_alert2", "Temperature probe disconnected.");

    if (Serial.available()) {
      String decision = Serial.readStringUntil('\n');
      decision.trim();

      if (gasDetectedPending) {
        if (decision == "GAS_DETECTED") gasDetectedTime = millis();
      } else {
        if (decision == "GAS_DETECTED") {
          gasDetectedPending = true;
          gasDetectedTime = millis();
          digitalWrite(GREEN_LED, HIGH);
          digitalWrite(RED_LED, LOW);
          myServo.write(90);
          sendAlert("gas_detected", "Bio-Gas detected.");
        }
        else if (decision == "FEED_NOW" || decision == "OPTIMAL") {
          digitalWrite(GREEN_LED, HIGH);
          digitalWrite(RED_LED, LOW);
          myServo.write(90);
        }
        else if (decision == "ACIDIC_STOP") {
          digitalWrite(GREEN_LED, LOW);
          digitalWrite(RED_LED, HIGH);
          myServo.write(0);
          sendAlert("red_alert", "Red alert: pH low / acidic condition detected.");
        }
        else if (decision == "WAIT_LOW_TEMP") {
          digitalWrite(GREEN_LED, LOW);
          digitalWrite(RED_LED, HIGH);
          myServo.write(0);
          sendAlert("red_alert2", "Red alert: Temperature issue detected.");
        }
        else if (decision == "TEMP_SENSOR_ERROR") {
          digitalWrite(GREEN_LED, LOW);
          digitalWrite(RED_LED, HIGH);
          myServo.write(0);
          sendAlert("red_alert2", "Temperature probe disconnected.");
        }
      }
    }
  }

  if (gasDetectedPending && millis() - gasDetectedTime >= 5000) {
    gasDetectedPending = false;
    sendAlert("GAS_DETECTED_OPEN", "Bio-Gas detection confirmed.");
  }
}
