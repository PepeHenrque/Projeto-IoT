#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Configuração da Tela OLED (128x64 pixels)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Definição dos pinos
const int pinoSensor = 4;   // Sensor PIR no pino D4
const int pinoLed = 18;     // LED indicador no pino D18

int estadoSensor = 0;
int contadorAnimacao = 0;

void setup() {
  Serial.begin(115200); 
  
  pinMode(pinoSensor, INPUT); 
  pinMode(pinoLed, OUTPUT);   
  
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Falha ao encontrar o Display OLED SSD1306"));
    while(1);
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(20, 20);
  display.println(F("CAMPUSSMART"));
  display.setCursor(20, 35);
  display.println(F("Modo Eco Ativo"));
  display.display();

  delay(2000); 
}

void loop() {
  estadoSensor = digitalRead(pinoSensor);
  contadorAnimacao = (contadorAnimacao + 1) % 4;

  display.clearDisplay();
  display.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  
  display.setCursor(14, 4);
  display.setTextSize(1);
  display.print(F("=== CAMPUSSMART ==="));

  if (estadoSensor == HIGH) {
    digitalWrite(pinoLed, HIGH);
    
    // Status Ocupada
    display.setCursor(8, 18);
    display.setTextSize(2);
    display.println(F("OCUPADA"));

    // Simulação de gasto energético ativo (Ventoinha/Carga ligada)
    display.setCursor(8, 40);
    display.setTextSize(1);
    display.println(F("Carga: 1.5W (Ativo)"));
    
    display.setCursor(8, 52);
    display.println(F("Corrente: ~300mA"));

    // Animação de radar ativo
    if (contadorAnimacao == 0) {
      display.drawCircle(112, 28, 3, SSD1306_WHITE);
    } else if (contadorAnimacao == 1) {
      display.drawCircle(112, 28, 6, SSD1306_WHITE);
    } else {
      display.fillCircle(112, 28, 3, SSD1306_WHITE);
    }

  } else {
    digitalWrite(pinoLed, LOW);
    
    // Status Livre / Modo Economia
    display.setCursor(14, 18);
    display.setTextSize(2);
    display.println(F("LIVRE"));

    // Simulação de economia de energia
    display.setCursor(8, 40);
    display.setTextSize(1);
    display.println(F("Modo Economia: ON"));
    
    display.setCursor(8, 52);
    display.println(F("Poupanca: 100% (0W)"));

    // Ícone estático de repouso
    display.fillCircle(112, 28, 2, SSD1306_WHITE);
  }

  display.display();
  delay(250); 
}
