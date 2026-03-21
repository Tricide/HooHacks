#include "DFRobotDFPlayerMini.h"
#include <WiFi.h>
#include <WebSocketsServer.h> 

HardwareSerial dfSerial(1);
DFRobotDFPlayerMini myDFPlayer;

const char* ssid     = "ESP32-Vibrator";
const char* password = "12345678";

WebSocketsServer webSocket(81);

String state = "stop";

void onWebSocketEvent(uint8_t client, WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_TEXT) {
    String cmd = String((char*)payload);
    Serial.println("Received: " + cmd);
    state = cmd;
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  
  Serial.begin(115200);
  delay(2000); // long delay to let everything stabilize
  dfSerial.begin(9600, SERIAL_8N1, 4, 5);

  Serial.println("Starting...");

  if (!myDFPlayer.begin(dfSerial, true, false)) {
    Serial.println("Init failed. Continuing anyway to read errors...");
  } else {
    Serial.println("Init OK!");
    myDFPlayer.volume(30);
  }

  WiFi.softAP(ssid, password);
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP()); // usually 192.168.4.1

  webSocket.begin();
  webSocket.onEvent(onWebSocketEvent);
  Serial.println("WebSocket server started on port 81");
}

void loop() {
  webSocket.loop();

  if (state == "buzz")  triggerHaptic();
  if (state == "stop")  stopHaptic();
}

void triggerHaptic() {
  // your DFPlayer or motor code here
  digitalWrite(LED_BUILTIN, HIGH);
  myDFPlayer.play(3);  // burst on
  delay(200);
  myDFPlayer.pause();  // burst off
  delay(100);
}

void stopHaptic() {
  digitalWrite(LED_BUILTIN, LOW);
  myDFPlayer.pause();  // burst off
}
