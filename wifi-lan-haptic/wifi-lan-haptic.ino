#include <WiFi.h>
#include <WebSocketsServer.h>
#include <DFRobotDFPlayerMini.h>

// --- WiFi Config ---
const char* ssid     = "wahoo";
const char* password = "";

// --- DFPlayer ---
HardwareSerial dfSerial(1);
DFRobotDFPlayerMini myDFPlayer;

// --- WebSocket ---
WebSocketsServer webSocket(81);

// --- State ---
String state = "idle";

// -------------------------------------------------------

void onWebSocketEvent(uint8_t client, WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) {
    Serial.println("Client connected");
  }
  else if (type == WStype_DISCONNECTED) {
    Serial.println("Client disconnected");
    state = "idle";  // safe fallback on disconnect
  }
  else if (type == WStype_TEXT) {
    state = String((char*)payload);
    Serial.println("State -> " + state);
  }
}

// -------------------------------------------------------

void setup() {
  Serial.begin(115200);

  // DFPlayer
  dfSerial.begin(9600, SERIAL_8N1, 4, 5);
  delay(1000);
  if (!myDFPlayer.begin(dfSerial, true, false)) {
    Serial.println("DFPlayer failed!");
  } else {
    Serial.println("DFPlayer ready");
    myDFPlayer.volume(30);
  }

  // WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP().toString());

  // WebSocket
  webSocket.begin();
  webSocket.onEvent(onWebSocketEvent);
  Serial.println("WebSocket started on port 81");
}

// -------------------------------------------------------

void loop() {
  webSocket.loop();  // must always run first

  if (state == "idle") {
    myDFPlayer.pause();

  } else if (state == "buzz") {
    myDFPlayer.play(3);
    delay(500);
    myDFPlayer.pause();
    delay(100);

  } else if (state == "pulse") {
    myDFPlayer.play(3);
    delay(200);
    myDFPlayer.pause();
    delay(100);

  } else if (state == "long") {
    myDFPlayer.play(3);
    delay(1000);
    myDFPlayer.pause();
    delay(500);
  }
}