#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ============================================================================
// RECURSOS FUTUROS / EXPERIMENTAIS (DESATIVADOS PARA O MVP - LINHA COMENTADA)
// #include <PubSubClient.h> // Habilitar caso vá utilizar Broker MQTT no ESP32
// ============================================================================

// --- Configurações da Rede Wi-Fi ---
const char* WIFI_SSID = "SUA_REDE_WIFI";       
const char* WIFI_PASS = "SUA_SENHA_WIFI";      

// --- Endereço do Backend FastAPI ---
const char* API_BASE_URL = "http://192.168.1.15:8000"; 

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1 
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

const int pinoSensor = 4;  
const int pinoLed = 18;    

int estadoSensor = 0;
int contadorAnimacao = 0;
String mensagemWeb = "";
String modoLedWeb = "AUTO"; 

void setup() {
  Serial.begin(115200);

  pinMode(pinoSensor, INPUT);
  pinMode(pinoLed, OUTPUT);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("ERRO: Display OLED SSD1306 não encontrado!"));
    while (1); 
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(20, 15);
  display.println(F("CAMPUSSMART"));
  display.setCursor(10, 35);
  display.println(F("Conectando Wi-Fi..."));
  display.display();

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(F("\n[Wi-Fi] Conectado com sucesso!"));
}

void loop() {
  estadoSensor = digitalRead(pinoSensor);
  contadorAnimacao = (contadorAnimacao + 1) % 4;

  if (WiFi.status() == WL_CONNECTED) {
    comunicarComAPI(estadoSensor == HIGH);
  }

  bool ligarCarga = false;

  if (modoLedWeb == "ON") {
    ligarCarga = true;                    
  } else if (modoLedWeb == "OFF") {
    ligarCarga = false;                   
  } else {
    ligarCarga = (estadoSensor == HIGH); 
  }

  digitalWrite(pinoLed, ligarCarga ? HIGH : LOW);

  desenharTela(ligarCarga);

  delay(300); 
}

void comunicarComAPI(bool ocupado) {
  HTTPClient http;
  String url = String(API_BASE_URL) + "/api/v1/telemetria";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<200> doc;
  doc["sala_id"] = "SALA_101";
  doc["ocupado"] = ocupado;
  doc["potencia_w"] = ocupado ? 1.5 : 0.0;
  doc["corrente_ma"] = ocupado ? 300 : 0;

  String requestBody;
  serializeJson(doc, requestBody);

  int httpResponseCode = http.POST(requestBody);

  if (httpResponseCode > 0) {
    String response = http.getString();
    StaticJsonDocument<300> resDoc;
    DeserializationError err = deserializeJson(resDoc, response);

    if (!err) {
      if (resDoc.containsKey("mensagem_web")) {
        mensagemWeb = resDoc["mensagem_web"].as<String>();
      }
      if (resDoc.containsKey("modo_led")) {
        modoLedWeb = resDoc["modo_led"].as<String>();
      }
    }
  }
  http.end();
}

void desenharTela(bool cargaAtiva) {
  display.clearDisplay();
  display.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);

  display.setCursor(12, 4);
  display.setTextSize(1);
  display.print(F("=== CAMPUSSMART ==="));

  display.setCursor(8, 18);
  display.setTextSize(2);
  display.println(cargaAtiva ? F("CARGA: ON") : F("CARGA: OFF"));

  display.setCursor(8, 38);
  display.setTextSize(1);
  display.print(F("Modo: "));
  display.println(modoLedWeb);

  if (mensagemWeb.length() > 0) {
    display.setCursor(8, 50);
    
    // ========================================================================
    // LINHA DE TRATAMENTO DE ÁUDIO NO OLED (COMENTADA LINHA POR LINHA)
    // if (mensagemWeb == "AVISO DE VOZ!") {
    //   display.print(F("🔊 FALANDO..."));
    // } else {
    //   display.print(F("WEB: "));
    //   display.println(mensagemWeb.substring(0, 12));
    // }
    // ========================================================================

    display.print(F("WEB: "));
    display.println(mensagemWeb.substring(0, 12)); 
  }

  if (cargaAtiva) {
    if (contadorAnimacao % 2 == 0) {
      display.fillCircle(114, 28, 3, SSD1306_WHITE);
    } else {
      display.drawCircle(114, 28, 5, SSD1306_WHITE);
    }
  } else {
    display.fillCircle(114, 28, 2, SSD1306_WHITE);
  }

  display.display();
}

// ============================================================================
// BLOCO FUTURO: CALLBACK MQTT (COMENTADO LINHA POR LINHA)
// void callbackMQTT(char* topic, byte* payload, unsigned int length) {
//   String mensagem = "";
//   for (int i = 0; i < length; i++) {
//     mensagem += (char)payload[i];
//   }
// }
// ============================================================================
