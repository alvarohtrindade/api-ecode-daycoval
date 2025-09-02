"""
Sistema de persistência e recuperação de portfolios que falharam no processamento.
Permite retry inteligente e rastreamento detalhado de falhas.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Tipos de falhas catalogadas."""
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    EMPTY_REPORT = "empty_report"
    PROCESSING_ERROR = "processing_error"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    """Registro detalhado de uma falha de portfolio."""
    portfolio_id: str
    portfolio_name: str
    failure_type: FailureType
    error_message: str
    timestamp: float
    attempt_count: int
    endpoint: str
    request_params: Dict[str, Any]
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável."""
        data = asdict(self)
        data['failure_type'] = self.failure_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailureRecord':
        """Cria instância a partir de dicionário."""
        data['failure_type'] = FailureType(data['failure_type'])
        return cls(**data)
    
    @property
    def age_minutes(self) -> float:
        """Idade da falha em minutos."""
        return (time.time() - self.timestamp) / 60
    
    @property
    def should_retry(self) -> bool:
        """Determina se deve tentar novamente baseado no tipo e tentativas."""
        retry_limits = {
            FailureType.API_ERROR: 5,
            FailureType.TIMEOUT: 3,
            FailureType.EMPTY_REPORT: 2,
            FailureType.PROCESSING_ERROR: 2,
            FailureType.RATE_LIMIT: 10,  # Rate limit pode ser temporário
            FailureType.AUTHENTICATION: 1,  # Erro de auth é crítico
            FailureType.UNKNOWN: 3
        }
        
        max_attempts = retry_limits.get(self.failure_type, 3)
        return self.attempt_count < max_attempts
    
    @property
    def retry_delay_seconds(self) -> float:
        """Calcula delay para próxima tentativa baseado no tipo de falha."""
        base_delays = {
            FailureType.API_ERROR: 60,     # API instável - aguardar mais
            FailureType.TIMEOUT: 30,       # Timeout - aguardar menos
            FailureType.EMPTY_REPORT: 120, # Report vazio - aguardar processamento
            FailureType.PROCESSING_ERROR: 180, # Erro processamento - aguardar mais
            FailureType.RATE_LIMIT: 300,   # Rate limit - aguardar bastante
            FailureType.AUTHENTICATION: 600, # Auth error - aguardar muito
            FailureType.UNKNOWN: 90
        }
        
        base_delay = base_delays.get(self.failure_type, 90)
        # Backoff exponencial baseado nas tentativas
        return base_delay * (2 ** (self.attempt_count - 1))


class FailedPortfolioManager:
    """Gerenciador de portfolios que falharam no processamento."""
    
    def __init__(self, checkpoint_dir: Path = Path('./checkpoints')):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.failures_file = self.checkpoint_dir / 'failed_portfolios.json'
        self._failures: Dict[str, FailureRecord] = {}
        self._load_failures()
    
    def _load_failures(self) -> None:
        """Carrega falhas persistidas do arquivo."""
        try:
            if self.failures_file.exists():
                with open(self.failures_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self._failures = {
                    portfolio_id: FailureRecord.from_dict(failure_data)
                    for portfolio_id, failure_data in data.items()
                }
                
                logger.info(f"Carregadas {len(self._failures)} falhas do checkpoint")
            else:
                logger.info("Nenhum checkpoint de falhas encontrado - iniciando limpo")
                
        except Exception as e:
            logger.error(f"Erro ao carregar falhas do checkpoint: {e}")
            self._failures = {}
    
    def _save_failures(self) -> None:
        """Persiste falhas no arquivo."""
        try:
            data = {
                portfolio_id: failure.to_dict()
                for portfolio_id, failure in self._failures.items()
            }
            
            # Backup do arquivo atual
            if self.failures_file.exists():
                backup_file = self.failures_file.with_suffix('.json.bak')
                self.failures_file.rename(backup_file)
            
            with open(self.failures_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Persistidas {len(self._failures)} falhas no checkpoint")
            
        except Exception as e:
            logger.error(f"Erro ao salvar falhas no checkpoint: {e}")
    
    def record_failure(
        self,
        portfolio_id: str,
        portfolio_name: str,
        failure_type: FailureType,
        error_message: str,
        endpoint: str,
        request_params: Dict[str, Any],
        stack_trace: Optional[str] = None
    ) -> None:
        """
        Registra uma falha de portfolio.
        
        Args:
            portfolio_id: ID do portfolio que falhou
            portfolio_name: Nome do portfolio
            failure_type: Tipo da falha
            error_message: Mensagem de erro
            endpoint: Endpoint que falhou
            request_params: Parâmetros da requisição
            stack_trace: Stack trace do erro (opcional)
        """
        # Se já existe, incrementa contador de tentativas
        if portfolio_id in self._failures:
            existing_failure = self._failures[portfolio_id]
            attempt_count = existing_failure.attempt_count + 1
        else:
            attempt_count = 1
        
        failure_record = FailureRecord(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio_name,
            failure_type=failure_type,
            error_message=error_message,
            timestamp=time.time(),
            attempt_count=attempt_count,
            endpoint=endpoint,
            request_params=request_params,
            stack_trace=stack_trace
        )
        
        self._failures[portfolio_id] = failure_record
        self._save_failures()
        
        logger.warning(
            f"Falha registrada: {portfolio_id} ({portfolio_name}) - "
            f"{failure_type.value} - Tentativa {attempt_count}"
        )
    
    def remove_success(self, portfolio_id: str) -> None:
        """Remove portfolio da lista de falhas (sucesso no processamento)."""
        if portfolio_id in self._failures:
            failure = self._failures.pop(portfolio_id)
            self._save_failures()
            logger.info(
                f"Sucesso registrado: {portfolio_id} removido das falhas "
                f"após {failure.attempt_count} tentativas"
            )
    
    def get_retryable_portfolios(self) -> List[FailureRecord]:
        """
        Retorna portfolios que devem ser reprocessados.
        
        Returns:
            Lista de registros de falha prontos para retry
        """
        current_time = time.time()
        retryable = []
        
        for failure in self._failures.values():
            if failure.should_retry:
                time_since_failure = current_time - failure.timestamp
                if time_since_failure >= failure.retry_delay_seconds:
                    retryable.append(failure)
        
        # Ordenar por prioridade: menos tentativas primeiro
        retryable.sort(key=lambda f: f.attempt_count)
        
        logger.info(f"Encontrados {len(retryable)} portfolios prontos para retry")
        return retryable
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas detalhadas das falhas.
        
        Returns:
            Dicionário com estatísticas das falhas
        """
        if not self._failures:
            return {
                'total_failures': 0,
                'by_type': {},
                'retryable': 0,
                'abandoned': 0
            }
        
        # Contagem por tipo
        type_counts = {}
        retryable_count = 0
        abandoned_count = 0
        
        for failure in self._failures.values():
            failure_type = failure.failure_type.value
            type_counts[failure_type] = type_counts.get(failure_type, 0) + 1
            
            if failure.should_retry:
                retryable_count += 1
            else:
                abandoned_count += 1
        
        return {
            'total_failures': len(self._failures),
            'by_type': type_counts,
            'retryable': retryable_count,
            'abandoned': abandoned_count,
            'oldest_failure_age_minutes': max(
                f.age_minutes for f in self._failures.values()
            ) if self._failures else 0
        }
    
    def get_failed_portfolio_ids(self) -> Set[str]:
        """Retorna IDs de todos os portfolios com falha."""
        return set(self._failures.keys())
    
    def get_failure_details(self, portfolio_id: str) -> Optional[FailureRecord]:
        """Retorna detalhes de falha para um portfolio específico."""
        return self._failures.get(portfolio_id)
    
    def clear_old_failures(self, max_age_hours: int = 24) -> int:
        """
        Remove falhas antigas do sistema.
        
        Args:
            max_age_hours: Idade máxima em horas para manter falhas
        
        Returns:
            Número de falhas removidas
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        old_failures = [
            portfolio_id for portfolio_id, failure in self._failures.items()
            if (current_time - failure.timestamp) > max_age_seconds
        ]
        
        for portfolio_id in old_failures:
            del self._failures[portfolio_id]
        
        if old_failures:
            self._save_failures()
            logger.info(f"Removidas {len(old_failures)} falhas antigas (>{max_age_hours}h)")
        
        return len(old_failures)
    
    def export_failure_report(self, output_file: Path) -> bool:
        """
        Exporta relatório detalhado das falhas para CSV.
        
        Args:
            output_file: Arquivo de saída
            
        Returns:
            True se exportou com sucesso
        """
        try:
            import csv
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'portfolio_id', 'portfolio_name', 'failure_type', 'error_message',
                    'timestamp', 'attempt_count', 'endpoint', 'age_minutes',
                    'should_retry', 'retry_delay_seconds'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for failure in self._failures.values():
                    row = {
                        'portfolio_id': failure.portfolio_id,
                        'portfolio_name': failure.portfolio_name,
                        'failure_type': failure.failure_type.value,
                        'error_message': failure.error_message,
                        'timestamp': datetime.fromtimestamp(failure.timestamp).isoformat(),
                        'attempt_count': failure.attempt_count,
                        'endpoint': failure.endpoint,
                        'age_minutes': round(failure.age_minutes, 1),
                        'should_retry': failure.should_retry,
                        'retry_delay_seconds': round(failure.retry_delay_seconds, 1)
                    }
                    writer.writerow(row)
            
            logger.info(f"Relatório de falhas exportado para {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao exportar relatório de falhas: {e}")
            return False


def classify_error(error: Exception) -> FailureType:
    """
    Classifica tipo de erro baseado na exceção.
    
    Args:
        error: Exceção capturada
        
    Returns:
        Tipo de falha classificado
    """
    from ..core.exceptions import (
        APIError, TimeoutError, EmptyReportError, 
        ReportProcessingError, RateLimitError, AuthenticationError
    )
    
    if isinstance(error, TimeoutError):
        return FailureType.TIMEOUT
    elif isinstance(error, EmptyReportError):
        return FailureType.EMPTY_REPORT
    elif isinstance(error, ReportProcessingError):
        return FailureType.PROCESSING_ERROR
    elif isinstance(error, RateLimitError):
        return FailureType.RATE_LIMIT
    elif isinstance(error, AuthenticationError):
        return FailureType.AUTHENTICATION
    elif isinstance(error, APIError):
        return FailureType.API_ERROR
    else:
        return FailureType.UNKNOWN


# Instância global para facilitar uso
_global_manager: Optional[FailedPortfolioManager] = None


def get_failed_portfolio_manager() -> FailedPortfolioManager:
    """Retorna instância global do gerenciador."""
    global _global_manager
    if _global_manager is None:
        _global_manager = FailedPortfolioManager()
    return _global_manager