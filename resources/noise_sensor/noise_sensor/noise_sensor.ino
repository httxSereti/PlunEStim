//BLE
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

//OLED
#include <Wire.h>               // Only needed for Arduino 1.6.5 and earlier
#include "SSD1306Wire.h"        // legacy: #include "SSD1306.h"
SSD1306Wire display(0x3c, 5, 4);

//Sound
int adcVal = 0;
const int adcPin = 34;
const int sampleWindow = 100;
unsigned int sample;
byte noise_level;

//status
bool deviceConnected = false;
bool oldDeviceConnected = false;

//BLE
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"
BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;

//connect/disconnect action
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
    }
};



void InitBLE() {
  // Create the BLE Device
  BLEDevice::init("SOUND");

  // Create the BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create a BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_INDICATE
                    );

  // Create a BLE Descriptor
  pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();
  Serial.println("Waiting a client connection to notify...");
}


void setup() {
  Serial.begin(115200);
  Serial.println("Start");
  InitBLE();
  display.init();
  display.flipScreenVertically();
  display.setFont(ArialMT_Plain_10);
  noise_level = 0;
}


void loop() {

  //calc noise level
  unsigned long startMillis = millis();
  float peakToPeak = 0;
  unsigned int signalMax = 0;
  unsigned int signalMin = 4096;
  while (millis() - startMillis < sampleWindow)
  {
    sample = analogRead(adcPin);
    if (sample > signalMax) {
      signalMax = sample;
    }
    else if (sample < signalMin) {
      signalMin = sample;
    }
  }
  peakToPeak = signalMax - signalMin;                    // max - min = peak-peak amplitude
  int db = map(peakToPeak, 20, 900, 49.5, 90);
  Serial.println(db);
  int noise_level = (peakToPeak * 135 / 4096) - 8 ;
  if (noise_level < 0) {
    noise_level = 0;
  }

  // draw level bar
  display.clear();
  display.drawProgressBar(0, 32, 120, 10, noise_level);

  // draw the percentage level
  display.setTextAlignment(TEXT_ALIGN_CENTER);
  display.drawString(64, 15, String(noise_level) + "%");

  // display if connected
  if (deviceConnected ) {
    display.drawString(64, 5, "BT");
  }
  display.display();

  // notify changed value
  if (deviceConnected) {
    pCharacteristic->setValue((uint8_t*)&noise_level, 8);
    pCharacteristic->notify();
    delay(3); // bluetooth stack will go into congestion, if too many packets are sent, in 6 hours test i was able to go as low as 3ms
  }
  // disconnecting
  if (!deviceConnected && oldDeviceConnected) {
    delay(500); // give the bluetooth stack the chance to get things ready
    pServer->startAdvertising(); // restart advertising
    Serial.println("start advertising");
    oldDeviceConnected = deviceConnected;
  }
  // connecting
  if (deviceConnected && !oldDeviceConnected) {
    // do stuff here on connecting
    oldDeviceConnected = deviceConnected;
  }

  //pause
  delay(100);
}
