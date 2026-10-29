// Definição dos pinos
const int pinoSensor = 13; // Pino conectado ao OUT do Sensor PIR
int estadoSensor = 0;      // Variável para armazenar a leitura (0 ou 1)

void setup() {
  // Inicia a comunicação serial para vermos os logs na tela 
  // (115200 é o baud rate mais estável para o ESP32)
  Serial.begin(115200); 
  
  // Configura o pino do sensor para receber dados
  pinMode(pinoSensor, INPUT);
  
  Serial.println("Aguardando calibração do sensor PIR...");
  delay(2000); // Pausa para o sensor estabilizar no ambiente
  Serial.println("Sistema CampusSmart Iniciado! Monitorando presença...");
}

void loop() {
  // Lê o valor atual do pino (HIGH = detectou movimento, LOW = vazio)
  estadoSensor = digitalRead(pinoSensor);

  if (estadoSensor == HIGH) {
    Serial.println("Status: MOVIMENTO DETECTADO (Sala Ocupada)");
    // Futuramente: aqui a ventoinha ligará simulando o Ar-Condicionado
  } else {
    Serial.println("Status: VAZIO (Ninguém na sala)");
    // Futuramente: aqui inicia o alerta de desperdício se a ventoinha estiver ligada
  }

  // Pausa de 1 segundo antes da próxima leitura para não inundar o terminal
  delay(1000); 
}
