**Banco de dados para MySQL Workbench**





É necessário ter instalado o MySQL Workbench



Para criar essas tabelas no MySQL Workbench, você precisa executar o script dentro de um banco de dados (schema).



**1** - Abra o MySQL Workbench e clique na sua conexão local (geralmente chamada de **Local instance 3306**). Digite sua senha, se solicitar.



**2** - Abra uma nova aba de query clicando no ícone de pergaminho com um "+" no canto superior esquerdo (ou pressionando **Ctrl + T**).



**3** - Cole o script completo, incluindo a criação do banco de dados para organizar o projeto:







\-- Cria o banco de dados e define como o banco atual

CREATE DATABASE IF NOT EXISTS sistema\_iot;

USE sistema\_iot;



\-- Cria a tabela de salas

CREATE TABLE salas (

&#x20;   id INT AUTO\_INCREMENT PRIMARY KEY,

&#x20;   nome VARCHAR(100) NOT NULL,

&#x20;   modo\_operacao ENUM('AUTO', 'ON', 'OFF') DEFAULT 'AUTO',

&#x20;   status\_ocupado BOOLEAN DEFAULT FALSE

);



\-- Cria a tabela de avisos

CREATE TABLE avisos\_oled (

&#x20;   id INT AUTO\_INCREMENT PRIMARY KEY,

&#x20;   sala\_id INT NOT NULL,

&#x20;   mensagem VARCHAR(255) NOT NULL,

&#x20;   timestamp TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,

&#x20;   FOREIGN KEY (sala\_id) REFERENCES salas(id) ON DELETE CASCADE

);



\-- Cria a tabela de telemetria

CREATE TABLE telemetrias (

&#x20;   id INT AUTO\_INCREMENT PRIMARY KEY,

&#x20;   sala\_id INT NOT NULL,

&#x20;   ocupado BOOLEAN NOT NULL,

&#x20;   potencia\_w FLOAT NOT NULL,

&#x20;   corrente\_ma INT NOT NULL,

&#x20;   timestamp TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,

&#x20;   FOREIGN KEY (sala\_id) REFERENCES salas(id) ON DELETE CASCADE

);

**4** - Execute o script clicando no ícone de raio amarelo (o primeiro, sem a lupa) na barra de ferramentas da query, ou pressione **Ctrl + Shift + Enter**.



**5** - Verifique as tabelas olhando no painel lateral esquerdo chamado "SCHEMAS". Clique no ícone de atualizar (duas setas em círculo). Expanda o banco **sistema\_iot** e a pasta Tables para ver **salas**, **avisos\_oled** e **telemetrias** criadas.

