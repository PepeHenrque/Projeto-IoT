# Banco de Dados — MySQL Workbench

Guia de configuração e execução do banco de dados `sistema_iot` para o CampusSmart.

## Pré-requisitos
- Ter o **MySQL Server** e o **MySQL Workbench** instalados (versão 8.0+ recomendada).

---

## Como executar o script no MySQL Workbench

1. **Abra o MySQL Workbench** e conecte-se à sua instância local (geralmente chamada de **Local instance 3306**).
2. **Abra uma nova aba de consulta (Query Tab)** clicando no ícone com o sinal de `+` no canto superior esquerdo ou pressionando `Ctrl + T`.
3. **Cole o script SQL completo** ou execute o arquivo `BancoProjetoIot.sql`:

```sql
-- Cria o banco de dados e define como o banco atual
CREATE DATABASE IF NOT EXISTS sistema_iot;
USE sistema_iot;

-- Remoção segura para recriação
DROP TABLE IF EXISTS telemetrias;
DROP TABLE IF EXISTS avisos_oled;
DROP TABLE IF EXISTS salas;

-- Cria a tabela de salas
CREATE TABLE salas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    modo_operacao ENUM('AUTO', 'ON', 'OFF') DEFAULT 'AUTO',
    status_ocupado BOOLEAN DEFAULT FALSE
);

-- Cria a tabela de avisos exibidos no display OLED
CREATE TABLE avisos_oled (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sala_id INT NOT NULL,
    mensagem VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE
);

-- Cria a tabela de telemetrias enviadas pelo ESP32
CREATE TABLE telemetrias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sala_id INT NOT NULL,
    ocupado BOOLEAN NOT NULL,
    potencia_w FLOAT NOT NULL,
    corrente_ma INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE
);

-- Carga inicial de salas
INSERT INTO salas (id, nome, modo_operacao, status_ocupado) VALUES
(101, 'Sala 101', 'AUTO', 0)
ON DUPLICATE KEY UPDATE nome = VALUES(nome);
```

4. **Execute o script** clicando no ícone do raio (`Execute`) na barra de ferramentas ou pressionando `Ctrl + Shift + Enter`.
5. **Verifique as tabelas criadas**: No painel lateral esquerdo (**SCHEMAS**), clique no botão de atualizar (duas setas circulares). Expanda o schema `sistema_iot` e a pasta **Tables** para visualizar as tabelas `salas`, `avisos_oled` e `telemetrias`.
