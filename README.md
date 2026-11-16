# CampusSmart — Monitoramento Inteligente e Automação IoT

Sistema integrado de monitoramento e eficiência energética de salas universitárias, combinando microcontroladores ESP32, mensageria MQTT, API REST (FastAPI), banco de dados relacional (MySQL) e interface web responsiva.

---

## 📁 Estrutura do Repositório

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

## 👥 Equipe e Divisão de Papéis

| Integrante | Papel no Projeto | Módulo Responsável |
| :--- | :--- | :--- |
| **Pedro Henrique Gomes de Lima** | IoT Engineer & Repositório | Firmware ESP32/Arduino, Hardware e Gestão do GitHub |
| **Gustavo Victor Tavares da Silva** | Front-end Developer | UI Mobile, Layout e Estilização |
| **João Henrique Rodrigues Campos** | Front-end Developer | UI Mobile, Componentes e Consumo da API |
| **Letícia Albuquerque Vila Nova da Silva** | Back-end Developer | API REST, Regras de Negócio e Rotas |
| **Líbia Caniceiro da Silveira** | Back-end Developer | API REST, Ingestão de Dados IoT e Log de Eventos |
| **Miquéias Almeida da Silva** | DBA / Banco de Dados | Modelagem SQL, Tabelas e Scripts de Dados |
