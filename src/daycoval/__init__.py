"""
API Daycoval - Sistema limpo e modular para relatórios automatizados.

Este pacote fornece uma interface limpa e bem estruturada para:
- Relatórios de carteira diária (endpoint 32)
- Relatórios de posição de cotistas (endpoint 45)
- Gestão de portfolios com integração Aurora/CADFUN
- CLI organizado e extensível
"""

__version__ = "2.0.0"
__author__ = "Catalise Analytics"
__email__ = "dev@catalise.com.br"

# Importações principais para facilitar uso
from .config.settings import get_settings, AppSettings
from .config.portfolios import get_portfolio_manager, PortfolioManager
from .core.models import (
    Portfolio, 
    ReportFormat, 
    ReportType,
    ReportRequest,
    ReportResponse,
    DailyReportRequest,
    QuoteholderRequest
)
from .core.exceptions import (
    DaycovalError,
    APIError,
    ConfigurationError,
    ValidationError,
    PortfolioNotFoundError
)
from .services.daily_reports import DailyReportService, create_daily_report_service

# Funcionalidades principais
__all__ = [
    # Versão e metadados
    '__version__',
    '__author__',
    '__email__',
    
    # Configuração
    'get_settings',
    'AppSettings',
    'get_portfolio_manager',
    'PortfolioManager',
    
    # Modelos principais
    'Portfolio',
    'ReportFormat',
    'ReportType',
    'ReportRequest',
    'ReportResponse',
    'DailyReportRequest',
    'QuoteholderRequest',
    
    # Exceções
    'DaycovalError',
    'APIError', 
    'ConfigurationError',
    'ValidationError',
    'PortfolioNotFoundError',
    
    # Serviços
    'DailyReportService',
    'create_daily_report_service',
]


def get_version():
    """Retorna versão do pacote."""
    return __version__


def quick_start():
    """
    Guia rápido de uso do sistema.
    
    Returns:
        str: Texto com instruções básicas
    """
    return """
🚀 DAYCOVAL API - GUIA RÁPIDO

📋 Comandos principais:
   daycoval info                    # Informações do sistema
   daycoval list-portfolios         # Listar portfolios
   daycoval quick-report 2025-08-17 # Relatório de teste
   
📊 Relatórios diários:
   daycoval daily single 4471709 2025-08-17
   daycoval daily batch 2025-08-17 --all-portfolios
   
🔗 Banco de dados:
   daycoval db test                 # Testar conexão
   daycoval db refresh              # Atualizar portfolios
   daycoval db stats                # Estatísticas
   
📚 Documentação completa:
   daycoval --help
   daycoval daily --help
   daycoval db --help
"""


def validate_environment():
    """
    Valida se o ambiente está configurado corretamente.
    
    Returns:
        tuple[bool, list[str]]: (sucesso, lista_de_problemas)
    """
    problems = []
    
    try:
        # Testar configurações
        settings = get_settings()
        
        if not settings.api.api_key:
            problems.append("APIKEY_GESTOR não configurada")
        
        if not settings.api.base_url:
            problems.append("PROD_URL não configurada")
            
    except Exception as e:
        problems.append(f"Erro ao carregar configurações: {e}")
    
    try:
        # Testar portfolios
        portfolio_manager = get_portfolio_manager()
        portfolios = portfolio_manager.get_all_portfolios()
        
        if not portfolios:
            problems.append("Nenhum portfolio encontrado")
            
    except Exception as e:
        problems.append(f"Erro ao carregar portfolios: {e}")
    
    return len(problems) == 0, problems


def health_check():
    """
    Verifica saúde geral do sistema.
    
    Returns:
        dict: Status detalhado dos componentes
    """
    health = {
        'overall': 'unknown',
        'components': {}
    }
    
    # Testar configurações
    try:
        settings = get_settings()
        health['components']['config'] = {
            'status': 'healthy',
            'api_configured': bool(settings.api.api_key and settings.api.base_url),
            'database_configured': bool(settings.database.host and settings.database.username)
        }
    except Exception as e:
        health['components']['config'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Testar banco de dados
    try:
        portfolio_manager = get_portfolio_manager()
        db_success, db_message = portfolio_manager.test_database_connection()
        
        health['components']['database'] = {
            'status': 'healthy' if db_success else 'degraded',
            'message': db_message,
            'connection_ok': db_success
        }
    except Exception as e:
        health['components']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Testar portfolios
    try:
        portfolio_manager = get_portfolio_manager()
        portfolios = portfolio_manager.get_all_portfolios()
        
        health['components']['portfolios'] = {
            'status': 'healthy' if portfolios else 'degraded',
            'count': len(portfolios),
            'loaded': bool(portfolios)
        }
    except Exception as e:
        health['components']['portfolios'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Determinar status geral
    component_statuses = [comp['status'] for comp in health['components'].values()]
    
    if all(status == 'healthy' for status in component_statuses):
        health['overall'] = 'healthy'
    elif any(status == 'unhealthy' for status in component_statuses):
        health['overall'] = 'unhealthy'
    else:
        health['overall'] = 'degraded'
    
    return health