# Contexto e Diretrizes para API Ecode Daycoval

## 1. Visão Geral do Projeto

**Nome:** api-ecode-daycoval  
**Versão:** 2.1.0 (Enhanced with --n-days and --consolidar)  
**Repositório:** https://github.com/alvarohtrindade/api-ecode-daycoval.git  
**Descrição:** Sistema modular para geração de relatórios automatizados da API Daycoval com suporte a dias úteis e consolidação de dados.

### 1.1 Principais Funcionalidades

- ✅ **Relatórios automatizados** para endpoints 32, 45, 1048, 1799, 1988
- ✅ **Sistema Enhanced** com retry inteligente e taxa de sucesso >90%
- ✅ **Cálculo de dias úteis** via tabela `DW_CORPORATIVO.Dm_Calendario`
- ✅ **Consolidação de dados** em CSV e PDF
- ✅ **CLI modular** com comandos específicos por funcionalidade
- ✅ **Testes unitários e integração** completos

### 1.2 Novidades da Versão 2.1

🔥 **FEATURE: Suporte a `--n-days`**
- Calcula automaticamente data útil D-n consultando tabela `Dm_Calendario`
- Substitui necessidade de especificar datas manualmente
- Funciona com todos os endpoints

🔥 **FEATURE: Suporte a `--consolidar`** 
- Agrega dados de múltiplos fundos em arquivo único
- Formatos CSV e PDF suportados
- Inclui metadados de origem e timestamps

## 2. Estrutura Arquitetônica

### 2.1 Organização de Módulos

```
src/daycoval/
├── cli/
│   ├── main.py                          # CLI principal
│   └── commands/
│       ├── enhanced_profitability.py   # 🆕 Comandos com --n-days/--consolidar
│       ├── profitability.py            # Comandos originais
│       ├── batch_enhanced.py           # Sistema Enhanced
│       ├── daily.py                    # Relatórios diários
│       └── quoteholder.py              # Relatórios de cotistas
├── services/
│   ├── data_consolidation.py           # 🆕 Serviço de consolidação
│   ├── profitability_reports.py        # Relatórios de rentabilidade
│   ├── daily_reports.py               # Relatórios diários
│   └── enhanced_batch_processor.py     # Processamento aprimorado
├── utils/
│   ├── date_business.py                # 🆕 Cálculo de dias úteis
│   ├── logging_utils.py               # Sistema de logs
│   └── mysql_connector_utils.py        # Conexão MySQL
├── core/
│   ├── models.py                       # Modelos Pydantic
│   ├── exceptions.py                   # Exceções customizadas
│   └── client.py                       # Cliente da API
└── config/
    ├── settings.py                     # Configurações
    └── portfolios.py                   # Gestão de portfolios
```

### 2.2 Endpoints Suportados

| Endpoint | Descrição | Comando CLI | Suporte n-days | Consolidação |
|----------|-----------|-------------|----------------|--------------|
| **32** | Carteira Diária | `daycoval ecode carteira` | ✅ | ✅ |
| **45** | Posição de Cotistas | `daycoval quoteholder` | ❌ | ❌ |
| **1048** | Rentabilidade Sintética | `daycoval ecode rentabilidade-sintetica` | ✅ | ✅ |
| **1799** | Relatório de Rentabilidade | `daycoval profitability relatorio-rentabilidade` | ❌ | ❌ |
| **1988** | Extrato Conta Corrente | `daycoval profitability extrato-conta-corrente` | ❌ | ❌ |

## 3. Novos Comandos CLI Implementados

### 3.1 Comando: `daycoval ecode rentabilidade-sintetica`

**Sintaxe completa:**
```bash
daycoval ecode rentabilidade-sintetica \
  [--carteiraId ID] \
  --format {PDF,CSVBR,CSVUS,TXTBR,TXTUS} \
  [--baseDiaria] \
  [--dataInicial YYYY-MM-DD] \
  [--dataFinal YYYY-MM-DD] \
  [--n-days N] \
  [--consolidar] \
  [--formato-consolidado {csv,pdf}] \
  [--saida PATH] \
  [opções adicionais...]
```

**Exemplos práticos:**
```bash
# 1. Portfolio específico D-1 (ontem útil)
daycoval ecode rentabilidade-sintetica \
  --carteiraId 1001 \
  --format PDF \
  --n-days 1

# 2. Todas as carteiras D-2 com consolidação
daycoval ecode rentabilidade-sintetica \
  --format CSVBR \
  --n-days 2 \
  --consolidar \
  --formato-consolidado csv \
  --saida ./reports

# 3. Base diária com período específico
daycoval ecode rentabilidade-sintetica \
  --carteiraId 1001 \
  --format PDF \
  --baseDiaria \
  --dataInicial 2025-08-01 \
  --dataFinal 2025-08-29
```

### 3.2 Comando: `daycoval ecode carteira`

**Sintaxe completa:**
```bash
daycoval ecode carteira \
  [--portfolio ID] \
  [--data YYYY-MM-DD] \
  [--n-days N] \
  [--consolidar] \
  [--formato {csv,pdf}] \
  [--saida PATH]
```

**Exemplos práticos:**
```bash
# 1. Portfolio específico D-1
daycoval ecode carteira \
  --portfolio 12345 \
  --n-days 1 \
  --formato csv

# 2. Todos os portfolios com consolidação
daycoval ecode carteira \
  --n-days 0 \
  --consolidar \
  --formato csv \
  --saida ./reports

# 3. Data específica
daycoval ecode carteira \
  --portfolio 12345 \
  --data 2025-09-04 \
  --formato pdf
```

### 3.3 Comando de Teste: `daycoval ecode test-n-days`

```bash
# Testar cálculo de dias úteis
daycoval ecode test-n-days --n-days 2
```

## 4. Sistema de Dias Úteis

### 4.1 Implementação (`date_business.py`)

**Classe principal:** `BusinessDateCalculator`

```python
from daycoval.utils.date_business import get_business_date_calculator

calculator = get_business_date_calculator()

# D-n dias úteis atrás
business_date = calculator.get_business_day(n_days=2)

# Data específica para dia útil anterior
business_date = calculator.get_business_day(specific_date='2025-01-01')

# Verificar se é dia útil
is_business = calculator.is_business_day('2025-09-04')
```

**Funcionalidades:**
- ✅ Consulta tabela `DW_CORPORATIVO.Dm_Calendario`
- ✅ Cache automático com TTL de 24h
- ✅ Suporte a múltiplos formatos de data
- ✅ Tratamento robusto de erros
- ✅ Thread safety

### 4.2 Integração com CLI

O sistema `--n-days` resolve automaticamente:

```bash
--n-days 0  # Hoje (ou último dia útil)
--n-days 1  # Ontem útil (D-1)
--n-days 2  # Anteontem útil (D-2)
```

Para `--baseDiaria`:
- `--n-days 1` → `dataInicial=D-2, dataFinal=D-1`
- `--n-days 2` → `dataInicial=D-3, dataFinal=D-2`

## 5. Sistema de Consolidação

### 5.1 Implementação (`data_consolidation.py`)

**Classe principal:** `DataConsolidationService`

```python
from daycoval.services.data_consolidation import create_consolidation_service

service = create_consolidation_service()

# Consolidar CSVs
success = service.consolidate_csv_reports(
    reports, output_path, endpoint_type="1048", include_metadata=True
)

# Consolidar PDFs (implementação básica)
success = service.consolidate_pdf_reports(
    reports, output_path, title="Relatório Consolidado"
)
```

**Funcionalidades:**
- ✅ Consolidação CSV com deduplicação
- ✅ Inclusão automática de metadados (FUNDO_ORIGEM, TIMESTAMP)
- ✅ Padronização de campos (datas, números)
- ✅ Validação de schema por endpoint
- ✅ Relatório de consolidação automático
- 🔄 Consolidação PDF (implementação básica)

### 5.2 Metadados Incluídos

Quando `include_metadata=True`:
```csv
FUNDO_ORIGEM,RELATORIO_INDEX,TIMESTAMP_CONSOLIDACAO,FUNDO,DATA,VALOR
FUNDO_A_FIDC,0,2025-09-04 14:30:25,FUNDO_A_FIDC,2025-09-04,1000.50
FUNDO_B_FIDC,1,2025-09-04 14:30:25,FUNDO_B_FIDC,2025-09-04,2000.75
```

## 6. Testes Implementados

### 6.1 Estrutura de Testes

```
tests/
├── test_date_business.py              # Testes unitários dias úteis
├── test_enhanced_profitability_cli.py # Testes comandos CLI
├── test_integration_e2e.py           # Testes integração E2E
├── conftest.py                       # Configurações pytest
└── fixtures/                         # Dados de teste
```

### 6.2 Executar Testes

```bash
# Todos os testes
pytest tests/ -v

# Testes unitários específicos
pytest tests/test_date_business.py -v
pytest tests/test_enhanced_profitability_cli.py -v

# Testes de integração (requer DB)
pytest tests/test_integration_e2e.py -m integration

# Cobertura
pytest tests/ --cov=src/daycoval --cov-report=html
```

### 6.3 Markers Disponíveis

- `@pytest.mark.integration` - Requer conexão com banco
- `@pytest.mark.slow` - Testes lentos (>5s)
- `@pytest.mark.unit` - Testes unitários rápidos

## 7. Configuração e Deployment

### 7.1 Variáveis de Ambiente

**Obrigatórias:**
```bash
# Banco de dados
DB_HOST=aurora-cluster.cluster-xxx.us-east-1.rds.amazonaws.com
DB_USER=user
DB_PASSWORD=password
DB_NAME=DW_CORPORATIVO

# API Daycoval
APIKEY_GESTOR=your_api_key
PROD_URL=https://apigw.daycoval.com.br/custodia
```

**Opcionais:**
```bash
# Configurações avançadas
API_TIMEOUT=120
LOG_LEVEL=INFO
RATE_LIMIT_CALLS=20
RATE_LIMIT_PERIOD=60
```

### 7.2 Instalação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Instalar em modo desenvolvimento
pip install -e .

# 3. Verificar instalação
daycoval --help
daycoval info
daycoval check-config

# 4. Testar conexões
daycoval db-test
```

### 7.3 Estrutura de Diretórios

```bash
# Criar estrutura padrão
mkdir -p {data/{input,output,mapping,checkpoints},logs,reports}

# Arquivos de configuração
cp .env.template .env  # Editar com credenciais
```

## 8. Troubleshooting

### 8.1 Problemas Comuns

**Erro: "Nenhum dia útil encontrado"**
```bash
# Verificar conexão com banco
daycoval db-test

# Testar calculadora
daycoval ecode test-n-days --n-days 1
```

**Erro: "Portfolio não encontrado"**
```bash
# Listar portfolios disponíveis
daycoval list-portfolios --limit 20

# Atualizar cache
daycoval db-refresh
```

**Erro: "API timeout"**
```bash
# Usar sistema Enhanced com retry
daycoval batch-enhanced synthetic-enhanced --all-portfolios
```

### 8.2 Logs e Debug

**Localização dos logs:**
```bash
# Logs da aplicação
tail -f logs/daycoval.log

# Logs específicos
tail -f logs/date_business_test.log
tail -f logs/consolidation.log
```

**Debug verbose:**
```bash
# Executar com verbose
daycoval --verbose ecode rentabilidade-sintetica --carteiraId 1001 --format PDF
```

### 8.3 Performance

**Sistema Enhanced (recomendado para produção):**
```bash
# Taxa de sucesso >90%
daycoval batch-enhanced synthetic-enhanced \
  --all-portfolios \
  --format CSVBR \
  --rate-limit-delay 2.0
```

**Configurar rate limiting:**
```python
# Em .env
RATE_LIMIT_CALLS=15  # Reduzir para APIs instáveis
RATE_LIMIT_PERIOD=60
```

## 9. Roadmap e Melhorias Futuras

### 9.1 Funcionalidades Planejadas

- 🔄 **Consolidação PDF** completa com PyPDF2/reportlab
- 🔄 **Suporte a `--n-days`** para endpoints 1799 e 1988
- 🔄 **Cache de relatórios** com Redis
- 🔄 **Notificações** via email/Slack
- 🔄 **Dashboard web** para monitoramento
- 🔄 **Agendamento** com cron jobs

### 9.2 Melhorias Técnicas

- 🔄 **Paralelização** de requests com asyncio
- 🔄 **Compressão** de arquivos grandes
- 🔄 **Validação avançada** de dados com Great Expectations
- 🔄 **Métricas** com Prometheus/Grafana
- 🔄 **CI/CD** com GitHub Actions

### 9.3 Compatibilidade

**Versões Python suportadas:** 3.8+  
**Dependências principais:**
- `click>=8.0.0` - CLI framework
- `mysql-connector-python>=8.0.0` - MySQL driver
- `pydantic>=1.8.0` - Validação de dados
- `requests>=2.25.0` - HTTP client
- `python-dotenv>=0.19.0` - Variáveis de ambiente

## 10. Changelog

### Versão 2.1.0 (2025-09-04)

**🆕 Novas funcionalidades:**
- ✅ Argumento `--n-days` para cálculo automático de dias úteis
- ✅ Argumento `--consolidar` para agregação de dados
- ✅ Sistema completo de dias úteis via tabela `Dm_Calendario`
- ✅ Serviço de consolidação CSV/PDF
- ✅ Comandos CLI aprimorados (`daycoval ecode`)
- ✅ Testes unitários e integração completos

**🔧 Melhorias:**
- ✅ Código defensivo com tratamento de erros
- ✅ Logging estruturado e detalhado
- ✅ Validação de parâmetros aprimorada
- ✅ Documentação completa e exemplos

**🐛 Correções:**
- ✅ Parsing CLI mais robusto
- ✅ Tratamento de encoding em CSVs
- ✅ Gestão de memória para arquivos grandes

### Versão 2.0.0 (Base)
- ✅ Estrutura modular completa
- ✅ Suporte a todos os endpoints
- ✅ Sistema Enhanced com retry
- ✅ CLI organizado com subcomandos

## 11. Contatos e Suporte

**Desenvolvedor:** Claude Code  
**Email:** alvaro.htrindade@gmail.com  
**Repositório:** https://github.com/alvarohtrindade/api-ecode-daycoval  

**Para suporte:**
1. Consultar este documento (CLAUDE.md)
2. Executar `daycoval check-config` para diagnóstico
3. Verificar logs em `logs/`
4. Abrir issue no GitHub com logs e contexto