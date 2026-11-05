#include <Wire.h>             // Comunicação I2C entre ESP32 e a tela
#include <Adafruit_GFX.h>       // Biblioteca gráfica base (formas, fontes, pixels)
#include <Adafruit_SSD1306.h>   // Driver específico para o display OLED SSD1306

// Configuração da Tela OLED (128x64 pixels)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1      // Usa o pino de reset padrão do ESP32 (-1)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);


const int pinoSensor = 4;     // Pino D4: Entrada do sinal do Sensor PIR
const int pinoLed = 18;       // Pino D18: Saída do LED indicador de movimento

// Variáveis de controle de fluxo
int estadoSensor = 0;         // Guarda a leitura digital do PIR (HIGH/LOW)
int contadorAnimacao = 0;     // Incrementador dos quadros da animação (0 a 3)

void setup() {
  Serial.begin(115200);       
  
  pinMode(pinoSensor, INPUT); // Configura o PIR para enviar dados ao ESP32
  pinMode(pinoLed, OUTPUT);   // Configura o pino do LED para enviar tensão
  
  // Inicializa o display OLED no endereço I2C padrão 0x3C
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Falha ao encontrar o Display OLED SSD1306"));
    while(1);                 // Loop infinito para travar o programa se a tela falhar
  }

  // Tela de apresentação / Inicialização do sistema
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(20, 20);
  display.println(F("CAMPUSSMART"));
  display.setCursor(20, 35);
  display.println(F("Modo Eco Ativo"));
  display.display();

  delay(2000);                // Aguarda 2 segundos para estabilização inicial do sensor
}

void loop() {
  // Leitura do estado atual do sensor PIR
  estadoSensor = digitalRead(pinoSensor);
  
  // Avança o quadro da animação (módulo 4 faz o valor alternar entre 0, 1, 2 e 3)
  contadorAnimacao = (contadorAnimacao + 1) % 4;

  // Limpa o buffer da tela para desenhar o novo quadro
  display.clearDisplay();
  
  // Desenha a moldura retangular nas bordas (x=0, y=0 até 128x64)
  display.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  
  // Cabeçalho fixo do projeto
  display.setCursor(14, 4);
  display.setTextSize(1);
  display.print(F("=== CAMPUSSMART ==="));

  // --- LÓGICA DE PRESENÇA DETECTADA (SALA OCUPADA) ---
  if (estadoSensor == HIGH) {
    digitalWrite(pinoLed, HIGH); // Liga o LED indicador de movimento
    
    // Imprime status principal
    display.setCursor(8, 18);
    display.setTextSize(2);
    display.println(F("OCUPADA"));

    // Exibe telemetria de consumo estimado da carga
    display.setCursor(8, 40);
    display.setTextSize(1);
    display.println(F("Carga: 1.5W (Ativo)"));
    
    display.setCursor(8, 52);
    display.println(F("Corrente: ~300mA"));

    // Animação de radar (desenha círculos de tamanhos diferentes dependendo do contador)
    if (contadorAnimacao == 0) {
      display.drawCircle(112, 28, 3, SSD1306_WHITE);
    } else if (contadorAnimacao == 1) {
      display.drawCircle(112, 28, 6, SSD1306_WHITE);
    } else {
      display.fillCircle(112, 28, 3, SSD1306_WHITE);
    }

  // --- LÓGICA DE SALA VAZIA (MODO ECONOMIA) ---
  } else {
    digitalWrite(pinoLed, LOW);  // Desliga o LED indicador
    
    // Imprime status principal
    display.setCursor(14, 18);
    display.setTextSize(2);
    display.println(F("LIVRE"));

    // Exibe telemetria de economia de energia
    display.setCursor(8, 40);
    display.setTextSize(1);
    display.println(F("Modo Economia: ON"));
    
    display.setCursor(8, 52);
    display.println(F("Poupanca: 100% (0W)"));

    // Desenha um ponto estático no canto indicando estado de repouso
    display.fillCircle(112, 28, 2, SSD1306_WHITE);
  }

  // Envia as instruções de desenho registradas no buffer para os pixels físicos da tela
  display.display();
  
  // Pausa de 250ms entre os quadros (garante 4 atualizações por segundo)
  delay(250); 
}
