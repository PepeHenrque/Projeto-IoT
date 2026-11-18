# CampusSmart — Monitoramento Inteligente e Automação IoT

Sistema integrado de monitoramento e eficiência energética de salas universitárias, combinando microcontroladores ESP32, mensageria MQTT, API REST (FastAPI), banco de dados relacional (MySQL) e interface web responsiva.

---

## Estrutura do Repositório

```
Projeto-IoT/
├── src/
│   ├── backend/        # API REST em FastAPI, integração MQTT e regras de negócio
│   ├── database/       # Modelagem relacional SQL e scripts do banco (MySQL)
│   ├── frontend/       # Interface web responsiva para monitoramento e controle
│   └── hardware/       # Firmware em C++/Arduino para ESP32, sensor PIR e display OLED
├── .gitignore          # Arquivos e pastas desconsiderados pelo Git
└── README.md           # Visão geral do projeto e equipe
```

---

## Como as partes se conectam

```
ESP32 (PIR + OLED + ventoinha) ⇄ MQTT (broker.hivemq.com) ⇄ Back-end FastAPI ⇄ MySQL
                                                                  ⇅ HTTP
                                                       Front-end (Sala 101) no navegador/celular
```

## Como rodar tudo

1. **Banco de dados:** execute `src/database/BancoProjetoIot.sql` no MySQL (Workbench). Se o MySQL não estiver instalado ou ligado no computador, o back-end cria automaticamente o mesmo banco (mesmas tabelas) em SQLite, no arquivo `src/backend/sistema_iot.db`, e tudo continua funcionando.
2. **Back-end + interface:**
   ```bash
   cd src/backend
   python -m venv .venv
   .venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Abra **http://localhost:8000/** (no celular, na mesma rede: `http://IP-DO-COMPUTADOR:8000/`).
3. **ESP32:** configure o Wi-Fi em `src/hardware/main.ino` e grave a placa (detalhes em `src/hardware/README.md`).
   Sem a placa: `python src/hardware/simulador_esp32.py`.
4. **Conferir:** http://localhost:8000/api/v1/device/status mostra se o ESP32 está online e o MQTT conectado.

## Endereços úteis (com o back-end rodando)

| Endereço | O que mostra |
|---|---|
| http://localhost:8000/ | Aplicativo da Sala 101 |
| http://localhost:8000/celular | QR code para abrir o aplicativo no celular (mesmo Wi-Fi) |
| http://localhost:8000/banco | O que está gravado no banco: tabelas `salas`, `telemetrias` e `avisos_oled` (atualiza a cada 5 s) |
| http://localhost:8000/docs | Documentação interativa da API (Swagger) |
| http://localhost:8000/api/v1/device/status | Diagnóstico: ESP32 online, MQTT conectado e último comando |

## Banco de dados

O banco `sistema_iot` tem três tabelas (script em `src/database/BancoProjetoIot.sql`):

| Tabela | O que guarda | Quem grava |
|---|---|---|
| `salas` | A Sala 101, seu modo de operação (AUTO/ON/OFF) e se está ocupada | Carga inicial e comandos do app |
| `telemetrias` | Leituras do ESP32 a cada 2 s: ocupação, potência (W) e corrente (mA) | Back-end, ao receber a telemetria via MQTT |
| `avisos_oled` | Comandos e mensagens enviados ao display (ex.: "CORTE: Ar-condicionado desligado", "MODO ON") | Back-end, a cada comando do app |

---

## Equipe e Divisão de Papéis

| Integrante | Papel no Projeto | Módulo Responsável |
| :--- | :--- | :--- |
| **Pedro Henrique Gomes de Lima** | IoT Engineer & Repositório | Firmware ESP32/Arduino, Hardware e Gestão do GitHub |
| **Gustavo Victor Tavares da Silva** | Front-end Developer | UI Mobile, Layout e Estilização |
| **João Henrique Rodrigues Campos** | Front-end Developer | UI Mobile, Componentes e Consumo da API |
| **Letícia Albuquerque Vila Nova da Silva** | Back-end Developer | API REST, Regras de Negócio e Rotas |
| **Líbia Caniceiro da Silveira** | Back-end Developer | API REST, Ingestão de Dados IoT e Log de Eventos |
| **Miquéias Almeida da Silva** | DBA / Banco de Dados | Modelagem SQL, Tabelas e Scripts de Dados |
