# Sistema Unificado de Relatórios Daycoval

Sistema completo para geração automatizada de relatórios da API Daycoval, com suporte a múltiplos endpoints e processamento em lote.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Instalação e Configuração](#instalação-e-configuração)
- [Relatórios Disponíveis](#relatórios-disponíveis)
- [Guia de Uso](#guia-de-uso)
- [Parâmetros Avançados](#parâmetros-avançados)
- [Exemplos Práticos](#exemplos-práticos)
- [Solução de Problemas](#solução-de-problemas)

## 🎯 Visão Geral

Este sistema permite gerar cinco tipos principais de relatórios da API Daycoval:

| Endpoint | Tipo de Relatório | Descrição |
|----------|-------------------|-----------|
| **32** | **Carteira Diária** | Relatórios de posição da carteira em uma data específica |
| **45** | **Posição de Cotistas** | Relatórios detalhados dos cotistas por fundo |
| **1048** | **Rentabilidade Sintética** | Relatórios de rentabilidade sintética com base diária opcional |
| **1799** | **Relatório de Rentabilidade** | Relatórios de rentabilidade com índice CDI configurável |
| **1988** | **Extrato Conta Corrente** | Extratos de conta corrente por período e agência/conta |

### ✨ Principais Funcionalidades

- ✅ **Processamento Individual ou em Lote** (1 fundo ou todos os 104 fundos)
- ✅ **Rate Limiting Automático** (evita sobrecarga na API)
- ✅ **Retry Inteligente Aprimorado** (sistema avançado de recuperação de falhas)
- ✅ **Persistência de Falhas** (checkpoint system para reprocessamento)
- ✅ **Taxa de Sucesso 90%+** (sistema enhanced batch com circuit breaker)
- ✅ **Múltiplos Formatos** (PDF, CSV, TXT, JSON)
- ✅ **Configuração Flexível** (defaults inteligentes + customização)
- ✅ **Logs Detalhados** (rastreamento completo do processo)

## 🚀 Instalação e Configuração

### 1. Configuração Inicial

```bash
# Execute o script de configuração
python setup.py

# Isso irá:
# - Verificar dependências
# - Criar diretórios necessários
# - Validar arquivo de configuração
# - Testar conectividade com API
```

### 2. Estrutura de Arquivos

```
daycoval/
├── api.py                    # Módulo principal da API
├── batch_processor.py        # Processamento em lote
├── quoteholder_reports.py    # Módulo para relatórios de cotistas
├── cli.py                   # Interface de linha de comando
├── portfolios.json          # Configuração dos fundos
├── utils/
│   └── logging_utils.py     # Sistema de logs
└── reports/                 # Diretório de saída (criado automaticamente)
```

### 3. Arquivo de Configuração

O arquivo `portfolios.json` contém:
- **95 fundos mapeados** (ID → Nome)
- **Configurações padrão** para relatórios de cotistas
- **Configurações de rate limiting**

## 📊 Relatórios Disponíveis

### 🏦 Relatório de Carteira Diária (Endpoint 32)

**O que contém:**
- Posições dos ativos na carteira
- Valores de mercado
- Rentabilidade
- Composição da carteira

**Quando usar:**
- Relatórios diários de posição
- Acompanhamento de performance
- Análise de composição de portfólio

### 👥 Relatório de Posição de Cotistas (Endpoint 45)

**O que contém:**
- Lista detalhada de cotistas
- Quantidade de cotas por investidor
- Informações de assessores
- Classificação por tipo de investidor

**Quando usar:**
- Controle de base de cotistas
- Relatórios regulamentares
- Análise de distribuição

### 📈 Relatório de Rentabilidade Sintética (Endpoint 1048) ⭐ NOVO

**O que contém:**
- Análise de rentabilidade sintética com base diária opcional
- Comparação com índices de referência configuráveis
- Métricas de performance ajustadas por período
- Dados históricos personalizáveis por data

**Características avançadas:**
- ✅ **Portfolio Opcional**: Pode processar TODAS as carteiras quando omitido
- ✅ **Base Diária**: Análise por período específico (dataInicial → dataFinal)
- ✅ **Múltiplos Tipos**: Cadastro (0), Início a Início (1), Fim a Fim (2)
- ✅ **Saída Dupla**: Individual por fundo + Consolidado (CSV)

**Quando usar:**
- Análise de performance de fundos específicos ou portfolio completo
- Comparação de rentabilidade em períodos históricos
- Relatórios executivos de gestão
- Monitoramento de indicadores customizáveis

### 💰 Relatório de Rentabilidade (Endpoint 1799) ⭐ NOVO

**O que contém:**
- Análise de rentabilidade com índice CDI configurável
- Indicadores de performance personalizáveis
- Tratamento de movimento de ajuste compartilhado
- Flexibilidade na configuração de títulos e logotipos

**Características avançadas:**
- ✅ **Índice CDI Configurável**: Permite definir diferentes índices de referência
- ✅ **Formatação Personalizável**: Nome longo/curto no título, posição do nome do relatório
- ✅ **Tratamento de Ajustes**: Opção para tratar movimentos de ajuste compartilhado
- ✅ **Data Opcional**: Usa data atual se não especificada

**Quando usar:**
- Relatórios de rentabilidade com referência CDI específica
- Análise personalizada de performance
- Comparações com índices de mercado customizados

### 🏦 Extrato Conta Corrente (Endpoint 1988) ⭐ NOVO

**O que contém:**
- Extratos bancários detalhados por período
- Movimentações de conta corrente específica
- Filtros por agência e conta
- Controle de período com dias configuráveis

**Características avançadas:**
- ✅ **Filtro por Agência/Conta**: Busca específica por dados bancários
- ✅ **Período Flexível**: Data inicial obrigatória, final opcional
- ✅ **Controle de Dias**: Parâmetro adicional para controle temporal
- ✅ **Múltiplos Formatos**: PDF, CSV, TXT com formatação BR/US

**Quando usar:**
- Conciliação bancária detalhada
- Auditoria de movimentações por conta
- Relatórios de compliance bancário
- Análise de fluxo de caixa por agência

## 📖 Guia de Uso

### Sintaxe Básica

```bash
python cli.py [opções_globais] [tipo_relatório] [modo] [parâmetros]
```

**Componentes:**
- **Opções globais**: `--format`, `--output-dir`, `--verbose`
- **Tipo de relatório**: `daily`, `quoteholder` ou `profitability`
- **Modo**: `single` (1 fundo) ou `batch` (múltiplos fundos)
- **Parâmetros**: Específicos de cada tipo de relatório

### 🏦 Relatórios de Carteira Diária

#### Um Fundo Específico
```bash
# Formato PDF (padrão)
python cli.py daily single --portfolio 4471709 --date 2025-07-31

# Formato CSV Brasileiro
python cli.py --format CSVBR daily single --portfolio 4471709 --date 2025-07-31

# Com preview das primeiras linhas (apenas texto)
python cli.py daily single --portfolio 4471709 --date 2025-07-31 --preview
```

#### Todos os Fundos (Lote)
```bash
# Todos os 95 fundos em PDF
python cli.py daily batch --all-portfolios --date 2025-07-31

# Fundos específicos
python cli.py daily batch --portfolio-list "4471709,8205906,8310432" --date 2025-07-31

# Com diretório personalizado
python cli.py --output-dir ./relatorios_diarios daily batch --all-portfolios --date 2025-07-31
```

### 👥 Relatórios de Posição de Cotistas

#### Um Fundo Específico
```bash
# Configuração básica (usa defaults)
python cli.py quoteholder single --portfolio 4471709 --date 2025-07-31

# Com range específico de clientes
python cli.py quoteholder single --portfolio 4471709 --date 2025-07-31 --client-range "1000:5000"

# Para classe específica de investidor (0 = Pessoa Jurídica)
python cli.py quoteholder single --portfolio 4471709 --date 2025-07-31 --investor-class 0

# Com headers Excel habilitados
python cli.py quoteholder single --portfolio 4471709 --date 2025-07-31 --excel-headers true
```

#### Todos os Fundos (Lote)
```bash
# Todos os fundos com configuração padrão
python cli.py quoteholder batch --all-portfolios --date 2025-07-31

# Todos os fundos, apenas Pessoa Física (classe 2)
python cli.py quoteholder batch --all-portfolios --date 2025-07-31 --investor-class 2

# Fundos específicos com parâmetros customizados
python cli.py quoteholder batch --portfolio-list "4471709,8205906" --date 2025-07-31 \
    --client-range "1:999999" \
    --investor-class -1 \
    --excel-headers true
```

### 📈 Relatórios de Rentabilidade Sintética (CORRIGIDO v2.1)

**🔧 CORREÇÕES IMPLEMENTADAS:**
- ✅ Correção do parser CLI: `--daily-base` não é mais interpretado como portfolio ID
- ✅ Implementação de relatórios individuais + consolidado para `--all-portfolios`
- ✅ Parâmetros de data agora funcionam corretamente com `--daily-base`

#### Comando Synthetic Otimizado (RECOMENDADO)
```bash
# Portfolio específico com base diária (COMANDO CORRIGIDO)
daycoval profitability synthetic \
    --portfolio-id 1001 \
    --daily-base \
    --start-date 2025-08-01 \
    --end-date 2025-08-29 \
    --format PDF \
    --profitability-type 0

# TODOS os portfolios - gera 104 arquivos individuais + 1 consolidado
daycoval profitability synthetic \
    --all-portfolios \
    --format CSVBR \
    --daily-base \
    --start-date 2025-08-01 \
    --end-date 2025-08-29 \
    --output-dir ./reports

# 🚀 PROCESSAMENTO APRIMORADO com retry inteligente (RECOMENDADO)
daycoval batch-enhanced synthetic-enhanced \
    --all-portfolios \
    --format CSVBR \
    --rate-limit-delay 2.0 \
    --output-dir ./reports

# Portfolio específico sem base diária
daycoval profitability synthetic \
    --portfolio-id 2050 \
    --format PDF \
    --profitability-type 1
```

#### Comando Direto (Endpoint 1048)
```bash
# Relatório para carteira específica em PDF
daycoval profitability relatorio-rentabilidade-sintetica --carteiraId 111376 --format PDF

# Relatório para TODAS as carteiras (carteiraId omitido) em CSV
daycoval profitability relatorio-rentabilidade-sintetica --format CSVBR

# Com base diária e período específico
daycoval profitability relatorio-rentabilidade-sintetica \
    --carteiraId 111376 \
    --format PDF \
    --baseDiaria \
    --dataInicial 2022-10-03 \
    --dataFinal 2022-10-07 \
    --tipoRentabilidadeIndice 0
```

#### Comando Simplificado
```bash
# Usando comando 'synthetic' (mais amigável)
daycoval profitability synthetic 111376 --format PDF --daily-base \
    --start-date 2022-10-03 --end-date 2022-10-07

# Todas as carteiras
daycoval profitability synthetic --all-portfolios --format CSVBR
```

### 💰 Relatórios de Rentabilidade (Endpoint 1799) ⭐ NOVO

#### Comando Direto
```bash
# Relatório de rentabilidade básico em PDF
daycoval profitability relatorio-rentabilidade \
    --carteira 111376 \
    --format PDF \
    --indiceCDI CDI

# Relatório com data específica e configurações personalizadas
daycoval profitability relatorio-rentabilidade \
    --carteira 111376 \
    --format CSVBR \
    --data 2022-10-07 \
    --indiceCDI CDI \
    --usaNomeLongoTitulo \
    --trataMovimentoAjusteComp
```

#### Parâmetros Disponíveis (Endpoint 1799)

| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `--carteira` | Integer | ✅ | Código da carteira | `111376` |
| `--format` | String | ✅ | Formato do relatório | PDF, CSVBR, CSVUS, TXTBR, TXTUS |
| `--data` | String | ❌ | Data de referência | 2022-10-07 |
| `--indiceCDI` | String | ❌ | Índice CDI | CDI (default) |
| `--nomeRelatorioEsquerda` | Boolean | ❌ | Nome relatório à esquerda | Default: true |
| `--omiteLogotipo` | Boolean | ❌ | Omitir logotipo | Default: false |
| `--usaNomeCurtoCarteira` | Boolean | ❌ | Nome curto da carteira | Default: false |
| `--usaNomeLongoTitulo` | Boolean | ❌ | Nome longo no título | Default: false |
| `--trataMovimentoAjusteComp` | Boolean | ❌ | Tratar movimento ajuste | Default: true |

### 🏦 Extratos Conta Corrente (Endpoint 1988) ⭐ NOVO

#### Comando Direto
```bash
# Extrato conta corrente básico
daycoval profitability extrato-conta-corrente \
    --carteira 17485 \
    --format PDF \
    --dataInicial 2024-05-01 \
    --agencia 00019 \
    --conta 0000000123

# Extrato com período definido e formatação CSV
daycoval profitability extrato-conta-corrente \
    --carteira 17485 \
    --format CSVBR \
    --dataInicial 2024-05-01 \
    --dataFinal 2024-05-31 \
    --agencia 00019 \
    --conta 0000000123 \
    --dias 30
```

#### Parâmetros Disponíveis (Endpoint 1988)

| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `--carteira` | Integer | ✅ | Código da carteira | `17485` |
| `--format` | String | ✅ | Formato do relatório | PDF, CSVBR, CSVUS, TXTBR, TXTUS |
| `--dataInicial` | String | ✅ | Data inicial | 2024-05-01 |
| `--dataFinal` | String | ❌ | Data final | 2024-05-31 |
| `--agencia` | String | ✅ | Código da agência | 00019 |
| `--conta` | String | ✅ | Número da conta | 0000000123 |
| `--dias` | Integer | ❌ | Número de dias | Default: 0 |
| `--nomeRelatorioEsquerda` | Boolean | ❌ | Nome relatório à esquerda | Default: true |
| `--omiteLogotipo` | Boolean | ❌ | Omitir logotipo | Default: false |
| `--usaNomeCurtoCarteira` | Boolean | ❌ | Nome curto da carteira | Default: false |

#### Parâmetros Disponíveis (Endpoint 1048)

| Parâmetro | Tipo | Obrigatório | Descrição | Valores |
|-----------|------|-------------|-----------|---------|
| `--carteiraId` | Integer | ❌ | Código da carteira | Se omitido: todas as carteiras |
| `--format` | String | ✅ | Formato do relatório | PDF, CSVBR, CSVUS, TXTBR, TXTUS |
| `--baseDiaria` | Boolean | ❌ | Base diária | Default: false |
| `--dataInicial` | String | Condicional* | Data inicial | YYYY-MM-DD |
| `--dataFinal` | String | Condicional* | Data final | YYYY-MM-DD |
| `--nomeRelatorioEsquerda` | Boolean | ❌ | Nome relatório à esquerda | Default: true |
| `--omiteLogotipo` | Boolean | ❌ | Omitir logotipo | Default: false |
| `--usaNomeCurtoCarteira` | Boolean | ❌ | Nome curto da carteira | Default: false |
| `--tipoRentabilidadeIndice` | Integer | ❌ | Tipo de rentabilidade | 0, 1 ou 2 (default: 0) |
| `--emitirPosicaoDeD0Abertura` | Boolean | ❌ | Emitir posição D0 | Default: false |

*\*Obrigatório se `--baseDiaria` for true*

## 🚀 Sistema Enhanced - Processamento Aprimorado (NOVO!)

**Taxa de Sucesso: 90%+ (vs 57% do sistema padrão)**

O sistema Enhanced é uma versão aprimorada com retry inteligente e persistência de falhas, ideal para processamento em lote de grande escala.

### Principais Melhorias

- ✅ **Retry Inteligente**: Sistema avançado com backoff exponencial
- ✅ **Persistência de Falhas**: Checkpoints automáticos para reprocessamento  
- ✅ **Circuit Breaker**: Isolamento de portfolios problemáticos
- ✅ **Rate Limiting Adaptativo**: Otimização automática de performance
- ✅ **Monitoramento Detalhado**: Estatísticas em tempo real
- ✅ **Recuperação Automática**: Reprocessamento de falhas sem intervenção manual

### Comandos Enhanced

#### 1. Processamento Aprimorado
```bash
# Processar TODOS os portfolios com retry inteligente
daycoval batch-enhanced synthetic-enhanced \
    --all-portfolios \
    --format CSVBR \
    --rate-limit-delay 2.0 \
    --output-dir ./reports

# Resultado esperado: 90%+ de taxa de sucesso
# 📊 Processamento APRIMORADO de TODOS os 104 portfolios
# ✅ Sucessos: 94
# ❌ Falhas: 8  
# 🔴 Circuit Breaker: 2
# 📈 Taxa de Sucesso: 90.4%
# 🎉 META ATINGIDA: Taxa de sucesso 90.4% >= 90.0%
```

#### 2. Reprocessamento de Falhas
```bash
# Reprocessar apenas portfolios que falharam anteriormente
daycoval batch-enhanced retry-failures \
    --format CSVBR \
    --max-portfolios 10

# Resultado:
# 🔄 REPROCESSAMENTO DE FALHAS:
# ✅ Recuperados: 6
# 🎉 Sucesso! 6 portfolios foram recuperados
```

#### 3. Monitoramento e Estatísticas
```bash
# Ver estatísticas detalhadas das falhas
daycoval batch-enhanced failure-stats

# Exportar relatório de falhas para análise
daycoval batch-enhanced failure-stats \
    --export-csv ./reports/failure_analysis.csv

# Limpar falhas antigas (>24h)
daycoval batch-enhanced failure-stats --clear-old 24
```

### Parâmetros do Sistema Enhanced

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `--rate-limit-delay` | `1.0` | Delay entre requests (segundos) |
| `--max-parallel` | `3` | Máximo de requests paralelos |
| `--max-portfolios` | Ilimitado | Limitar número de portfolios (retry) |

### Sistema de Falhas e Retry

O sistema Enhanced classifica falhas automaticamente e aplica estratégias específicas:

| Tipo de Falha | Tentativas | Delay Base | Descrição |
|----------------|------------|------------|-----------|
| **API Error (500)** | 5x | 60s | Erros de servidor - aguarda mais |
| **Timeout** | 3x | 30s | Problemas de rede - retry rápido |
| **Empty Report** | 2x | 120s | Relatório vazio - aguarda processamento |
| **Rate Limit (429)** | 10x | 300s | Limite da API - aguarda bastante |
| **Authentication** | 1x | 600s | Erro crítico - aguarda muito |

### Arquivos de Checkpoint

```bash
# Estrutura automática criada:
./checkpoints/
├── failed_portfolios.json      # Falhas ativas para reprocessamento
├── failed_portfolios.json.bak  # Backup automático
└── failure_reports/            # Relatórios detalhados
    └── detailed_report_YYYYMMDD.csv
```

### Quando Usar Enhanced vs Padrão

**Use Enhanced quando:**
- 🎯 Processamento de todos os 104 portfolios
- 🎯 Precisa de alta taxa de sucesso (>90%)
- 🎯 Ambiente de produção crítico
- 🎯 Processamento automático/agendado

**Use Padrão quando:**
- 📋 Poucos portfolios (<10)  
- 📋 Testes e desenvolvimento
- 📋 Processamento interativo manual

### 🔧 Comandos Utilitários

```bash
# Listar todos os fundos disponíveis
python cli.py list portfolios

# Listar classes de investidor disponíveis
python cli.py list investor-classes

# Ver ajuda completa
python cli.py --help

# Ver ajuda de um comando específico
python cli.py quoteholder single --help
```

## ⚙️ Parâmetros Avançados

### Opções Globais (Aplicam-se a Todos os Comandos)

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `--format` | `PDF` | Formato: `PDF`, `CSVBR`, `CSVUS`, `TXTBR`, `TXTUS`, `JSON` |
| `--output-dir` | `./reports` | Diretório onde salvar os arquivos |
| `--config` | `portfolios.json` | Arquivo de configuração |
| `--verbose` | Desabilitado | Logs detalhados |

### Parâmetros Específicos - Relatórios de Cotistas

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `--client-range` | String | Range de clientes | `"1000:5000"` |
| `--advisor-range` | String | Range de assessores | `"1:999"` |
| `--advisor2-range` | String | Range de assessores 2 | `"0:0"` |
| `--investor-class` | Integer | Classe de investidor (-1 a 21) | `-1` (Todos) |
| `--show-if-code` | Boolean | Mostrar código IF | `true`/`false` |
| `--excel-headers` | Boolean | Headers formato Excel | `true`/`false` |
| `--message` | String | Mensagem personalizada | `"Relatório mensal"` |

### Classes de Investidor

| Código | Descrição |
|--------|-----------|
| `-1` | **Todos** (recomendado para uso geral) |
| `0` | PJU - Pessoa Jurídica |
| `1` | PRI - Private |
| `2` | VAR - Varejo |
| `3` | FAC - Fundos em Cotas |
| `4` | PCO - Por Conta e Ordem |
| `5` | INS - Institucional |
| ... | (21 classes no total - use `python cli.py list investor-classes`) |

## 💡 Exemplos Práticos

### Cenário 1: Relatório Diário de Todos os Fundos
```bash
# Gerar PDFs de carteira diária para todos os 95 fundos
python cli.py daily batch --all-portfolios --date 2025-07-31

# Resultado: 95 arquivos PDF em ./reports/
# Formato: CATALISE_FIC_FIDC_RL_20250731.pdf
```

### Cenário 2: Relatório de Cotistas com Filtros
```bash
# Apenas investidores pessoa física (classe 2) em formato CSV
python cli.py --format CSVBR quoteholder batch --all-portfolios --date 2025-07-31 --investor-class 2

# Resultado: 95 arquivos CSV com apenas cotistas pessoa física
# Formato: POSICAO_COTISTAS_CATALISE_FIC_FIDC_RL_20250731.csv
```

### Cenário 3: Análise de Fundo Específico
```bash
# Relatório completo de um fundo (carteira + cotistas)
python cli.py daily single --portfolio 4471709 --date 2025-07-31
python cli.py quoteholder single --portfolio 4471709 --date 2025-07-31

# Resultado: 2 arquivos PDF com visão completa do fundo
```

### Cenário 4: Relatório Regulatório
```bash
# Cotistas institucionais (classe 5) com headers Excel
python cli.py quoteholder batch --all-portfolios --date 2025-07-31 \
    --investor-class 5 \
    --excel-headers true \
    --message "Relatório CVM mensal"
```

### Cenário 5: Análise de Rentabilidade Sintética
```bash
# Relatório de performance de todas as carteiras em CSV
daycoval profitability relatorio-rentabilidade-sintetica --format CSVBR

# Resultado: 1 arquivo CSV consolidado com dados de todas as carteiras
# Formato: RENTABILIDADE_SINTETICA_TODAS_CARTEIRAS_YYYYMMDD.csv
```

### Cenário 6: Acompanhamento Periódico de Performance
```bash
# Rentabilidade sintética com base diária para período específico
daycoval profitability relatorio-rentabilidade-sintetica \
    --carteiraId 111376 \
    --format PDF \
    --baseDiaria \
    --dataInicial 2025-07-01 \
    --dataFinal 2025-07-31 \
    --tipoRentabilidadeIndice 1

# Resultado: PDF com análise detalhada de performance no período
```

## 🚀 Processamento em Lote (Batch)

O sistema suporta processamento em lote para todos os endpoints, com retry inteligente e recuperação de falhas.

### ✨ Características do Processamento Batch

- **Retry Inteligente**: Até 5 tentativas com backoff exponencial e jitter
- **Circuit Breaker**: Proteção contra falhas em cascata da API
- **Rate Limiting**: Controle automático de taxa para evitar sobrecarga
- **Relatórios de Progresso**: Acompanhe o processamento em tempo real
- **Persistência de Falhas**: Sistema inteligente de checkpoint para reprocessamento
- **Recuperação Automática**: Comando para reprocessar apenas os que falharam

### 📊 Batch - Relatório de Rentabilidade (Endpoint 1799)

```bash
# Processamento em lote com lista de carteiras inline
daycoval profitability batch-rentabilidade \
    --portfolios "17485,17486,17487" \
    --format CSVBR \
    --data 2024-01-31 \
    --indiceCDI CDI \
    --output-dir ./reports

# Processamento em lote com arquivo de carteiras
daycoval profitability batch-rentabilidade \
    --portfolios-file examples/portfolios_exemplo.txt \
    --format PDF \
    --trataMovimentoAjusteComp \
    --usaNomeLongoTitulo \
    --output-dir ./reports
```

### 🏦 Batch - Extrato Conta Corrente (Endpoint 1988)

```bash
# Processamento em lote para extratos
daycoval profitability batch-extrato-conta-corrente \
    --portfolios "17485,17486,17487" \
    --format CSVBR \
    --dataInicial 2024-01-01 \
    --dataFinal 2024-01-31 \
    --agencia "00019" \
    --conta "0000000123" \
    --output-dir ./reports

# Com arquivo de portfolios e configurações avançadas
daycoval profitability batch-extrato-conta-corrente \
    --portfolios-file examples/portfolios_exemplo.txt \
    --format PDF \
    --dataInicial 2024-01-01 \
    --agencia "00019" \
    --conta "0000000123" \
    --dias 30 \
    --nomeRelatorioEsquerda \
    --output-dir ./reports
```

### 📝 Formato do Arquivo de Portfolios

Crie um arquivo de texto simples com um ID de portfolio por linha:

```text
# examples/portfolios_exemplo.txt
17485
17486
17487
17488
17489
```

### 📈 Monitoramento do Processamento

Durante a execução, você verá:

```bash
🚀 Processamento em lote - Relatório de Rentabilidade (1799)
   Portfolios: 5
   Formato: CSVBR

🔄 Processando 1/5: 17485 (FUNDO_EXEMPLO_01)
      ✅ Processado: 2.45 MB
      📁 Salvo: RENTABILIDADE_FUNDO_EXEMPLO_01_2024-01-31.csv

🔄 Processando 2/5: 17486 (FUNDO_EXEMPLO_02)
      ❌ Falha final após retries: API timeout

📊 RESUMO DO PROCESSAMENTO:
   ✅ Sucessos: 4
   ❌ Falhas: 1
   📈 Taxa de Sucesso: 80.0%

✅ Processamento concluído!
   Sucessos: 4/5
   Taxa de sucesso: 80.0%
```

### 🔄 Reprocessamento de Falhas

O sistema automaticamente salva informações sobre portfolios que falharam. Use o processador enhanced para reprocessar apenas os que tiveram problema:

```python
# Exemplo programático para reprocessar falhas
from daycoval.services.enhanced_batch_processor import create_enhanced_batch_processor

processor = create_enhanced_batch_processor()
# O método process_failed_portfolios_retry() reprocessa automaticamente
# apenas os portfolios que falharam anteriormente
```

## 🛠️ Solução de Problemas

### Erro: "No module named 'utils'"
```bash
# Problema: Caminho do módulo utils
# Solução: Verificar se utils/ está no diretório correto
# Ou executar de: C:\Users\atrindade\catalise\DataAnalytics\
```

### Erro: "Invalid URL 'None/report/reports/32'"
```bash
# Problema: BASE_URL não definida no api.py
# Solução: Verificar se BASE_URL = "https://apigw.daycoval.com.br/custodia"
```

### Erro: "unrecognized arguments: --format"
```bash
# Problema: Ordem incorreta dos argumentos
# ❌ Errado: python cli.py quoteholder --format PDF batch
# ✅ Correto: python cli.py --format PDF quoteholder batch
```

### Rate Limiting (429 Too Many Requests)
```bash
# O sistema tem rate limiting automático
# Se persistir, ajustar em portfolios.json:
# "rate_limit": { "max_calls": 20, "period_seconds": 60 }
```

### Arquivos Não Gerados
```bash
# Verificar permissões do diretório
# Usar --verbose para logs detalhados
python cli.py --verbose daily single --portfolio 4471709 --date 2025-07-31
```

## 📁 Estrutura dos Arquivos Gerados

### Nomenclatura Automática

**Relatórios Diários:**
```
NOME_DO_FUNDO_YYYYMMDD.extensao
Exemplo: CATALISE_FIC_FIDC_RL_20250731.pdf
```

**Relatórios de Cotistas:**
```
POSICAO_COTISTAS_NOME_DO_FUNDO_YYYYMMDD.extensao
Exemplo: POSICAO_COTISTAS_CATALISE_FIC_FIDC_RL_20250731.pdf
```

### Organização Sugerida
```
reports/
├── daily/                   # Relatórios de carteira diária
│   ├── 2025-07-31/
│   └── 2025-08-01/
├── quoteholders/            # Relatórios de cotistas
│   ├── 2025-07-31/
│   └── 2025-08-01/
└── logs/                    # Logs do sistema
```

---

## 🔥 NOVA ESTRUTURA CLI v2.5 - Rentabilidade Sintética (Endpoint 1048)

### ⚡ Comandos Refatorados (IMPLEMENTAÇÃO FINAL)

A estrutura CLI foi **completamente refatorada** baseada na análise do Gemini CLI 2.5 Pro para resolver os problemas de parsing e funcionalidade.

#### 🎯 Comando: `synthetic-profitability single`

**Portfolio específico com base diária:**
```bash
# Comando CORRETO para o caso de uso original reportado
daycoval profitability synthetic-profitability single 12345 \
    --daily-base \
    --start-date 2025-08-01 \
    --end-date 2025-08-29 \
    --format PDF \
    --profitability-type 0

# Portfolio específico sem base diária
daycoval profitability synthetic-profitability single 12345 \
    --format CSVBR \
    --profitability-type 1
```

#### 🎯 Comando: `synthetic-profitability all`

**Todos os portfolios (individual + consolidado):**
```bash
# Todos com base diária - CSV (gera individual + consolidado)
daycoval profitability synthetic-profitability all \
    --daily-base \
    --start-date 2025-08-01 \
    --end-date 2025-08-29 \
    --format CSVBR \
    --profitability-type 0

# Todos em PDF (apenas individuais)
daycoval profitability synthetic-profitability all \
    --format PDF \
    --profitability-type 2
```

### 📊 Funcionalidades Implementadas

| Funcionalidade | Status | Descrição |
|----------------|--------|-----------|
| ✅ **CLI Parsing** | **CORRIGIDO** | `daily-base` não é mais interpretado como portfolio ID |
| ✅ **Saída Dupla** | **IMPLEMENTADO** | CSV: arquivos individuais + consolidado |
| ✅ **Date Range** | **CORRIGIDO** | `--start-date` e `--end-date` funcionam com `--daily-base` |
| ✅ **Logging** | **APRIMORADO** | Rastreamento detalhado dos parâmetros de API |
| ✅ **Defensive Programming** | **APLICADO** | Proteção contra AttributeError em portfolios opcionais |

### 🔍 Exemplo de Output

**Comando:**
```bash
daycoval profitability synthetic-profitability all --format CSVBR --daily-base --start-date 2025-08-01 --end-date 2025-08-29
```

**Resultado esperado:**
```
📊 Processando TODOS os 95 portfolios:
   - Arquivos individuais por fundo
   - Arquivo consolidado final

🔄 Gerando relatórios individuais...
   [1/95] 12345 (FUNDO ALPHA FIDC)
      ✅ Salvo: FUNDO_ALPHA_FIDC_SINTETICA_20250829.csv
   [2/95] 12346 (FUNDO BETA FIDC)
      ✅ Salvo: FUNDO_BETA_FIDC_SINTETICA_20250829.csv
   ...

🔄 Gerando arquivo consolidado...
      ✅ Consolidado: CONSOLIDADO_SINTETICA_TODOS_FUNDOS_20250829.csv

🎯 RESULTADO FINAL:
   Total portfolios: 95
   ✅ Sucessos: 93
   ❌ Falhas: 2
   📈 Taxa de sucesso: 97.9%
   📁 Diretório: ./reports
```

---

## 🚀 Scripts de Automação

### Script Diário (Bash/PowerShell)
```bash
#!/bin/bash
# Gerar relatórios diários automaticamente
DATE=$(date +%Y-%m-%d)

echo "Gerando relatórios para $DATE..."

# Relatórios de carteira
python cli.py daily batch --all-portfolios --date "$DATE" --output-dir "./reports/daily/$DATE"

# Relatórios de cotistas
python cli.py quoteholder batch --all-portfolios --date "$DATE" --output-dir "./reports/quoteholders/$DATE"

echo "Concluído!"
```

### Agendamento (Windows Task Scheduler)
```
Programa: python
Argumentos: cli.py daily batch --all-portfolios --date 2025-07-31
Diretório: C:\caminho\para\daycoval\
Horário: 08:00 (após fechamento do D-1)
```

## 🔧 Changelog v2.1 (02/09/2025)

### Correções Críticas Implementadas

**PROBLEMA RESOLVIDO:** Comando `synthetic` com erro de parsing
- ❌ **ANTES**: `daycoval profitability synthetic daily-base --start-date...` → Erro: "Portfolio daily-base não encontrado"
- ✅ **AGORA**: `daycoval profitability synthetic --daily-base --start-date...` → Funciona corretamente

**PROBLEMA RESOLVIDO:** --all-portfolios gerando apenas consolidado
- ❌ **ANTES**: `--all-portfolios` gerava apenas 1 arquivo consolidado
- ✅ **AGORA**: `--all-portfolios` gera 104 arquivos individuais + 1 consolidado = 105 arquivos total

**PROBLEMA RESOLVIDO:** Parâmetros de data ignorados
- ❌ **ANTES**: `--start-date` e `--end-date` eram ignorados sem `--daily-base`
- ✅ **AGORA**: Parâmetros de data funcionam corretamente com `--daily-base`

### Comandos Corretos v2.1
```bash
# ✅ COMANDO CORRIGIDO (usar este)
daycoval profitability synthetic --portfolio-id 1001 --daily-base --start-date 2025-08-01 --end-date 2025-08-29 --format PDF

# ✅ TODOS OS PORTFOLIOS (105 arquivos gerados)
daycoval profitability synthetic --all-portfolios --format CSVBR --daily-base --start-date 2025-08-01 --end-date 2025-08-29
```

## 📞 Suporte

Para dúvidas ou problemas:

1. **Verificar logs**: Usar `--verbose` para informações detalhadas
2. **Consultar este README**: Exemplos e soluções comuns
3. **Testar conectividade**: `python cli.py list portfolios`
4. **Validar configuração**: `python setup.py`
5. **Testar comando synthetic**: `daycoval profitability synthetic --help`

---

**Versão:** 2.1  
**Última atualização:** 02/09/2025  
**Endpoints suportados:** 32 (Carteira Diária), 45 (Posição de Cotistas), 1048 (Rentabilidade Sintética)  
**Fundos configurados:** 95