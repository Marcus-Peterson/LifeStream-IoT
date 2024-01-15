#include <ArduinoBLE.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <PulseSensorPlayground.h>

//If you are going to use this code, it is recommended to use the Arduino Rev 4
#define ONE_WIRE_BUS 2
const int PulseWire = A0;
int Threshold = 550;
PulseSensorPlayground pulseSensor;

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// GSR setup
const int GSRPin = A1;
const int numReadings = 10;
int gsrReadings[numReadings]; // circular buffer for GSR readings
int readIndex = 0; // current position in the buffer
long total = 0; // total of readings
int average = 0; // average of readings

BLEService healthService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEStringCharacteristic jsonCharacteristic("19B10010-E8F2-537E-4F6C-D104768A1214", BLENotify, 256);

void setup() {
  Serial.begin(9600);
  sensors.begin();
  pulseSensor.analogInput(PulseWire);
  pulseSensor.setThreshold(Threshold);
  pulseSensor.begin();
  
  // Initialize the GSR readings
  for (int thisReading = 0; thisReading < numReadings; thisReading++) {
    gsrReadings[thisReading] = 0;
  }

  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1);
  }
  
  BLE.setLocalName("LifeStream_IoT");
  BLE.setAdvertisedService(healthService);
  healthService.addCharacteristic(jsonCharacteristic);
  BLE.addService(healthService);
  BLE.advertise();
  
  Serial.println("Bluetooth device active, waiting for connections...");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());
    
    while (central.connected()) {
      sensors.requestTemperatures();
      float temperatureC = sensors.getTempCByIndex(0);
      total = total - gsrReadings[readIndex];
      gsrReadings[readIndex] = analogRead(GSRPin);
      total = total + gsrReadings[readIndex];
      readIndex = (readIndex + 1) % numReadings;
      average = total / numReadings;
      
      int bpm = pulseSensor.getBeatsPerMinute();
      
      StaticJsonDocument<256> doc;
      doc["temperature"] = temperatureC;
      doc["gsr"] = average; // Here we use the averaged GSR value
      doc["bpm"] = bpm;
      
      char jsonBuffer[256];
      serializeJson(doc, jsonBuffer);
      jsonCharacteristic.writeValue(jsonBuffer);
      
      delay(1000);
    }
    
    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
  }
}
