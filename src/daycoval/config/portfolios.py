"""
Gerenciamento de portfolios e integração com banco CADFUN.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import mysql.connector
from mysql.connector import Error as MySQLError

from ..core.models import Portfolio
from ..core.exceptions import DatabaseError, PortfolioNotFoundError, ConfigurationError
from .settings import DatabaseSettings

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Gerencia portfolios com cache e fallback."""
    
    def __init__(self, db_settings: DatabaseSettings, fallback_file: Optional[Path] = None):
        self.db_settings = db_settings
        self.fallback_file = fallback_file or Path("portfolios.json")
        self._cache: Dict[str, Portfolio] = {}
        self._cache_loaded = False
    
    def _load_from_database(self) -> Dict[str, Portfolio]:
        """Carrega portfolios do banco CADFUN."""
        portfolios = {}
        
        try:
            with mysql.connector.connect(
                host=self.db_settings.host,
                port=self.db_settings.port,
                user=self.db_settings.username,
                password=self.db_settings.password,
                database=self.db_settings.database
            ) as connection:
                
                cursor = connection.cursor()
                
                # Query para buscar fundos ativos
                query = """
                SELECT DISTINCT 
                    ID_FUNDO_CUSTODIANTE, 
                    NOME_FUNDO
                FROM DW_DESENV.CADFUN 
                WHERE CUSTODIANTE LIKE '%DAYCOVAL%'
                	AND STATUS NOT IN ('Encerrado', 'Em estruturação')
                ORDER BY ID_FUNDO_CUSTODIANTE
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                for codigo_carteira, nome_fundo in results:
                    portfolio_id = str(codigo_carteira).strip()
                    fund_name = str(nome_fundo).strip()
                    
                    # Validar dados antes de adicionar
                    if portfolio_id and fund_name and portfolio_id != 'None':
                        portfolios[portfolio_id] = Portfolio(
                            id=portfolio_id,
                            name=fund_name
                        )
                
                logger.info(f"Carregados {len(portfolios)} portfolios do banco CADFUN")
                
        except MySQLError as e:
            logger.error(f"Erro ao conectar com banco CADFUN: {e}")
            raise DatabaseError(f"Erro ao acessar banco CADFUN: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao carregar portfolios: {e}")
            raise DatabaseError(f"Erro inesperado: {e}")
        
        return portfolios
    
    def _load_from_file(self) -> Dict[str, Portfolio]:
        """Carrega portfolios do arquivo de fallback."""
        portfolios = {}
        
        if not self.fallback_file.exists():
            logger.warning(f"Arquivo de fallback {self.fallback_file} não encontrado")
            return portfolios
        
        try:
            with open(self.fallback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            portfolio_data = data.get('portfolios', {})
            
            for portfolio_id, fund_name in portfolio_data.items():
                portfolio_id = str(portfolio_id).strip()
                fund_name = str(fund_name).strip()
                
                if portfolio_id and fund_name:
                    portfolios[portfolio_id] = Portfolio(
                        id=portfolio_id,
                        name=fund_name
                    )
            
            logger.info(f"Carregados {len(portfolios)} portfolios do arquivo {self.fallback_file}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao ler arquivo JSON {self.fallback_file}: {e}")
            raise ConfigurationError(f"Arquivo de portfolios inválido: {e}")
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo {self.fallback_file}: {e}")
            raise ConfigurationError(f"Erro ao carregar portfolios: {e}")
        
        return portfolios
    
    def _save_cache_to_file(self, portfolios: Dict[str, Portfolio]) -> bool:
        """Salva cache de portfolios em arquivo."""
        try:
            cache_data = {
                'portfolios': {p.id: p.name for p in portfolios.values()},
                'metadata': {
                    'source': 'database',
                    'timestamp': json.dumps(None, default=str),  # datetime.now().isoformat()
                    'total_count': len(portfolios)
                }
            }
            
            cache_file = Path("cache/fund_names_cache.json")
            cache_file.parent.mkdir(exist_ok=True)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cache salvo em {cache_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")
            return False
    
    def _load_portfolios(self) -> Dict[str, Portfolio]:
        """Carrega portfolios com fallback automático."""
        # Tentar carregar do banco primeiro
        try:
            portfolios = self._load_from_database()
            if portfolios:
                # Salvar cache se carregou do banco
                self._save_cache_to_file(portfolios)
                return portfolios
        except DatabaseError as e:
            logger.warning(f"Falha ao carregar do banco: {e}")
        
        # Fallback para arquivo
        try:
            portfolios = self._load_from_file()
            if portfolios:
                logger.info("Usando portfolios do arquivo de fallback")
                return portfolios
        except ConfigurationError as e:
            logger.warning(f"Falha ao carregar do arquivo: {e}")
        
        # Se chegou aqui, não conseguiu carregar de lugar nenhum
        raise ConfigurationError("Não foi possível carregar portfolios do banco nem do arquivo")
    
    def get_all_portfolios(self) -> Dict[str, Portfolio]:
        """Retorna todos os portfolios disponíveis."""
        if not self._cache_loaded:
            self._cache = self._load_portfolios()
            self._cache_loaded = True
        
        return self._cache.copy()
    
    def get_portfolio(self, portfolio_id: str) -> Portfolio:
        """Retorna portfolio específico por ID."""
        portfolios = self.get_all_portfolios()
        
        portfolio_id = str(portfolio_id).strip()
        
        if portfolio_id not in portfolios:
            raise PortfolioNotFoundError(portfolio_id)
        
        return portfolios[portfolio_id]
    
    def get_portfolio_name(self, portfolio_id: str) -> str:
        """Retorna nome do portfolio (método de compatibilidade)."""
        try:
            portfolio = self.get_portfolio(portfolio_id)
            return portfolio.name
        except PortfolioNotFoundError:
            return f"PORTFOLIO_{portfolio_id}"
    
    def portfolio_exists(self, portfolio_id: str) -> bool:
        """Verifica se portfolio existe."""
        try:
            self.get_portfolio(portfolio_id)
            return True
        except PortfolioNotFoundError:
            return False
    
    def get_portfolio_ids(self) -> List[str]:
        """Retorna lista de IDs de portfolios."""
        portfolios = self.get_all_portfolios()
        return list(portfolios.keys())
    
    def refresh_cache(self) -> bool:
        """Força recarregamento dos portfolios."""
        try:
            self._cache = self._load_portfolios()
            self._cache_loaded = True
            logger.info("Cache de portfolios atualizado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar cache: {e}")
            return False
    
    def clear_cache(self) -> None:
        """Limpa cache de portfolios."""
        self._cache.clear()
        self._cache_loaded = False
        logger.info("Cache de portfolios limpo")
    
    def test_database_connection(self) -> tuple[bool, str]:
        """Testa conexão com banco CADFUN."""
        try:
            with mysql.connector.connect(
                host=self.db_settings.host,
                port=self.db_settings.port,
                user=self.db_settings.username,
                password=self.db_settings.password,
                database=self.db_settings.database,
                connection_timeout=10
            ) as connection:
                
                cursor = connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM CADFUN WHERE SIT_FUNDO = 'A'")
                count = cursor.fetchone()[0]
                
                return True, f"Conexão OK - {count} fundos ativos encontrados"
                
        except MySQLError as e:
            return False, f"Erro MySQL: {e}"
        except Exception as e:
            return False, f"Erro: {e}"
    
    def get_statistics(self) -> Dict[str, any]:
        """Retorna estatísticas dos portfolios."""
        portfolios = self.get_all_portfolios()
        
        return {
            'total_portfolios': len(portfolios),
            'cache_loaded': self._cache_loaded,
            'fallback_file_exists': self.fallback_file.exists(),
            'sample_portfolios': dict(list(portfolios.items())[:5])
        }


# Instância global para compatibilidade
_portfolio_manager: Optional[PortfolioManager] = None


def get_portfolio_manager() -> PortfolioManager:
    """Obtém instância global do gerenciador de portfolios."""
    global _portfolio_manager
    
    if _portfolio_manager is None:
        from .settings import get_settings
        settings = get_settings()
        _portfolio_manager = PortfolioManager(settings.database)
    
    return _portfolio_manager


def reload_portfolio_manager() -> PortfolioManager:
    """Recarrega instância global do gerenciador."""
    global _portfolio_manager
    _portfolio_manager = None
    return get_portfolio_manager()


# Funções de compatibilidade para manter API similar
def get_fund_name(portfolio_id: str) -> str:
    """Função de compatibilidade - retorna nome do fundo."""
    manager = get_portfolio_manager()
    return manager.get_portfolio_name(portfolio_id)


def get_all_fund_names() -> Dict[str, str]:
    """Função de compatibilidade - retorna mapeamento ID -> nome."""
    manager = get_portfolio_manager()
    portfolios = manager.get_all_portfolios()
    return {p.id: p.name for p in portfolios.values()}


def refresh_fund_names() -> bool:
    """Função de compatibilidade - atualiza cache."""
    manager = get_portfolio_manager()
    return manager.refresh_cache()


def test_aurora_connection() -> tuple[bool, str]:
    """Função de compatibilidade - testa conexão."""
    manager = get_portfolio_manager()
    return manager.test_database_connection()