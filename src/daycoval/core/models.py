"""
Modelos de dados para a API Daycoval.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Union

# Constantes
DEFAULT_ALL_PORTFOLIOS_LABEL = "TODAS_AS_CARTEIRAS"


class ReportFormat(Enum):
    """Formatos de relatório suportados."""
    PDF = "PDF"
    CSV_BR = "CSVBR"
    CSV_US = "CSVUS"
    TXT_BR = "TXTBR" 
    TXT_US = "TXTUS"
    JSON = "JSON"

    @property
    def extension(self) -> str:
        """Retorna a extensão de arquivo para o formato."""
        extensions = {
            self.PDF: ".pdf",
            self.CSV_BR: ".csv",
            self.CSV_US: ".csv", 
            self.TXT_BR: ".txt",
            self.TXT_US: ".txt",
            self.JSON: ".json"
        }
        return extensions[self]

    @property
    def is_csv(self) -> bool:
        """Verifica se o formato é CSV."""
        return self in (self.CSV_BR, self.CSV_US)

    @property
    def is_text(self) -> bool:
        """Verifica se o formato é texto."""
        return self in (self.CSV_BR, self.CSV_US, self.TXT_BR, self.TXT_US, self.JSON)


class ReportType(Enum):
    """Tipos de relatório."""
    DAILY = 32
    QUOTEHOLDER = 45


@dataclass
class Portfolio:
    """Representa um portfolio/fundo."""
    id: str
    name: str
    
    def __post_init__(self):
        """Validação após inicialização."""
        if not self.id or not self.id.strip():
            raise ValueError("Portfolio ID não pode estar vazio")
        if not self.name or not self.name.strip():
            raise ValueError("Portfolio name não pode estar vazio")
            
        self.id = self.id.strip()
        self.name = self.name.strip()


@dataclass
class ReportRequest:
    """Requisição de relatório."""
    portfolio: Optional[Portfolio]
    date: datetime
    format: ReportFormat
    report_type: ReportType
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validação após inicialização."""
        if self.parameters is None:
            self.parameters = {}
            
        # Validar data
        if self.date > datetime.now():
            raise ValueError("Data do relatório não pode ser futura")


@dataclass
class ReportResponse:
    """Resposta de relatório."""
    content: Union[bytes, str]
    content_type: str
    filename: str
    portfolio: Optional[Portfolio]
    date: datetime
    format: ReportFormat
    size_bytes: int
    request_params: Dict[str, Any] = None
    
    def __post_init__(self):
        """Cálculo automático do tamanho se não fornecido."""
        if self.size_bytes == 0:
            if isinstance(self.content, bytes):
                self.size_bytes = len(self.content)
            elif isinstance(self.content, str):
                self.size_bytes = len(self.content.encode('utf-8'))
                
        if self.request_params is None:
            self.request_params = {}

    @property
    def is_binary(self) -> bool:
        """Verifica se o conteúdo é binário."""
        return isinstance(self.content, bytes)

    @property
    def size_mb(self) -> float:
        """Retorna o tamanho em MB."""
        return self.size_bytes / (1024 * 1024)

    def save_to_file(self, file_path: Path) -> bool:
        """Salva o conteúdo em arquivo."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.is_binary:
                with open(file_path, 'wb') as f:
                    f.write(self.content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.content)
                    
            return True
        except Exception:
            return False


@dataclass
class QuoteholderRequest(ReportRequest):
    """Requisição específica para relatórios de cotistas."""
    client_start: int = 1
    client_end: int = 999999999999
    advisor_start: int = 1
    advisor_end: int = 99999
    advisor2_start: int = 0
    advisor2_end: int = 0
    investor_class: int = -1
    show_if_code: bool = True
    excel_headers: bool = False
    message: str = ""
    left_report_name: bool = True
    omit_logo: bool = False
    use_short_portfolio_name: bool = False
    
    def to_api_params(self) -> Dict[str, Any]:
        """Converte para parâmetros da API."""
        return {
            "carteira": self.portfolio.id,
            "format": self.format.value,
            "data": self.date.strftime('%Y-%m-%d'),
            "nomeRelatorioEsquerda": self.left_report_name,
            "omiteLogotipo": self.omit_logo,
            "usaNomeCurtoCarteira": self.use_short_portfolio_name,
            "clienteInicial": self.client_start,
            "clienteFinal": self.client_end,
            "assessorInicial": self.advisor_start,
            "assessorFinal": self.advisor_end,
            "assessor2Inicial": self.advisor2_start,
            "assessor2Final": self.advisor2_end,
            "classeInvestidor": self.investor_class,
            "apresentaCodigoIF": self.show_if_code,
            "geraArquivoFormatoExcelHeaders": self.excel_headers,
            "mensagem": self.message,
            **self.parameters
        }


@dataclass
class DailyReportRequest(ReportRequest):
    """Requisição específica para relatórios diários."""
    break_level: int = 1
    left_report_name: bool = False
    omit_logo: bool = False
    detail_fixed_income: bool = True
    detail_net_worth: bool = False
    show_investor_qty: bool = True
    show_market_zeroed_security: bool = True
    consolidated_rc12: bool = False
    show_until_maturity_mark: bool = False
    considers_compensation: bool = False
    details_compensation: bool = False
    show_two_rentabilities: bool = False
    show_quota_without_amortization: bool = False
    show_quota_before_amortization: bool = False
    show_net_worth_percentual: bool = False
    
    def to_api_params(self) -> Dict[str, Any]:
        """Converte para parâmetros da API."""
        params = {
            "format": self.format.value,
            "date": self.date.strftime('%Y-%m-%d'),
            "breakLevel": self.break_level,
            "leftReportName": self.left_report_name,
            "omitLogotype": self.omit_logo,
            "detailFixedIncome": self.detail_fixed_income,
            "detailNetWorth": self.detail_net_worth,
            "showInvestorQty": self.show_investor_qty,
            "showMarketZeroedSecurity": self.show_market_zeroed_security,
            "consolidatedRC12": self.consolidated_rc12,
            "showUntilMaturityMark": self.show_until_maturity_mark,
            "considersCompensation": self.considers_compensation,
            "detailsCompensation": self.details_compensation,
            "showTwoRentabilities": self.show_two_rentabilities,
            "showQuotaWithoutAmortization": self.show_quota_without_amortization,
            "showQuotaBeforeAmortization": self.show_quota_before_amortization,
            "showNetWorthPercentual": self.show_net_worth_percentual,
            **self.parameters
        }
        
        # Adicionar portfolio apenas se especificado
        if self.portfolio:
            params["portfolio"] = self.portfolio.id
            
        return params


@dataclass
class BatchResult:
    """Resultado de processamento em lote."""
    total: int
    successful: int
    failed: int
    skipped: int
    results: Dict[str, Any]
    execution_time_seconds: float
    
    @property
    def success_rate(self) -> float:
        """Taxa de sucesso em percentual."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100

    @property
    def throughput(self) -> float:
        """Taxa de processamento (items/segundo)."""
        if self.execution_time_seconds == 0:
            return 0.0
        return self.total / self.execution_time_seconds


@dataclass
class ConsolidationResult:
    """Resultado de consolidação."""
    input_files: int
    output_file: Path
    total_rows: int
    size_bytes: int
    execution_time_seconds: float
    
    @property
    def size_mb(self) -> float:
        """Tamanho em MB."""
        return self.size_bytes / (1024 * 1024)
    
@dataclass
class SyntheticProfitabilityRequest(ReportRequest):
    """Requisição para Relatório Rentabilidade Sintética (endpoint 1048)."""
    daily_base: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    profitability_index_type: int = 0
    emit_d0_opening_position: bool = False
    left_report_name: bool = True
    omit_logo: bool = False
    use_short_portfolio_name: bool = False
    
    def __post_init__(self):
        """Validação após inicialização."""
        super().__post_init__()
        
        
        if self.daily_base and (not self.start_date or not self.end_date):
            raise ValueError("Para base diária, dataInicial e dataFinal são obrigatórias")
        
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Data inicial não pode ser posterior à data final")
        
        # Validar tipo de rentabilidade
        if self.profitability_index_type not in [0, 1, 2]:
            raise ValueError("tipoRentabilidadeIndice deve ser 0, 1 ou 2")
    
    def to_api_params(self) -> Dict[str, Any]:
        """Converte para parâmetros da API."""
        import logging
        logger = logging.getLogger(__name__)
        
        params = {
            "format": self.format.value,
            "baseDiaria": self.daily_base,
            "nomeRelatorioEsquerda": self.left_report_name,
            "omiteLogotipo": self.omit_logo,
            "usaNomeCurtoCarteira": self.use_short_portfolio_name,
            "tipoRentabilidadeIndice": self.profitability_index_type,
            "emitirPosicaoDeD0Abertura": self.emit_d0_opening_position
        }
        
        # carteiraId é opcional - se omitido, executa para todas as carteiras
        if self.portfolio:
            params["carteiraId"] = int(self.portfolio.id)
            logger.info(f"✅ Portfolio especificado: {self.portfolio.id}")
        else:
            logger.info(f"✅ Portfolio: {DEFAULT_ALL_PORTFOLIOS_LABEL} (carteiraId omitido)")
        
        
        if self.daily_base and self.start_date and self.end_date:
            params["dataInicial"] = self.start_date.strftime('%Y-%m-%d')
            params["dataFinal"] = self.end_date.strftime('%Y-%m-%d')
            logger.info(f"📅 Base diária ativada - Período: {params['dataInicial']} a {params['dataFinal']}")
        elif self.daily_base:
            logger.warning(f"⚠️ Base diária ativada mas datas não fornecidas: start_date={self.start_date}, end_date={self.end_date}")
        else:
            logger.info(f"📅 Base diária desativada - usando data atual da carteira")
        
        
        if self.parameters:
            params.update(self.parameters)
        
        # Log dos parâmetros finais enviados para API
        logger.info(f"🚀 Parâmetros finais API endpoint 1048: {params}")
        
        return params


@dataclass
class ProfitabilityRequest(ReportRequest):
    """Requisição para Relatório de Rentabilidade (endpoint 1799)."""
    report_date: Optional[datetime] = None
    left_report_name: bool = True
    omit_logo: bool = False
    use_short_portfolio_name: bool = False
    use_long_title_name: bool = False
    handle_shared_adjustment_movement: bool = True
    cdi_index: str = "CDI"
    
    def __post_init__(self):
        """Validação após inicialização."""
        super().__post_init__()
        
        
        if self.report_date and self.report_date > datetime.now():
            raise ValueError("Data do relatório não pode ser futura")
        
        # Validar índice CDI
        if not self.cdi_index or not self.cdi_index.strip():
            raise ValueError("indiceCDI é obrigatório")
    
    def to_api_params(self) -> Dict[str, Any]:
        """Converte para parâmetros da API."""
        params = {
            "carteira": int(self.portfolio.id),  # Seguindo documentação
            "format": self.format.value,
            "nomeRelatorioEsquerda": self.left_report_name,
            "omiteLogotipo": self.omit_logo,
            "usaNomeCurtoCarteira": self.use_short_portfolio_name,
            "usaNomeLongoTitulo": self.use_long_title_name,
            "trataMovimentoAjusteComp": self.handle_shared_adjustment_movement,
            "indiceCDI": self.cdi_index
        }
        
        
        if self.report_date:
            params["data"] = self.report_date.strftime('%Y-%m-%d')
        
       
        if self.parameters:
            params.update(self.parameters)
        
        return params


@dataclass  
class BankStatementRequest(ReportRequest):
    """Requisição para Extrato Conta Corrente (endpoint 1988)."""
    # Todos os campos devem ter valores padrão devido à herança de ReportRequest
    start_date: datetime = field(default_factory=datetime.now)
    agency: str = field(default="")  
    account: str = field(default="")
    end_date: Optional[datetime] = field(default=None)
    days: int = field(default=0)
    left_report_name: bool = field(default=True)
    omit_logo: bool = field(default=False)
    use_short_portfolio_name: bool = field(default=False)
    
    def __post_init__(self):
        """Validação após inicialização."""
        super().__post_init__()
        
        # Validar se campos obrigatórios foram fornecidos (não são valores padrão)
        if not self.agency or self.agency == "":
            raise ValueError("Agência é obrigatória")
            
        if not self.account or self.account == "":
            raise ValueError("Conta é obrigatória")
        
        # Validar datas
        if self.start_date > datetime.now():
            raise ValueError("Data inicial não pode ser futura")
        
        if self.end_date and self.end_date > datetime.now():
            raise ValueError("Data final não pode ser futura")
            
        if self.end_date and self.start_date > self.end_date:
            raise ValueError("Data inicial não pode ser posterior à data final")
            
        # Validar dias
        if self.days < 0:
            raise ValueError("Número de dias não pode ser negativo")
    
    def to_api_params(self) -> Dict[str, Any]:
        """Converte para parâmetros da API."""
        params = {
            "carteira": int(self.portfolio.id),
            "format": self.format.value,
            "dataInicial": self.start_date.strftime('%Y-%m-%d'),
            "agencia": self.agency,
            "conta": self.account,
            "dias": self.days,
            "nomeRelatorioEsquerda": self.left_report_name,
            "omiteLogotipo": self.omit_logo,
            "usaNomeCurtoCarteira": self.use_short_portfolio_name
        }
        
        # dataFinal é opcional
        if self.end_date:
            params["dataFinal"] = self.end_date.strftime('%Y-%m-%d')
        else:
            params["dataFinal"] = ""
        
        # Adicionar parâmetros extras
        if self.parameters:
            params.update(self.parameters)
        
        return params