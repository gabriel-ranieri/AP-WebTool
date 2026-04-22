-- 1. Tabela de Usuários
CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(150) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2. Tabela de Categorias de Templates
CREATE TABLE IF NOT EXISTS `categorias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. Tabela de Pessoas (Clientes/Associados)
CREATE TABLE IF NOT EXISTS `pessoas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tipo_pessoa` enum('Associado ACRESP','Cliente') NOT NULL,
  `nome` varchar(255) NOT NULL,
  `natureza` enum('Pessoa Física','Empresa') NOT NULL,
  `cpf_cnpj` varchar(20) NOT NULL,
  `endereco` text,
  `rg` varchar(20) DEFAULT NULL,
  `ocupacao` varchar(100) DEFAULT NULL,
  `genero` varchar(50) DEFAULT NULL,
  `nome_mae` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cpf_cnpj` (`cpf_cnpj`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4. Tabela de Processos
CREATE TABLE IF NOT EXISTS `processos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero` varchar(25) NOT NULL,
  `foro` varchar(100) NOT NULL,
  `vara` varchar(100) NOT NULL,
  `comarca` varchar(100) NOT NULL,
  `pessoa_id` int NOT NULL,
  `status` enum('Acordo Celebrado','Acordo Quitado','Acordo Sendo Pago','Extinto','Arquivado','Em Andamento') NOT NULL DEFAULT 'Em Andamento',
  `categoria_id` int NOT NULL,
  
  PRIMARY KEY (`id`),
  KEY `pessoa_id` (`pessoa_id`),
  KEY `categoria_id` (`categoria_id`),
  CONSTRAINT `processos_ibfk_1` FOREIGN KEY (`pessoa_id`) REFERENCES `pessoas` (`id`),
  CONSTRAINT `processos_ibfk_2` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 5. Tabela de Templates
CREATE TABLE IF NOT EXISTS `templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(255) NOT NULL,
  `conteudo` longtext NOT NULL,
  `tem_endereco` tinyint(1) NOT NULL DEFAULT '0',
  `categoria_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `categoria_id` (`categoria_id`),
  CONSTRAINT `templates_ibfk_1` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 6. Tabela de Tracker de Petições
CREATE TABLE IF NOT EXISTS `peticoes_geradas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `processo_id` int NOT NULL,
  `template_id` int NOT NULL,
  `data_geracao` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `processo_id` (`processo_id`),
  KEY `template_id` (`template_id`),
  CONSTRAINT `peticoes_geradas_ibfk_1` FOREIGN KEY (`processo_id`) REFERENCES `processos` (`id`) ON DELETE CASCADE,
  CONSTRAINT `peticoes_geradas_ibfk_2` FOREIGN KEY (`template_id`) REFERENCES `templates` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 7. Tabela de Tags (Calendário/Tarefas)
CREATE TABLE IF NOT EXISTS `tags` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nome` VARCHAR(50) NOT NULL,
    `cor` VARCHAR(20) DEFAULT '#cccccc',
    UNIQUE KEY `nome` (`nome`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 8. Tabela de Tarefas
CREATE TABLE IF NOT EXISTS `tarefas` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `titulo` VARCHAR(255) NOT NULL,
    `descricao` TEXT,
    `data_vencimento` DATE,
    `hora_vencimento` TIME NULL,
    `status` ENUM('Pendente', 'Em Andamento', 'Concluída') DEFAULT 'Pendente',
    `processo_id` INT NULL,
    FOREIGN KEY (`processo_id`) REFERENCES `processos`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 9. Relacionamento Tarefas <-> Tags
CREATE TABLE IF NOT EXISTS `tarefa_tags` (
    `tarefa_id` INT,
    `tag_id` INT,
    PRIMARY KEY (`tarefa_id`, `tag_id`),
    FOREIGN KEY (`tarefa_id`) REFERENCES `tarefas`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`tag_id`) REFERENCES `tags`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 10. Tabela de Anexos das Tarefas (NOVA)
CREATE TABLE IF NOT EXISTS `tarefa_anexos` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `tarefa_id` INT NOT NULL,
    `nome_original` VARCHAR(255) NOT NULL,
    `caminho_arquivo` VARCHAR(255) NOT NULL,
    `data_upload` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `tarefa_id` (`tarefa_id`),
    CONSTRAINT `tarefa_anexos_ibfk_1` FOREIGN KEY (`tarefa_id`) REFERENCES `tarefas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Inserindo algumas tags padrão (O IGNORE pula se a tag já existir)
INSERT IGNORE INTO `tags` (`nome`, `cor`) VALUES 
('Prazo Fatal', '#ff4d4d'), 
('Audiência', '#4da6ff'), 
('Atendimento', '#ffa64d'), 
('Petição', '#b366ff');