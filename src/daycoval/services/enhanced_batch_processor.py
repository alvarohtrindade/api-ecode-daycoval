"""
Processador em lote aprimorado com retry inteligente e persistência de falhas.
Aumenta significativamente a taxa de sucesso em processamentos batch.
"""

import time
import traceback
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging

import click

# Adicionar o diretório raiz do projeto ao Python path para importar utils
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from utils.backoff_utils import with_backoff_jitter, CircuitBreakerOpenError
from ..core.models import ReportResponse, SyntheticProfitabilityRequest, ProfitabilityRequest, BankStatementRequest, Portfolio, ReportRequest
from ..core.exceptions import DaycovalError
from ..core.failed_portfolio_manager import (
    FailedPortfolioManager, classify_error, get_failed_portfolio_manager
)
from .profitability_reports import ProfitabilityReportService

logger = logging.getLogger(__name__)


class EnhancedBatchProcessor:
    """Processador em lote com retry inteligente e recuperação de falhas."""
    
    def __init__(
        self,
        service: ProfitabilityReportService,
        failure_manager: Optional[FailedPortfolioManager] = None,
        max_parallel_requests: int = 3,
        rate_limit_delay: float = 1.0
    ):
        self.service = service
        self.failure_manager = failure_manager or get_failed_portfolio_manager()
        self.max_parallel_requests = max_parallel_requests
        self.rate_limit_delay = rate_limit_delay
        self.stats = BatchProcessingStats()
    
    @with_backoff_jitter(
        max_attempts=5,
        base_wait=2.0,
        jitter=0.3,
        retryable_exceptions=(DaycovalError, Exception)
    )
    def _process_single_portfolio_with_retry(
        self,
        portfolio: Portfolio,
        request: ReportRequest
    ) -> Optional[ReportResponse]:
        """
        Processa um portfolio com retry inteligente.
        
        Args:
            portfolio: Portfolio a processar
            request: Request configurada para o portfolio
            
        Returns:
            Relatório se bem-sucedido, None se falhou
        """
        try:
            # Rate limiting básico
            time.sleep(self.rate_limit_delay)
            
            # Processar o relatório baseado no tipo de request
            if isinstance(request, SyntheticProfitabilityRequest):
                report = self.service.get_synthetic_profitability_report_sync(request)
                endpoint = "1048"
            elif isinstance(request, ProfitabilityRequest):
                report = self.service.get_profitability_report_sync(request)
                endpoint = "1799"
            elif isinstance(request, BankStatementRequest):
                report = self.service.get_bank_statement_report_sync(request)
                endpoint = "1988"
            else:
                raise ValueError(f"Tipo de request não suportado: {type(request)}")
            
            # Remover da lista de falhas se estava lá
            self.failure_manager.remove_success(portfolio.id)
            
            self.stats.record_success(portfolio.id)
            logger.info(f"✅ Sucesso: {portfolio.id} ({portfolio.name}) - Endpoint {endpoint}")
            
            return report
            
        except Exception as e:
            # Classificar e registrar a falha
            failure_type = classify_error(e)
            
            # Determinar endpoint para logging de erro
            if isinstance(request, SyntheticProfitabilityRequest):
                endpoint = "1048"
            elif isinstance(request, ProfitabilityRequest):
                endpoint = "1799"
            elif isinstance(request, BankStatementRequest):
                endpoint = "1988"
            else:
                endpoint = "unknown"
            
            self.failure_manager.record_failure(
                portfolio_id=portfolio.id,
                portfolio_name=portfolio.name,
                failure_type=failure_type,
                error_message=str(e),
                endpoint=endpoint,
                request_params=request.to_api_params(),
                stack_trace=traceback.format_exc()
            )
            
            self.stats.record_failure(portfolio.id, failure_type)
            logger.error(f"❌ Falha: {portfolio.id} - {failure_type.value}: {e}")
            
            # Re-lançar para o sistema de retry
            raise
    
    def process_portfolio_batch(
        self,
        portfolios: List[Portfolio],
        base_request: ReportRequest,
        save_individual: bool = True,
        output_dir: Optional[Path] = None
    ) -> Tuple[List[ReportResponse], 'BatchProcessingStats']:
        """
        Processa lote de portfolios com retry inteligente.
        
        Args:
            portfolios: Lista de portfolios para processar
            base_request: Request base (será customizada para cada portfolio)
            save_individual: Se deve salvar arquivos individuais
            output_dir: Diretório de saída (se save_individual=True)
            
        Returns:
            Tuple com (relatórios_bem_sucedidos, estatísticas)
        """
        logger.info(f"🚀 Iniciando processamento em lote de {len(portfolios)} portfolios")
        
        successful_reports = []
        self.stats.reset()
        
        for i, portfolio in enumerate(portfolios, 1):
            try:
                click.echo(f"🔄 Processando {i}/{len(portfolios)}: {portfolio.id} ({portfolio.name})")
                
                # Personalizar request para este portfolio baseado no tipo
                if isinstance(base_request, SyntheticProfitabilityRequest):
                    individual_request = SyntheticProfitabilityRequest(
                        portfolio=portfolio,
                        date=base_request.date,
                        format=base_request.format,
                        report_type=base_request.report_type,
                        daily_base=base_request.daily_base,
                        start_date=base_request.start_date,
                        end_date=base_request.end_date,
                        profitability_index_type=base_request.profitability_index_type,
                        emit_d0_opening_position=base_request.emit_d0_opening_position
                    )
                elif isinstance(base_request, ProfitabilityRequest):
                    individual_request = ProfitabilityRequest(
                        portfolio=portfolio,
                        date=base_request.date,
                        format=base_request.format,
                        report_type=base_request.report_type,
                        report_date=base_request.report_date,
                        left_report_name=base_request.left_report_name,
                        omit_logo=base_request.omit_logo,
                        use_short_portfolio_name=base_request.use_short_portfolio_name,
                        use_long_title_name=base_request.use_long_title_name,
                        handle_shared_adjustment_movement=base_request.handle_shared_adjustment_movement,
                        cdi_index=base_request.cdi_index
                    )
                elif isinstance(base_request, BankStatementRequest):
                    individual_request = BankStatementRequest(
                        portfolio=portfolio,
                        date=base_request.date,
                        format=base_request.format,
                        report_type=base_request.report_type,
                        start_date=base_request.start_date,
                        end_date=base_request.end_date,
                        agency=base_request.agency,
                        account=base_request.account,
                        days=base_request.days,
                        left_report_name=base_request.left_report_name,
                        omit_logo=base_request.omit_logo,
                        use_short_portfolio_name=base_request.use_short_portfolio_name
                    )
                else:
                    raise ValueError(f"Tipo de request não suportado para batch: {type(base_request)}")
                
                # Processar com retry inteligente
                report = self._process_single_portfolio_with_retry(portfolio, individual_request)
                
                if report:
                    successful_reports.append(report)
                    
                    # Salvar arquivo individual se solicitado
                    if save_individual and output_dir:
                        if self.service.save_report(report, output_dir):
                            click.echo(f"      📁 Salvo: {report.filename}")
                        else:
                            click.echo(f"      ⚠️ Erro ao salvar arquivo")
                    
                    click.echo(f"      ✅ Processado: {report.size_mb:.2f} MB")
                
            except CircuitBreakerOpenError:
                click.echo(f"      🔴 Circuit breaker aberto - pulando temporariamente")
                self.stats.record_circuit_breaker(portfolio.id)
                
            except Exception as e:
                # Erro já foi registrado pelo método com retry
                click.echo(f"      ❌ Falha final após retries: {str(e)[:100]}")
        
        # Estatísticas finais
        self._show_processing_summary()
        
        logger.info(
            f"Batch processado: {len(successful_reports)}/{len(portfolios)} sucessos "
            f"({self.stats.success_rate:.1f}%)"
        )
        
        return successful_reports, self.stats
    
    def process_failed_portfolios_retry(
        self,
        base_request: ReportRequest,
        save_individual: bool = True,
        output_dir: Optional[Path] = None,
        max_portfolios: Optional[int] = None
    ) -> Tuple[List[ReportResponse], 'BatchProcessingStats']:
        """
        Reprocessa portfolios que falharam anteriormente.
        
        Args:
            base_request: Request base
            save_individual: Se deve salvar arquivos individuais
            output_dir: Diretório de saída
            max_portfolios: Máximo de portfolios para reprocessar (None = todos)
            
        Returns:
            Tuple com (relatórios_recuperados, estatísticas)
        """
        retryable_failures = self.failure_manager.get_retryable_portfolios()
        
        if not retryable_failures:
            click.echo("ℹ️ Nenhum portfolio falhou para reprocessar")
            return [], BatchProcessingStats()
        
        if max_portfolios:
            retryable_failures = retryable_failures[:max_portfolios]
        
        click.echo(f"🔄 Reprocessando {len(retryable_failures)} portfolios que falharam")
        
        # Converter failure records para portfolios
        from ..config.portfolios import get_portfolio_manager
        portfolio_manager = get_portfolio_manager()
        
        portfolios_to_retry = []
        for failure in retryable_failures:
            try:
                portfolio = portfolio_manager.get_portfolio(failure.portfolio_id)
                portfolios_to_retry.append(portfolio)
            except Exception as e:
                logger.warning(f"Portfolio {failure.portfolio_id} não encontrado: {e}")
        
        # Processar com retry
        return self.process_portfolio_batch(
            portfolios_to_retry, base_request, save_individual, output_dir
        )
    
    def _show_processing_summary(self) -> None:
        """Exibe resumo detalhado do processamento."""
        stats = self.stats
        
        click.echo(f"\n📊 RESUMO DO PROCESSAMENTO:")
        click.echo(f"   ✅ Sucessos: {stats.successful_count}")
        click.echo(f"   ❌ Falhas: {stats.failed_count}")
        click.echo(f"   🔴 Circuit Breaker: {stats.circuit_breaker_count}")
        click.echo(f"   📈 Taxa de Sucesso: {stats.success_rate:.1f}%")
        
        if stats.failures_by_type:
            click.echo(f"\n🔍 FALHAS POR TIPO:")
            for failure_type, count in stats.failures_by_type.items():
                click.echo(f"   {failure_type}: {count}")
        
        # Estatísticas do failure manager
        failure_stats = self.failure_manager.get_failure_statistics()
        if failure_stats['total_failures'] > 0:
            click.echo(f"\n📋 HISTÓRICO DE FALHAS:")
            click.echo(f"   Total acumulado: {failure_stats['total_failures']}")
            click.echo(f"   Pode reprocessar: {failure_stats['retryable']}")
            click.echo(f"   Abandonados: {failure_stats['abandoned']}")


class BatchProcessingStats:
    """Estatísticas detalhadas do processamento em lote."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reinicia contadores."""
        self.successful_portfolios = set()
        self.failed_portfolios = set()
        self.circuit_breaker_portfolios = set()
        self.failures_by_type = {}
        self.start_time = time.time()
    
    def record_success(self, portfolio_id: str):
        """Registra sucesso."""
        self.successful_portfolios.add(portfolio_id)
    
    def record_failure(self, portfolio_id: str, failure_type):
        """Registra falha."""
        self.failed_portfolios.add(portfolio_id)
        failure_type_str = failure_type.value if hasattr(failure_type, 'value') else str(failure_type)
        self.failures_by_type[failure_type_str] = self.failures_by_type.get(failure_type_str, 0) + 1
    
    def record_circuit_breaker(self, portfolio_id: str):
        """Registra circuit breaker."""
        self.circuit_breaker_portfolios.add(portfolio_id)
    
    @property
    def successful_count(self) -> int:
        return len(self.successful_portfolios)
    
    @property
    def failed_count(self) -> int:
        return len(self.failed_portfolios)
    
    @property
    def circuit_breaker_count(self) -> int:
        return len(self.circuit_breaker_portfolios)
    
    @property
    def total_processed(self) -> int:
        return self.successful_count + self.failed_count + self.circuit_breaker_count
    
    @property
    def success_rate(self) -> float:
        total = self.total_processed
        return (self.successful_count / total * 100) if total > 0 else 0.0
    
    @property
    def processing_time_seconds(self) -> float:
        return time.time() - self.start_time


def create_enhanced_batch_processor() -> EnhancedBatchProcessor:
    """Cria instância do processador aprimorado com configurações padrão."""
    from .profitability_reports import create_profitability_service
    
    service = create_profitability_service()
    return EnhancedBatchProcessor(service)