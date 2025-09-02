-- Tabela para armazenar os dados de extrato dos portfólios
CREATE TABLE ft_extrato_daycoval (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Dados do portfólio
    id_carteira INT NOT NULL,
    nmfundo VARCHAR(100) NOT NULL,
    portfolio VARCHAR(255) NOT NULL,
    
    -- Período do extrato
    dt_inicio DATE NOT NULL,
    dt_final DATE NOT NULL,
    
    -- Dados da entrada/movimento
    tp_lancamento VARCHAR(50) NOT NULL,
    dt_lancamento DATE NOT NULL,
    
    -- Campos financeiros (DECIMAL para precisão monetária)
    valor DECIMAL(15,2) NULL,
    entrada DECIMAL(15,2) NULL,
    saida DECIMAL(15,2) NULL,
    saldo DECIMAL(15,2) NULL,
    
    -- Detalhes da transação (campos opcionais)
    security VARCHAR(100) NULL,
    lancamento TEXT NULL,
    security_cp VARCHAR(100) NULL,
    tp_entrada VARCHAR(50) NULL,
    
    -- Campos de controle obrigatórios
    business_key_hash CHAR(32) NOT NULL,
    row_hash CHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices para performance
    INDEX idx_id_carteira (id_carteira),
    INDEX idx_entry_date (entry_date),
    INDEX idx_business_key (business_key_hash),
    UNIQUE INDEX idx_row_hash (row_hash),
    INDEX idx_portfolio_period (id_carteira, begin_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;