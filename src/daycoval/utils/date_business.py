"""
Utilitários para cálculo de dias úteis baseado na tabela DW_CORPORATIVO.Dm_Calendario.

Este módulo fornece funcionalidades para:
- Calcular data útil D-n (n dias úteis atrás)
- Validar se uma data é dia útil
- Obter próximo/anterior dia útil

Author: Claude Code
Date: 2025-09-04
Version: 1.0
"""

import os
import sys
import traceback
import threading
from datetime import date, datetime, timedelta
from typing import Optional, List, Union
from pathlib import Path

# Adiciona o diretório raiz do projeto ao sys.path para imports
if __name__ == '__main__' and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from utils.logging_utils import Log, LogLevel
from utils.mysql_connector_utils import MySQLConnector
from utils.date_utils import get_mysql_connector

# Logger específico do módulo
logger = Log.get_logger(__name__)


class BusinessDateError(Exception):
    """Exceção específica para erros de dias úteis."""
    pass


class BusinessDateCalculator:
    """
    Calculadora de dias úteis baseada na tabela DW_CORPORATIVO.Dm_Calendario.
    
    Esta classe consulta a tabela de calendário do data warehouse para determinar
    dias úteis, considerando feriados e fins de semana conforme configurado.
    """
    
    def __init__(self, connector: Optional[MySQLConnector] = None):
        """
        Inicializa o calculador.
        
        Args:
            connector: Conector MySQL opcional. Se não fornecido, usa o padrão.
        """
        self.connector = connector or get_mysql_connector()
        self._cache_business_dates: Optional[List[date]] = None
        self._cache_valid_until: Optional[date] = None
        self._cache_lock = threading.Lock()  # Thread safety para cache
        
    def _get_calendar_query(self) -> str:
        """
        Query para buscar dias úteis na tabela Dm_Calendario.
        
        Returns:
            str: Query SQL para buscar dias úteis
        """
        return """
        SELECT Data, DiaSemana, FlagFeriado, FlagDiaUtil
        FROM DW_CORPORATIVO.Dm_Calendario 
        WHERE Data >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
          AND Data <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
          AND FlagDiaUtil IN (1, 'S', 'Y', TRUE)
        ORDER BY Data ASC
        """
    
    def _load_business_dates(self, force_refresh: bool = False) -> List[date]:
        """
        Carrega dias úteis do banco de dados (thread-safe).
        
        Args:
            force_refresh: Força recarregamento do cache
            
        Returns:
            List[date]: Lista de datas úteis ordenadas
            
        Raises:
            BusinessDateError: Erro ao consultar tabela de calendário
        """
        with self._cache_lock:
            # Verificar cache dentro do lock
            if (not force_refresh and 
                self._cache_business_dates is not None and 
                self._cache_valid_until is not None and
                date.today() <= self._cache_valid_until):
                return self._cache_business_dates
            
            logger.info('Carregando dias úteis da tabela Dm_Calendario (cache miss)')
            
            try:
                query = self._get_calendar_query()
                results = self.connector.query_all(query)
                
                if not results:
                    raise BusinessDateError("Nenhum registro encontrado na tabela Dm_Calendario")
                
                # Processar resultados (query já filtra dias úteis)
                business_dates = []
                for row in results:
                    data = row[0]  # Apenas o primeiro campo (Data)
                    
                    # Converter para date se necessário
                    if isinstance(data, datetime):
                        data = data.date()
                    elif isinstance(data, str):
                        data = datetime.strptime(data, '%Y-%m-%d').date()
                    
                    business_dates.append(data)
                
                if not business_dates:
                    raise BusinessDateError("Nenhum dia útil encontrado na tabela Dm_Calendario")
                
                # Ordenar datas
                business_dates.sort()
                
                # Atualizar cache
                self._cache_business_dates = business_dates
                self._cache_valid_until = date.today() + timedelta(days=1)
                
                logger.info(f'Carregados {len(business_dates)} dias úteis (de {business_dates[0]} até {business_dates[-1]})')
                return business_dates
                
            except Exception as e:
                logger.error(f'Erro ao carregar dias úteis: {str(e)}')
                logger.error(traceback.format_exc())
                raise BusinessDateError(f"Falha ao consultar tabela de calendário: {str(e)}")
    
    def is_business_day(self, target_date: Union[date, datetime, str]) -> bool:
        """
        Verifica se uma data é dia útil.
        
        Args:
            target_date: Data a verificar
            
        Returns:
            bool: True se é dia útil
        """
        try:
            # Normalizar data
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            elif isinstance(target_date, datetime):
                target_date = target_date.date()
            
            business_dates = self._load_business_dates()
            return target_date in business_dates
            
        except Exception as e:
            logger.error(f'Erro ao verificar se {target_date} é dia útil: {str(e)}')
            return False
    
    def get_business_day(self, n_days: int = 0, specific_date: Optional[Union[date, datetime, str]] = None) -> Optional[date]:
        """
        Obtém dia útil baseado em número de dias úteis atrás ou data específica.
        
        Args:
            n_days: Número de dias úteis atrás (0 = hoje, 1 = ontem útil, etc.)
            specific_date: Data específica para verificar/converter para dia útil
            
        Returns:
            Optional[date]: Data útil encontrada ou None se não encontrada
        """
        try:
            business_dates = self._load_business_dates()
            
            if specific_date is not None:
                # Normalizar data específica
                if isinstance(specific_date, str):
                    specific_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
                elif isinstance(specific_date, datetime):
                    specific_date = specific_date.date()
                
                # Se a data específica já é dia útil, retornar ela
                if specific_date in business_dates:
                    logger.debug(f'Data específica {specific_date} é dia útil')
                    return specific_date
                
                # Senão, buscar o dia útil anterior mais próximo
                business_dates_before = [d for d in business_dates if d < specific_date]
                if business_dates_before:
                    result = max(business_dates_before)
                    logger.info(f'Data específica {specific_date} não é dia útil. Dia útil anterior: {result}')
                    return result
                else:
                    logger.warning(f'Não foi encontrado dia útil anterior a {specific_date}')
                    return None
            
            else:
                # Buscar dia útil D-n a partir de hoje
                today = date.today()
                
                # Filtrar apenas dias úteis até hoje
                business_dates_until_today = [d for d in business_dates if d <= today]
                
                if not business_dates_until_today:
                    logger.error('Nenhum dia útil encontrado até hoje')
                    return None
                
                # Se n_days = 0, retornar hoje se for dia útil, senão último dia útil
                if n_days == 0:
                    if today in business_dates_until_today:
                        logger.debug(f'Hoje ({today}) é dia útil')
                        return today
                    else:
                        result = max(business_dates_until_today)
                        logger.info(f'Hoje ({today}) não é dia útil. Último dia útil: {result}')
                        return result
                
                # Buscar n-ésimo dia útil atrás
                business_dates_until_today.sort(reverse=True)  # Mais recentes primeiro
                
                if n_days >= len(business_dates_until_today):
                    logger.error(f'n_days={n_days} excede quantidade de dias úteis disponíveis ({len(business_dates_until_today)})')
                    return None
                
                result = business_dates_until_today[n_days]
                logger.info(f'Dia útil D-{n_days}: {result}')
                return result
                
        except Exception as e:
            logger.error(f'Erro ao calcular dia útil (n_days={n_days}, specific_date={specific_date}): {str(e)}')
            logger.error(traceback.format_exc())
            return None
    
    def get_next_business_day(self, from_date: Union[date, datetime, str]) -> Optional[date]:
        """
        Obtém próximo dia útil a partir de uma data.
        
        Args:
            from_date: Data de referência
            
        Returns:
            Optional[date]: Próximo dia útil ou None se não encontrado
        """
        try:
            # Normalizar data
            if isinstance(from_date, str):
                from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            elif isinstance(from_date, datetime):
                from_date = from_date.date()
            
            business_dates = self._load_business_dates()
            business_dates_after = [d for d in business_dates if d > from_date]
            
            if business_dates_after:
                result = min(business_dates_after)
                logger.debug(f'Próximo dia útil após {from_date}: {result}')
                return result
            else:
                logger.warning(f'Nenhum dia útil encontrado após {from_date}')
                return None
                
        except Exception as e:
            logger.error(f'Erro ao buscar próximo dia útil após {from_date}: {str(e)}')
            return None
    
    def get_previous_business_day(self, from_date: Union[date, datetime, str]) -> Optional[date]:
        """
        Obtém dia útil anterior a partir de uma data.
        
        Args:
            from_date: Data de referência
            
        Returns:
            Optional[date]: Dia útil anterior ou None se não encontrado
        """
        try:
            # Normalizar data
            if isinstance(from_date, str):
                from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            elif isinstance(from_date, datetime):
                from_date = from_date.date()
            
            business_dates = self._load_business_dates()
            business_dates_before = [d for d in business_dates if d < from_date]
            
            if business_dates_before:
                result = max(business_dates_before)
                logger.debug(f'Dia útil anterior a {from_date}: {result}')
                return result
            else:
                logger.warning(f'Nenhum dia útil encontrado antes de {from_date}')
                return None
                
        except Exception as e:
            logger.error(f'Erro ao buscar dia útil anterior a {from_date}: {str(e)}')
            return None
    
    def get_business_days_between(self, start_date: Union[date, datetime, str], 
                                 end_date: Union[date, datetime, str]) -> List[date]:
        """
        Obtém lista de dias úteis entre duas datas (inclusive).
        
        Args:
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            List[date]: Lista de dias úteis no período
        """
        try:
            # Normalizar datas
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            elif isinstance(start_date, datetime):
                start_date = start_date.date()
                
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            elif isinstance(end_date, datetime):
                end_date = end_date.date()
            
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            
            business_dates = self._load_business_dates()
            business_days_in_period = [d for d in business_dates if start_date <= d <= end_date]
            
            logger.debug(f'Dias úteis entre {start_date} e {end_date}: {len(business_days_in_period)}')
            return business_days_in_period
            
        except Exception as e:
            logger.error(f'Erro ao buscar dias úteis entre {start_date} e {end_date}: {str(e)}')
            return []
    
    def close(self):
        """Fecha conexão com banco de dados."""
        if self.connector:
            try:
                self.connector.close()
            except Exception as e:
                logger.error(f'Erro ao fechar conexão: {str(e)}')


# Instância global para reutilização
_global_calculator: Optional[BusinessDateCalculator] = None


def get_business_date_calculator() -> BusinessDateCalculator:
    """
    Obtém instância global do calculador de dias úteis.
    
    Returns:
        BusinessDateCalculator: Instância configurada
    """
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = BusinessDateCalculator()
    return _global_calculator


# Funções de conveniência para compatibilidade
def get_business_day(n_days: int = 0, specific_date: Optional[Union[date, datetime, str]] = None) -> Optional[date]:
    """
    Função de conveniência para obter dia útil.
    
    Args:
        n_days: Número de dias úteis atrás (0 = hoje, 1 = ontem útil, etc.)
        specific_date: Data específica para verificar/converter para dia útil
        
    Returns:
        Optional[date]: Data útil encontrada ou None se não encontrada
    """
    calculator = get_business_date_calculator()
    return calculator.get_business_day(n_days, specific_date)


def is_business_day(target_date: Union[date, datetime, str]) -> bool:
    """
    Função de conveniência para verificar se é dia útil.
    
    Args:
        target_date: Data a verificar
        
    Returns:
        bool: True se é dia útil
    """
    calculator = get_business_date_calculator()
    return calculator.is_business_day(target_date)


# Testes unitários integrados
def test_business_date_calculator() -> None:
    """
    Executa testes básicos do calculador de dias úteis.
    """
    logger.info('Iniciando testes do calculador de dias úteis')
    
    try:
        calculator = get_business_date_calculator()
        
        # Teste 1: Dia útil hoje ou anterior
        today_business = calculator.get_business_day(n_days=0)
        if today_business:
            logger.info(f'✅ Teste 1: Dia útil hoje/anterior: {today_business}')
        else:
            logger.error('❌ Teste 1: Falha ao obter dia útil atual')
        
        # Teste 2: 1 dia útil atrás
        yesterday_business = calculator.get_business_day(n_days=1)
        if yesterday_business:
            logger.info(f'✅ Teste 2: Dia útil D-1: {yesterday_business}')
        else:
            logger.error('❌ Teste 2: Falha ao obter dia útil D-1')
        
        # Teste 3: Data específica
        test_date = '2025-01-01'  # Provável feriado
        specific_business = calculator.get_business_day(specific_date=test_date)
        if specific_business:
            logger.info(f'✅ Teste 3: Dia útil para {test_date}: {specific_business}')
        else:
            logger.warning(f'⚠️  Teste 3: Nenhum dia útil encontrado para {test_date}')
        
        # Teste 4: Verificar se é dia útil
        if today_business:
            is_business = calculator.is_business_day(today_business)
            if is_business:
                logger.info(f'✅ Teste 4: {today_business} é dia útil: {is_business}')
            else:
                logger.error(f'❌ Teste 4: {today_business} deveria ser dia útil')
        
        logger.info('Testes concluídos')
        
    except Exception as e:
        logger.error(f'Erro durante os testes: {str(e)}')
        logger.error(traceback.format_exc())


def main() -> None:
    """
    Executa testes e demonstração do módulo.
    """
    # Configurar logging
    os.makedirs('logs', exist_ok=True)
    Log.set_level(LogLevel.INFO)
    Log.set_console_output(True)
    Log.set_log_file('logs/date_business_test.log', append=True)
    
    logger.info('=== TESTE DO MÓDULO DATE_BUSINESS ===')
    
    # Executar testes
    test_business_date_calculator()
    
    # Demonstração interativa
    logger.info('\n=== DEMONSTRAÇÃO INTERATIVA ===')
    
    try:
        calculator = get_business_date_calculator()
        
        # Exemplos de uso
        examples = [
            (0, None),  # Hoje
            (1, None),  # Ontem útil
            (5, None),  # 5 dias úteis atrás
            (None, '2025-01-01'),  # Data específica (Ano Novo)
            (None, '2025-12-25'),  # Data específica (Natal)
        ]
        
        for n_days, specific_date in examples:
            if specific_date:
                result = calculator.get_business_day(specific_date=specific_date)
                logger.info(f'Data específica {specific_date} → Dia útil: {result}')
            else:
                result = calculator.get_business_day(n_days=n_days)
                logger.info(f'D-{n_days} dias úteis → {result}')
        
        logger.info('=== DEMONSTRAÇÃO CONCLUÍDA ===')
        
    except Exception as e:
        logger.error(f'Erro na demonstração: {str(e)}')
        logger.error(traceback.format_exc())
    finally:
        calculator.close()


if __name__ == '__main__':
    main()