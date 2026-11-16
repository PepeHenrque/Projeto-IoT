#include <WiFi.h>
#include <PubSubClient.h> // Biblioteca para comunicação MQTT
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ============================================================================
// COMUNICAÇÃO HTTP ANTERIOR (DESATIVADA LINHA POR LINHA EM FAVOR DO MQTT)
// ============================================================================
// #include <HTTPClient.h> 
// const char* API_BASE_URL = "http://192.168.1.15:8000"; 
// ============================================================================

// --- Configurações da Rede Wi-Fi ---
const char* WIFI_SSID = "SUA_REDE_WIFI";       // Substitua pela sua rede
const char* WIFI_PASS = "SUA_SENHA_WIFI";      // Substitua pela sua senha

// --- Configurações do Broker MQTT ---
const char* MQTT_SERVER = "broker.hivemq.com"; // Broker público para testes
const int MQTT_PORT = 1883;
const char* TOPICO_TELEMETRIA = "campussmart/sala101/telemetria";
const char* TOPICO_COMANDOS = "campussmart/sala101/comandos";

// --- Configuração da Tela OLED (128x64 I2C) ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1 
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- Instâncias de Rede ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// --- Mapeamento de Hardware ---
const int pinoSensor = 4;  // Entrada Digital: Sensor PIR de Presença
const int pinoLed = 18;    // Saída Digital: LED / Módulo Relé (Ventoinha / Lâmpada)

// --- Variáveis Globais de Estado ---
int estadoSensor = 0;
int contadorAnimacao = 0;
String mensagemWeb = "";
String modoCarga = "AUTO"; // Opções recebidas via MQTT: "AUTO", "ON", "OFF"
unsigned long ultimoEnvioMQTT = 0;

// ============================================================================
// FUNÇÃO CALLBACK: EXECUTADA AUTOMATICAMENTE QUANDO O BACKEND ENVIA UM COMANDO
// ============================================================================
void callbackMQTT(char* topic, byte* payload, unsigned int length) {
  String mensagem = "";
  for (int i = 0; i < length; i++) {
    mensagem += (char)payload[i];
  }
  
  StaticJsonDocument<300> doc;
  DeserializationError error = deserializeJson(doc, mensagem);
  
  if (!error) {
    if (doc.containsKey("modo_carga")) {
      modoCarga = doc["modo_carga"].as<String>();
    }
    if (doc.containsKey("mensagem_web")) {
      mensagemWeb = doc["mensagem_web"].as<String>();
    }
  }
}

// ============================================================================
// GARANTE A CONEXÃO CONTÍNUA COM O BROKER MQTT
// ============================================================================
void reconectarMQTT() {
  while (!mqttClient.connected()) {
    Serial.print(F("Conectando ao Broker MQTT..."));
    String clientId = "ESP32-CampusSmart-" + String(random(0xffff), HEX);
    
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println(F(" Conectado com sucesso!"));
      mqttClient.subscribe(TOPICO_COMANDOS); // Inscreve-se para receber comandos instantâneos
    } else {
      Serial.print(F(" Falha. Erro = "));
      Serial.print(mqttClient.state());
      Serial.println(F(" Tentando novamente em 2 segundos..."));
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(pinoSensor, INPUT);
  pinMode(pinoLed, OUTPUT);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("ERRO: Display OLED não encontrado!"));
    while (1); 
  }

  // Tela Inicial
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(20, 15);
  display.println(F("CAMPUSSMART"));
  display.setCursor(10, 35);
  display.println(F("Conectando Wi-Fi..."));
  display.display();

  // Conexão Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(F("\n[Wi-Fi] Conectado!"));

  // Configuração do Cliente MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(callbackMQTT);
}

void loop() {
  if (!mqttClient.connected()) {
    reconectarMQTT();
  }
  mqttClient.loop(); // Mantém a escuta de pacotes MQTT ativa sem travar a placa

  // 1. Leitura do Sensor PIR
  estadoSensor = digitalRead(pinoSensor);
  contadorAnimacao = (contadorAnimacao + 1) % 4;

  // 2. Envio de Telemetria via MQTT a cada 2 segundos
  if (millis() - ultimoEnvioMQTT > 2000) {
    publicarTelemetriaMQTT(estadoSensor == HIGH);
    ultimoEnvioMQTT = millis();
  }

  // 3. Lógica de Acionamento da Carga (Ventoinha / Lâmpada no Pino D18)
  bool ligarCarga = false;

  if (modoCarga == "ON") {
    ligarCarga = true;                    // Forçado via Web
  } else if (modoCarga == "OFF") {
    ligarCarga = false;                   // Desligado via Web
  } else {
    ligarCarga = (estadoSensor == HIGH); // Modo AUTO: Depende do PIR
  }

  digitalWrite(pinoLed, ligarCarga ? HIGH : LOW);

  // 4. Renderização da Tela OLED
  desenharTela(ligarCarga);

  delay(250); 
}

// ============================================================================
// PUBLICAÇÃO DA TELEMETRIA PARA O TÓPICO MQTT
// ============================================================================
void publicarTelemetriaMQTT(bool ocupado) {
  StaticJsonDocument<200> doc;
  doc["sala_id"] = "SALA_101";
  doc["ocupado"] = ocupado;
  doc["potencia_w"] = ocupado ? 1.5 : 0.0;
  doc["corrente_ma"] = ocupado ? 300 : 0;

  char jsonBuffer[200];
  serializeJson(doc, jsonBuffer);
  mqttClient.publish(TOPICO_TELEMETRIA, jsonBuffer);
}

// ============================================================================
// DESENHO DA INTERFACE NA TELA OLED
// ============================================================================
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
  display.println(modoCarga);

  if (mensagemWeb.length() > 0) {
    display.setCursor(8, 50);
    
    // ========================================================================
    // RECURSO DE ÁUDIO NO OLED (COMENTADO LINHA POR LINHA)
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
// CONTROLE DE MÓDULO RELÉ DUPLO / SEGUNDA VENTOINHA (COMENTADO PARA O FUTURO)
// ============================================================================
// const int pinoRelesecondario = 19;
// void controlarVentoinhaFisica(bool estado) {
//   digitalWrite(pinoRelesecondario, estado ? HIGH : LOW);
// }
// ============================================================================
