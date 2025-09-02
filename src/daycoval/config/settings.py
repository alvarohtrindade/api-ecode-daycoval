"""
Configuração centralizada para a API Daycoval.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class APISettings:
    """Configurações da API Daycoval."""
    api_key: str
    base_url: str
    timeout: int = 60  # Aumentado de 30 para 60 segundos
    max_retries: int = 3
    backoff_factor: float = 2.0
    rate_limit_calls: int = 30
    rate_limit_period: int = 60

    @classmethod
    def from_env(cls) -> 'APISettings':
        """Cria configuração a partir de variáveis de ambiente."""
        api_key = os.getenv('APIKEY_GESTOR')
        base_url = os.getenv('PROD_URL')
        
        if not api_key:
            raise ValueError("APIKEY_GESTOR não encontrada nas variáveis de ambiente")
        if not base_url:
            raise ValueError("PROD_URL não encontrada nas variáveis de ambiente")
            
        return cls(
            api_key=api_key,
            base_url=base_url,
            timeout=int(os.getenv('API_TIMEOUT', '60')),  # Padrão aumentado
            max_retries=int(os.getenv('API_MAX_RETRIES', '3')),
            backoff_factor=float(os.getenv('API_BACKOFF_FACTOR', '2.0')),
            rate_limit_calls=int(os.getenv('RATE_LIMIT_CALLS', '30')),
            rate_limit_period=int(os.getenv('RATE_LIMIT_PERIOD', '60'))
        )


@dataclass
class DatabaseSettings:
    """Configurações do banco Aurora."""
    host: str
    port: int
    username: str
    password: str
    database: str
    
    @classmethod
    def from_env(cls) -> 'DatabaseSettings':
        """Cria configuração a partir de variáveis de ambiente."""
        host = os.getenv('AURORA_HOST')
        username = os.getenv('AURORA_USER')
        password = os.getenv('AURORA_PASSWORD')
        database = os.getenv('AURORA_DATABASE', 'DW_DESENV')
        
        if not all([host, username, password]):
            raise ValueError("Configurações Aurora incompletas: AURORA_HOST, AURORA_USER, AURORA_PASSWORD são obrigatórias")
            
        return cls(
            host=host,
            port=int(os.getenv('AURORA_PORT', '3306')),
            username=username,
            password=password,
            database=database
        )


@dataclass
class DirectorySettings:
    """Configurações para gerenciamento de diretórios."""
    base_drive: str = "F:"
    endpoint_mappings: Dict[int, str] = field(default_factory=lambda: {
        32: "12. Carteira Diária",
        45: "13. Posição Cotistas"
    })
    month_names: Dict[int, str] = field(default_factory=lambda: {
        1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
        5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
        9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
    })
    
    @classmethod
    def from_env(cls) -> 'DirectorySettings':
        """Cria configuração a partir de variáveis de ambiente."""
        return cls(
            base_drive=os.getenv('DEFAULT_BASE_DRIVE', 'F:')
        )


@dataclass
class LoggingSettings:
    """Configurações de logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    file_path: Optional[str] = None
    max_size_mb: float = 5.0
    backup_count: int = 5
    use_colors: bool = True
    
    @classmethod
    def from_env(cls) -> 'LoggingSettings':
        """Cria configuração a partir de variáveis de ambiente."""
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            file_path=os.getenv('LOG_FILE_PATH'),
            max_size_mb=float(os.getenv('LOG_MAX_SIZE_MB', '5.0')),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
            use_colors=os.getenv('LOG_USE_COLORS', 'true').lower() == 'true'
        )


@dataclass
class AppSettings:
    """Configurações completas da aplicação."""
    api: APISettings
    database: DatabaseSettings
    directories: DirectorySettings
    logging: LoggingSettings
    
    @classmethod
    def from_env(cls) -> 'AppSettings':
        """Cria todas as configurações a partir de variáveis de ambiente."""
        return cls(
            api=APISettings.from_env(),
            database=DatabaseSettings.from_env(),
            directories=DirectorySettings.from_env(),
            logging=LoggingSettings.from_env()
        )


# Instância global de configuração
def get_settings() -> AppSettings:
    """Obtém configurações da aplicação (singleton)."""
    if not hasattr(get_settings, '_settings'):
        get_settings._settings = AppSettings.from_env()
    return get_settings._settings


def reload_settings() -> AppSettings:
    """Recarrega configurações da aplicação."""
    if hasattr(get_settings, '_settings'):
        delattr(get_settings, '_settings')
    return get_settings()