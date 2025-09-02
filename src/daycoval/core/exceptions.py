"""
Exceções customizadas para a API Daycoval.
"""


class DaycovalError(Exception):
    """Exceção base para erros da API Daycoval."""
    pass


class ConfigurationError(DaycovalError):
    """Erro de configuração."""
    pass


class APIError(DaycovalError):
    """Erro na comunicação com a API."""
    
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(APIError):
    """Erro de rate limiting."""
    pass


class AuthenticationError(APIError):
    """Erro de autenticação."""
    pass


class ValidationError(DaycovalError):
    """Erro de validação de dados."""
    pass


class DatabaseError(DaycovalError):
    """Erro de banco de dados."""
    pass


class FileError(DaycovalError):
    """Erro relacionado a arquivos."""
    pass


class ConsolidationError(DaycovalError):
    """Erro durante consolidação."""
    pass


class PortfolioNotFoundError(DaycovalError):
    """Portfolio não encontrado."""
    
    def __init__(self, portfolio_id: str):
        super().__init__(f"Portfolio {portfolio_id} não encontrado")
        self.portfolio_id = portfolio_id


class ReportProcessingError(DaycovalError):
    """Erro quando relatório ainda está sendo processado."""
    pass


class EmptyReportError(DaycovalError):
    """Erro quando relatório está vazio ou inválido."""
    pass


class TimeoutError(APIError):
    """Erro de timeout específico."""
    pass