#include <WiFi.h>
#include <PubSubClient.h> // Biblioteca para comunicação MQTT (Nick O'Leary)
#include <ArduinoJson.h>  // v6 ou v7
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ============================================================================
// CONFIGURAÇÃO DA REDE WI-FI
// ============================================================================
// O ESP32 só conecta em redes de 2,4 GHz.
// Rede com página de login no navegador (captive portal): NÃO funciona com o ESP32.
//   -> Use o roteador do celular (2,4 GHz) ou peça à TI para liberar o MAC do ESP32
//      (aparece no Serial Monitor ao ligar).
const char* WIFI_SSID = "SUA_REDE_WIFI";       // Substitua pela sua rede
const char* WIFI_PASS = "SUA_SENHA_WIFI";      // Substitua pela sua senha

// Rede com usuário + senha NA PRÓPRIA CONEXÃO (WPA2-Enterprise / PEAP, tipo eduroam):
// descomente a linha abaixo e preencha os dados.
// #define USAR_WPA2_ENTERPRISE
#ifdef USAR_WPA2_ENTERPRISE
const char* EAP_IDENTIDADE = "seu_usuario";    // normalmente igual ao usuário
const char* EAP_USUARIO    = "seu_usuario";
const char* EAP_SENHA      = "sua_senha";
#endif

// ============================================================================
// CONFIGURAÇÃO DO BROKER MQTT (precisa ser igual ao back-end: src/backend/app/main.py)
// ============================================================================
const char* MQTT_SERVER = "broker.hivemq.com"; // Broker público para testes
const int   MQTT_PORT   = 1883;
// O broker público é compartilhado: o "cs7f3a" evita misturar com outros projetos.
#define TOPICO_BASE "campussmart/cs7f3a/sala101"
const char* TOPICO_TELEMETRIA = TOPICO_BASE "/telemetria";
const char* TOPICO_COMANDOS   = TOPICO_BASE "/comandos";
const char* TOPICO_STATUS     = TOPICO_BASE "/status";   // "online"/"offline" (Last Will)

// ============================================================================
// REGRAS DO SISTEMA
// ============================================================================
const unsigned long TEMPO_OCIOSIDADE_MS = 30000; // AUTO: carga fica ligada até 30 s após o último movimento
const unsigned long INTERVALO_TELEMETRIA_MS = 2000;
const float POTENCIA_AC_W = 1100.0;              // potência simulada do ar-condicionado ligado
const float TENSAO_V = 220.0;

// --- Configuração da Tela OLED (128x64 I2C) ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
bool oledOk = false;

// --- Instâncias de Rede ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// --- Mapeamento de Hardware ---
const int pinoSensor = 4;  // Entrada Digital: Sensor PIR de Presença
// Carga (ventoinhas = ar-condicionado simulado). Hoje: LED no GPIO 18. Com o módulo relé duplo:
//   IN1 -> GPIO 18 (ventoinha 1)   IN2 -> GPIO 19 (ventoinha 2)   VCC -> VIN (5 V)   GND -> GND
const int pinoRele1 = 18;  // canal 1 do relé (ou o LED atual)
const int pinoRele2 = 19;  // canal 2 do relé (segunda ventoinha). Use -1 se não houver.
// A maioria dos módulos relé azuis de 5 V liga com sinal LOW ("ativo em LOW").
// LED ligado direto no pino: false.  Módulo relé: normalmente true (se ficar invertido, troque).
const bool RELE_ATIVO_EM_LOW = false;
// LED da "luz da sala" (indicador de presença): acende quando o PIR detecta alguém, independente do app.
// Hoje o LED está no GPIO 18 (fazendo papel de AC). Quando o relé chegar, mude o fio do LED para o GPIO 23.
const int pinoLedPresenca = 23;  // use -1 se não houver LED de presença

// --- Protótipos ---
void acionarCarga(bool ligar);
void publicarTelemetriaMQTT(bool cargaEnergizada, bool acRodando);
void desenharTela(bool acRodando);
void telaInicial(int passo, const char* status);

// --- Variáveis Globais de Estado ---
String modoCarga = "AUTO";     // "AUTO", "ON", "OFF" (recebido via MQTT)
bool acHabilitado = true;      // ar-condicionado ligado/desligado pelo app (rotas ac/on e ac/cut)
String mensagemWeb = "";       // mensagem para o display (até 64 caracteres)
bool presenca = false;         // presença considerando o tempo de ociosidade
unsigned long ultimoMovimento = 0;
bool jaHouveMovimento = false;
unsigned long ultimoEnvioMQTT = 0;
unsigned long ultimaTentativaWiFi = 0;
unsigned long ultimaTentativaMQTT = 0;
int contadorAnimacao = 0;
float anguloVentoinha = 0;              // giro da ventoinha desenhada no OLED
int rolagemX = SCREEN_WIDTH;            // posição da mensagem rolando na última linha
unsigned long destaqueMensagemAte = 0;  // mostra a mensagem nova em tela cheia até este instante

// ============================================================================
// A fonte padrão do OLED não tem acentos: converte "ç ã é..." (UTF-8) em letras simples.
// ============================================================================
String semAcentos(const char* texto) {
  const char* de[]  = {"á","à","â","ã","ä","é","ê","è","í","ì","ó","ô","õ","ò","ú","ü","ù","ç",
                       "Á","À","Â","Ã","É","Ê","Í","Ó","Ô","Õ","Ú","Ç","º","ª"};
  const char* para[] = {"a","a","a","a","a","e","e","e","i","i","o","o","o","o","u","u","u","c",
                        "A","A","A","A","E","E","I","O","O","O","U","C","o","a"};
  String s = String(texto);
  for (unsigned int i = 0; i < sizeof(de) / sizeof(de[0]); i++) s.replace(de[i], para[i]);
  String limpo = "";
  for (unsigned int i = 0; i < s.length(); i++) {           // remove o que sobrar fora do ASCII
    char c = s.charAt(i);
    if ((unsigned char)c >= 32 && (unsigned char)c < 127) limpo += c;
  }
  return limpo;
}

// ============================================================================
// CALLBACK: EXECUTADO QUANDO O BACK-END ENVIA UM COMANDO
// Formato: {"modo_carga":"AUTO|ON|OFF", "ac":"ON|OFF", "mensagem_web":"texto"}
// ============================================================================
void callbackMQTT(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  if (error) {
    Serial.print(F("[MQTT] Comando inválido: "));
    Serial.println(error.c_str());
    return;
  }

  // Campos independentes: o comando pode trazer um ou todos.
  const char* modo = doc["modo_carga"].as<const char*>();     // nullptr se o campo não vier
  if (!modo) modo = doc["modo_led"].as<const char*>();         // nome antigo, mantido por compatibilidade
  if (modo) {
    String m = String(modo);
    m.toUpperCase();
    if (m == "AUTO" || m == "ON" || m == "OFF") modoCarga = m;
  }
  const char* ac = doc["ac"].as<const char*>();
  if (ac) {
    String a = String(ac);
    a.toUpperCase();
    if (a == "ON") acHabilitado = true;
    else if (a == "OFF") acHabilitado = false;
  }
  const char* msg = doc["mensagem_web"].as<const char*>();
  if (msg) {
    String nova = semAcentos(msg).substring(0, 64);
    if (nova.length() > 0 && nova != mensagemWeb) destaqueMensagemAte = millis() + 3500;  // mensagem nova: tela cheia
    mensagemWeb = nova;
    rolagemX = SCREEN_WIDTH;
  }

  Serial.printf("[MQTT] Comando: modo=%s ac=%s msg=\"%s\"\n", modoCarga.c_str(),
                acHabilitado ? "ON" : "OFF", mensagemWeb.c_str());
}

// ============================================================================
// WI-FI E MQTT SEM TRAVAR A PLACA
// Se a rede cair, o sensor e o modo AUTO continuam funcionando localmente.
// ============================================================================
void iniciarWiFi() {
  WiFi.mode(WIFI_STA);
#ifdef USAR_WPA2_ENTERPRISE
  WiFi.begin(WIFI_SSID, WPA2_AUTH_PEAP, EAP_IDENTIDADE, EAP_USUARIO, EAP_SENHA);
#else
  WiFi.begin(WIFI_SSID, WIFI_PASS);
#endif
}

void manterConexoes() {
  unsigned long agora = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (agora - ultimaTentativaWiFi > 10000) {   // tenta de novo a cada 10 s
      ultimaTentativaWiFi = agora;
      Serial.println(F("[Wi-Fi] Sem conexão. Tentando reconectar..."));
      WiFi.disconnect();
      iniciarWiFi();
    }
    return;
  }

  if (!mqttClient.connected() && agora - ultimaTentativaMQTT > 3000) {
    ultimaTentativaMQTT = agora;
    String clientId = "ESP32-CampusSmart-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print(F("[MQTT] Conectando ao broker..."));
    // Last Will: se o ESP32 cair, o broker publica "offline" no tópico de status.
    if (mqttClient.connect(clientId.c_str(), TOPICO_STATUS, 0, true, "offline")) {
      Serial.println(F(" conectado!"));
      mqttClient.publish(TOPICO_STATUS, "online", true);
      mqttClient.subscribe(TOPICO_COMANDOS);  // recebe também o último comando guardado (retain)
    } else {
      // -2 = não alcançou o broker (porta 1883 bloqueada na rede?); 5 = não autorizado
      Serial.printf(" falhou (estado %d). Nova tentativa em 3 s.\n", mqttClient.state());
    }
  }
}

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(pinoSensor, INPUT);
  pinMode(pinoRele1, OUTPUT);
  if (pinoRele2 >= 0) pinMode(pinoRele2, OUTPUT);
  acionarCarga(false);   // começa desligado (respeitando relé ativo em LOW)
  if (pinoLedPresenca >= 0) {
    pinMode(pinoLedPresenca, OUTPUT);
    digitalWrite(pinoLedPresenca, LOW);
  }

  oledOk = display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  if (!oledOk) {
    Serial.println(F("ERRO: Display OLED não encontrado! Seguindo sem display."));
  } else {
    telaInicial(0, "Conectando Wi-Fi");
  }

  Serial.print(F("[Wi-Fi] MAC do ESP32 (para a TI liberar): "));
  WiFi.mode(WIFI_STA);
  Serial.println(WiFi.macAddress());

  iniciarWiFi();
  unsigned long inicio = millis();
  int passo = 0;
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 15000) {  // espera no máximo 15 s
    telaInicial(passo++, "Conectando Wi-Fi");
    delay(150);
    if (passo % 4 == 0) Serial.print(".");
  }
  telaInicial(100, WiFi.status() == WL_CONNECTED ? "Wi-Fi conectado!" : "Sem Wi-Fi: modo local");
  delay(800);
  ultimaTentativaWiFi = millis();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(F("\n[Wi-Fi] Conectado! IP: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(F("\n[Wi-Fi] Não conectou. O sistema funciona offline e continua tentando."));
  }

  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(callbackMQTT);
  mqttClient.setBufferSize(512);
}

// ============================================================================
// LOOP
// ============================================================================
void loop() {
  manterConexoes();
  mqttClient.loop();

  // 1. Leitura do Sensor PIR com tempo de ociosidade
  unsigned long agora = millis();
  if (digitalRead(pinoSensor) == HIGH) {
    ultimoMovimento = agora;
    jaHouveMovimento = true;
  }
  presenca = jaHouveMovimento && (agora - ultimoMovimento < TEMPO_OCIOSIDADE_MS);

  // 2. Lógica da carga: ar-condicionado habilitado E (ON, ou AUTO com presença)
  bool cargaEnergizada = (modoCarga == "ON") || (modoCarga == "AUTO" && presenca);
  bool ligarCarga = acHabilitado && cargaEnergizada;
  acionarCarga(ligarCarga);
  if (pinoLedPresenca >= 0) digitalWrite(pinoLedPresenca, presenca ? HIGH : LOW);  // luz da sala segue a presença

  // 3. Telemetria a cada 2 s
  if (agora - ultimoEnvioMQTT >= INTERVALO_TELEMETRIA_MS) {
    ultimoEnvioMQTT = agora;
    publicarTelemetriaMQTT(cargaEnergizada, ligarCarga);
  }

  // 4. Tela OLED
  contadorAnimacao++;
  desenharTela(ligarCarga);

  delay(80);   // ~12 quadros por segundo no OLED (animação suave)
}

// ============================================================================
// PUBLICAÇÃO DA TELEMETRIA
// ============================================================================
void publicarTelemetriaMQTT(bool cargaEnergizada, bool acRodando) {
  if (!mqttClient.connected()) return;
  float potencia = acRodando ? POTENCIA_AC_W : 0.0;

  StaticJsonDocument<256> doc;
  doc["sala_id"] = "SALA_101";
  doc["ocupado"] = presenca;
  doc["modo"] = modoCarga;
  doc["ac_ligado"] = acHabilitado;
  doc["carga_ligada"] = cargaEnergizada;
  doc["potencia_w"] = potencia;
  doc["corrente_ma"] = (int)(potencia / TENSAO_V * 1000.0);

  char jsonBuffer[256];
  size_t n = serializeJson(doc, jsonBuffer, sizeof(jsonBuffer));
  mqttClient.publish(TOPICO_TELEMETRIA, (const uint8_t*)jsonBuffer, n, false);
}

// ============================================================================
// DESENHO DA INTERFACE NA TELA OLED (128x64)
//  +------------------------------+
//  | SALA 101          [wifi] (o) |  cabeçalho invertido: Wi-Fi e MQTT
//  |  .---.  AR COND.     1100W   |
//  |  | * |  ON          [AUTO]   |  ventoinha girando quando o AC está rodando
//  |  '---'  o Ocupada    [====]  |  AUTO: barra = tempo até desligar por ociosidade
//  | -----------------------------|
//  | mensagem do app rolando...   |
//  +------------------------------+
// ============================================================================
void textoCentralizado(const String& t, int y, int tamanho) {
  display.setTextSize(tamanho);
  int largura = t.length() * 6 * tamanho;
  display.setCursor(max(0, (SCREEN_WIDTH - largura) / 2), y);
  display.print(t);
}

// Tela de abertura com barra de progresso (usada enquanto conecta o Wi-Fi)
void telaInicial(int passo, const char* status) {
  if (!oledOk) return;
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextWrap(false);
  textoCentralizado("CAMPUS", 4, 2);
  textoCentralizado("SMART", 22, 2);
  // raio estilizado ao lado do nome
  display.fillTriangle(112, 6, 104, 20, 110, 20, SSD1306_WHITE);
  display.fillTriangle(108, 18, 114, 18, 106, 32, SSD1306_WHITE);
  textoCentralizado(String(status), 42, 1);
  display.drawRoundRect(14, 54, 100, 8, 3, SSD1306_WHITE);
  if (passo >= 100) {
    display.fillRoundRect(16, 56, 96, 4, 2, SSD1306_WHITE);
  } else {
    int x = 16 + (passo * 6) % 76;          // bloco "andando" dentro da barra
    display.fillRoundRect(x, 56, 20, 4, 2, SSD1306_WHITE);
  }
  display.display();
}

// Ventoinha com 3 pás. Gira quando "girando"; com X por cima se o AC foi desligado pelo app.
void desenharVentoinha(int cx, int cy, bool girando, bool habilitado) {
  display.drawCircle(cx, cy, 16, SSD1306_WHITE);
  if (girando) anguloVentoinha += 0.45;
  if (anguloVentoinha > 6.2832) anguloVentoinha -= 6.2832;
  for (int i = 0; i < 3; i++) {
    float a = anguloVentoinha + i * 2.0944;   // 120 graus entre as pás
    int x1 = cx + cos(a) * 13,        y1 = cy + sin(a) * 13;
    int x2 = cx + cos(a + 0.75) * 11, y2 = cy + sin(a + 0.75) * 11;
    display.fillTriangle(cx, cy, x1, y1, x2, y2, SSD1306_WHITE);
  }
  display.fillCircle(cx, cy, 3, SSD1306_BLACK);
  display.drawCircle(cx, cy, 3, SSD1306_WHITE);
  if (girando && contadorAnimacao % 4 < 2) {   // "vento" saindo
    display.drawPixel(cx + 19, cy - 6, SSD1306_WHITE);
    display.drawPixel(cx + 20, cy, SSD1306_WHITE);
    display.drawPixel(cx + 19, cy + 6, SSD1306_WHITE);
  }
  if (!habilitado) {
    display.drawLine(cx - 11, cy - 11, cx + 11, cy + 11, SSD1306_WHITE);
    display.drawLine(cx - 11, cy + 11, cx + 11, cy - 11, SSD1306_WHITE);
  }
}

void desenharCabecalho(bool w, bool m) {
  display.fillRect(0, 0, SCREEN_WIDTH, 11, SSD1306_WHITE);
  display.setTextSize(1);
  display.setTextColor(SSD1306_BLACK);
  display.setCursor(3, 2);
  display.print(F("SALA 101"));
  // Wi-Fi: 3 barrinhas (cheias = conectado; só contorno = sem Wi-Fi)
  for (int i = 0; i < 3; i++) {
    int h = 3 + i * 2, x = 101 + i * 4;
    if (w) display.fillRect(x, 9 - h, 3, h, SSD1306_BLACK);
    else display.drawRect(x, 9 - h, 3, h, SSD1306_BLACK);
  }
  // MQTT: bolinha cheia = conectado; piscando vazia = tentando
  if (m) display.fillCircle(121, 5, 3, SSD1306_BLACK);
  else if (contadorAnimacao % 10 < 5) display.drawCircle(121, 5, 3, SSD1306_BLACK);
  display.setTextColor(SSD1306_WHITE);
}

// Mensagem nova do app em tela cheia (por alguns segundos)
void desenharDestaqueMensagem() {
  display.fillRect(0, 0, SCREEN_WIDTH, 11, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(19, 2);
  display.print(F("MENSAGEM DO APP"));
  display.setTextColor(SSD1306_WHITE);
  display.setTextWrap(true);
  display.setCursor(0, 18);
  display.print(mensagemWeb);
  display.setTextWrap(false);
  if (contadorAnimacao % 6 < 3) display.drawRect(0, 12, SCREEN_WIDTH, 52, SSD1306_WHITE);  // moldura piscando
}

void desenharTela(bool acRodando) {
  if (!oledOk) return;
  display.clearDisplay();
  display.setTextWrap(false);
  bool w = WiFi.status() == WL_CONNECTED, m = mqttClient.connected();

  if (millis() < destaqueMensagemAte) {
    desenharDestaqueMensagem();
    display.display();
    return;
  }

  desenharCabecalho(w, m);
  desenharVentoinha(19, 33, acRodando, acHabilitado);

  // Ar-condicionado: estado e potência
  display.setTextSize(1);
  display.setCursor(44, 14);
  display.print(F("AR COND."));
  String pot = acRodando ? String((int)POTENCIA_AC_W) : String("0");
  pot += "W";
  display.setCursor(SCREEN_WIDTH - pot.length() * 6, 14);
  display.print(pot);

  display.setTextSize(2);
  display.setCursor(44, 24);
  display.print(acRodando ? F("ON") : F("OFF"));

  // Modo da carga numa "etiqueta"; fica cheia quando a carga está energizada
  display.setTextSize(1);
  int mx = 90, my = 25, mw = 36, mh = 13;
  bool chipCheio = (modoCarga == "ON") || (modoCarga == "AUTO" && presenca);
  if (chipCheio) display.fillRoundRect(mx, my, mw, mh, 4, SSD1306_WHITE);
  else display.drawRoundRect(mx, my, mw, mh, 4, SSD1306_WHITE);
  display.setTextColor(chipCheio ? SSD1306_BLACK : SSD1306_WHITE);
  display.setCursor(mx + (mw - modoCarga.length() * 6) / 2 + 1, my + 3);
  display.print(modoCarga);
  display.setTextColor(SSD1306_WHITE);

  // Presença: bonequinho + texto
  int px = 47, py = 44;
  if (presenca) {
    display.fillCircle(px, py - 2, 2, SSD1306_WHITE);            // cabeça
    display.drawLine(px, py, px, py + 4, SSD1306_WHITE);          // corpo
    display.drawLine(px - 3, py + 2, px + 3, py + 2, SSD1306_WHITE);
    display.drawLine(px, py + 4, px - 2, py + 7, SSD1306_WHITE);  // pernas
    display.drawLine(px, py + 4, px + 2, py + 7, SSD1306_WHITE);
  } else {
    display.drawCircle(px, py - 2, 2, SSD1306_WHITE);
    display.drawLine(px - 3, py + 6, px + 3, py + 6, SSD1306_WHITE);
  }
  display.setCursor(54, 42);
  display.print(presenca ? F("Ocupada") : F("Vazia"));

  // AUTO com presença: barra regressiva até desligar por ociosidade
  if (modoCarga == "AUTO" && presenca) {
    unsigned long passou = millis() - ultimoMovimento;
    unsigned long resta = passou < TEMPO_OCIOSIDADE_MS ? TEMPO_OCIOSIDADE_MS - passou : 0;
    display.drawRect(98, 43, 28, 6, SSD1306_WHITE);
    display.fillRect(99, 44, (int)(26UL * resta / TEMPO_OCIOSIDADE_MS), 4, SSD1306_WHITE);
  }

  // Linha de baixo: mensagem do app (rolando se for longa) ou status da conexão
  display.drawFastHLine(0, 53, SCREEN_WIDTH, SSD1306_WHITE);
  String rodape;
  if (mensagemWeb.length() > 0) rodape = mensagemWeb;
  else if (!w) rodape = "Sem Wi-Fi: modo local";
  else if (!m) rodape = "Conectando ao MQTT...";
  else rodape = "Online - CampusSmart";
  int larguraTexto = rodape.length() * 6;
  if (larguraTexto <= SCREEN_WIDTH) {
    display.setCursor((SCREEN_WIDTH - larguraTexto) / 2, 56);
  } else {
    rolagemX -= 2;
    if (rolagemX < -larguraTexto) rolagemX = SCREEN_WIDTH;
    display.setCursor(rolagemX, 56);
  }
  display.print(rodape);

  display.display();
}

// ============================================================================
// ACIONAMENTO DA CARGA (LED hoje / módulo relé duplo quando chegar)
// As duas ventoinhas seguem o mesmo estado (o "ar-condicionado" da sala).
// ============================================================================
void acionarCarga(bool ligar) {
  int nivel = (ligar != RELE_ATIVO_EM_LOW) ? HIGH : LOW;
  digitalWrite(pinoRele1, nivel);
  if (pinoRele2 >= 0) digitalWrite(pinoRele2, nivel);
}

