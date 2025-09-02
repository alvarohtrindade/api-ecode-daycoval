-- DW_STAGING.ft_carteira_daycoval definição

CREATE TABLE `ft_carteira_daycoval` (
  `id` int NOT NULL AUTO_INCREMENT,
  `linha_id` varchar(50) DEFAULT NULL,
  `tipo_registro` varchar(50) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `codigo_fundo` varchar(50) DEFAULT NULL,
  `nome_fundo` varchar(255) DEFAULT NULL,
  `categoria` varchar(255) DEFAULT NULL,
  `moeda` varchar(50) DEFAULT NULL,
  `banco` varchar(255) DEFAULT NULL,
  `data_referencia` varchar(50) DEFAULT NULL,
  `tipo_conta` varchar(50) DEFAULT NULL,
  `descricao_conta` varchar(255) DEFAULT NULL,
  `observacao` varchar(255) DEFAULT NULL,
  `valor_1` decimal(20,2) DEFAULT NULL,
  `valor_2` decimal(20,2) DEFAULT NULL,
  `valor_3` decimal(20,2) DEFAULT NULL,
  `valor_4` decimal(20,2) DEFAULT NULL,
  `valor_principal` decimal(20,2) DEFAULT NULL,
  `valor_secundario` decimal(20,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `update_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5723 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;