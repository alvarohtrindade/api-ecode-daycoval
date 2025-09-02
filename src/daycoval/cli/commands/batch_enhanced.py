"""
Comandos CLI aprimorados para processamento em lote com retry inteligente.
"""

from datetime import datetime
from pathlib import Path

import click

from ...config.portfolios import get_portfolio_manager
from ...services.enhanced_batch_processor import create_enhanced_batch_processor
from ...core.models import ReportFormat, SyntheticProfitabilityRequest, DEFAULT_ALL_PORTFOLIOS_LABEL
from ...core.exceptions import DaycovalError
from ...core.failed_portfolio_manager import get_failed_portfolio_manager


@click.group()
def batch_enhanced_cli():
    """Comandos aprimorados para processamento em lote."""
    pass


@batch_enhanced_cli.command('synthetic-enhanced')
@click.option('--format', 'report_format', default='CSVBR',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--portfolios', help='IDs específicos (separados por vírgula)')
@click.option('--all-portfolios', is_flag=True, help='Todos os portfolios')
@click.option('--daily-base', is_flag=True, help='Usar base diária')
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), help='Data inicial')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), help='Data final')
@click.option('--profitability-type', default=0, type=click.Choice(['0', '1', '2']))
@click.option('--max-parallel', default=3, help='Máximo de requests paralelos')
@click.option('--rate-limit-delay', default=1.0, help='Delay entre requests (segundos)')
@click.pass_context
def synthetic_enhanced(
    ctx, report_format: str, output_dir: str, portfolios: str, all_portfolios: bool,
    daily_base: bool, start_date: datetime, end_date: datetime, profitability_type: str,
    max_parallel: int, rate_limit_delay: float
):
    """Processamento sintético aprimorado com retry inteligente."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Validações
        if daily_base and (not start_date or not end_date):
            click.echo("❌ Para base diária, --start-date e --end-date são obrigatórios", err=True)
            return False
        
        # Determinar portfolios
        portfolio_manager = get_portfolio_manager()
        
        if all_portfolios:
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolio_list = list(portfolio_dict.values())
            click.echo(f"📊 Processamento APRIMORADO de TODOS os {len(portfolio_list)} portfolios")
        elif portfolios:
            portfolio_ids = [p.strip() for p in portfolios.split(',')]
            portfolio_list = []
            for pid in portfolio_ids:
                portfolio_list.append(portfolio_manager.get_portfolio(pid))
            click.echo(f"📊 Processamento APRIMORADO de {len(portfolio_list)} portfolios específicos")
        else:
            click.echo("❌ Especifique --all-portfolios ou --portfolios", err=True)
            return False
        
        click.echo(f"   Formato: {report_format}")
        click.echo(f"   Retry inteligente: ✅ ATIVO")
        click.echo(f"   Persistência de falhas: ✅ ATIVO")
        click.echo(f"   Rate limiting: {rate_limit_delay}s entre requests")
        if daily_base:
            click.echo(f"   Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        
        # Criar request base
        base_request = SyntheticProfitabilityRequest(
            portfolio=None,  # Será personalizado para cada portfolio
            date=end_date if daily_base and end_date else datetime.now(),
            format=ReportFormat(report_format),
            report_type=1048,
            daily_base=daily_base,
            start_date=start_date if daily_base else None,
            end_date=end_date if daily_base else None,
            profitability_index_type=int(profitability_type),
            emit_d0_opening_position=False
        )
        
        # Criar processador aprimorado
        processor = create_enhanced_batch_processor()
        processor.max_parallel_requests = max_parallel
        processor.rate_limit_delay = rate_limit_delay
        
        # Processar com retry inteligente
        output_path = Path(output_dir)
        successful_reports, stats = processor.process_portfolio_batch(
            portfolios=portfolio_list,
            base_request=base_request,
            save_individual=True,
            output_dir=output_path
        )
        
        # Consolidar CSVs se aplicável
        if report_format.startswith('CSV') and successful_reports:
            click.echo("\n🔄 Gerando arquivo consolidado...")
            
            consolidation_type = "SINTETICA_ENHANCED"
            date_str = (end_date or datetime.now()).strftime('%Y%m%d')
            consolidated_filename = f"CONSOLIDADO_{consolidation_type}_TODOS_FUNDOS_{date_str}.csv"
            consolidated_path = output_path / consolidated_filename
            
            from ...services.profitability_reports import ProfitabilityReportService
            if ProfitabilityReportService.consolidate_csv_reports(
                successful_reports, consolidated_path, "1048"
            ):
                click.echo(f"      ✅ Consolidado: {consolidated_filename}")
            else:
                click.echo(f"      ❌ Erro no consolidado")
        
        # Estatísticas finais
        total = len(portfolio_list)
        success_rate = stats.success_rate
        processing_time = stats.processing_time_seconds / 60  # minutos
        
        click.echo(f"\n🎯 RESULTADO FINAL (ENHANCED):")
        click.echo(f"   Total portfolios: {total}")
        click.echo(f"   ✅ Sucessos: {stats.successful_count}")
        click.echo(f"   ❌ Falhas: {stats.failed_count}")
        click.echo(f"   🔴 Circuit Breakers: {stats.circuit_breaker_count}")
        click.echo(f"   📈 Taxa de sucesso: {success_rate:.1f}%")
        click.echo(f"   ⏱️ Tempo total: {processing_time:.1f} minutos")
        click.echo(f"   📁 Diretório: {output_path}")
        
        # Determinar status de sucesso melhorado
        target_success_rate = 90.0
        if success_rate >= target_success_rate:
            click.echo(f"🎉 META ATINGIDA: Taxa de sucesso {success_rate:.1f}% >= {target_success_rate}%")
        else:
            click.echo(f"⚠️ Abaixo da meta: {success_rate:.1f}% < {target_success_rate}%")
            click.echo("💡 Dica: Use 'retry-failures' para reprocessar falhas")
        
        return success_rate >= 70.0  # Critério mínimo de sucesso
        
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


@batch_enhanced_cli.command('retry-failures')
@click.option('--format', 'report_format', default='CSVBR',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--max-portfolios', type=int, help='Máximo de portfolios para reprocessar')
@click.option('--daily-base', is_flag=True, help='Usar base diária')
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), help='Data inicial')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), help='Data final')
@click.option('--profitability-type', default=0, type=click.Choice(['0', '1', '2']))
@click.pass_context
def retry_failures(
    ctx, report_format: str, output_dir: str, max_portfolios: int,
    daily_base: bool, start_date: datetime, end_date: datetime, profitability_type: str
):
    """Reprocessa portfolios que falharam com retry inteligente."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Verificar falhas disponíveis
        failure_manager = get_failed_portfolio_manager()
        failure_stats = failure_manager.get_failure_statistics()
        
        if failure_stats['retryable'] == 0:
            click.echo("ℹ️ Nenhum portfolio está disponível para reprocessamento")
            click.echo(f"   Total de falhas: {failure_stats['total_failures']}")
            click.echo(f"   Abandonadas (muitas tentativas): {failure_stats['abandoned']}")
            return True
        
        click.echo(f"🔄 REPROCESSAMENTO DE FALHAS:")
        click.echo(f"   Portfolios disponíveis: {failure_stats['retryable']}")
        if max_portfolios:
            click.echo(f"   Limitado a: {max_portfolios}")
        
        # Criar request base
        base_request = SyntheticProfitabilityRequest(
            portfolio=None,
            date=end_date if daily_base and end_date else datetime.now(),
            format=ReportFormat(report_format),
            report_type=1048,
            daily_base=daily_base,
            start_date=start_date if daily_base else None,
            end_date=end_date if daily_base else None,
            profitability_index_type=int(profitability_type),
            emit_d0_opening_position=False
        )
        
        # Criar processador e reprocessar falhas
        processor = create_enhanced_batch_processor()
        output_path = Path(output_dir)
        
        recovered_reports, stats = processor.process_failed_portfolios_retry(
            base_request=base_request,
            save_individual=True,
            output_dir=output_path,
            max_portfolios=max_portfolios
        )
        
        # Estatísticas de recuperação
        recovery_count = stats.successful_count
        click.echo(f"\n🎯 RESULTADO DO REPROCESSAMENTO:")
        click.echo(f"   ✅ Recuperados: {recovery_count}")
        click.echo(f"   ❌ Ainda falhando: {stats.failed_count}")
        
        if recovery_count > 0:
            click.echo(f"🎉 Sucesso! {recovery_count} portfolios foram recuperados")
        else:
            click.echo("⚠️ Nenhum portfolio foi recuperado nesta execução")
        
        return recovery_count > 0
        
    except Exception as e:
        click.echo(f"❌ Erro no reprocessamento: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


@batch_enhanced_cli.command('failure-stats')
@click.option('--export-csv', help='Exportar relatório detalhado para CSV')
@click.option('--clear-old', type=int, help='Limpar falhas antigas (horas)')
def failure_stats(export_csv: str, clear_old: int):
    """Exibe estatísticas detalhadas das falhas."""
    try:
        failure_manager = get_failed_portfolio_manager()
        
        # Limpar falhas antigas se solicitado
        if clear_old:
            cleared = failure_manager.clear_old_failures(clear_old)
            if cleared > 0:
                click.echo(f"🧹 Removidas {cleared} falhas antigas (>{clear_old}h)")
        
        # Obter estatísticas
        stats = failure_manager.get_failure_statistics()
        
        click.echo("📊 ESTATÍSTICAS DE FALHAS:")
        click.echo(f"   Total acumulado: {stats['total_failures']}")
        click.echo(f"   ✅ Pode reprocessar: {stats['retryable']}")
        click.echo(f"   ❌ Abandonados: {stats['abandoned']}")
        
        if stats['oldest_failure_age_minutes'] > 0:
            age_hours = stats['oldest_failure_age_minutes'] / 60
            click.echo(f"   🕐 Falha mais antiga: {age_hours:.1f} horas")
        
        if stats['by_type']:
            click.echo("\n🔍 FALHAS POR TIPO:")
            for failure_type, count in stats['by_type'].items():
                click.echo(f"   {failure_type}: {count}")
        
        # Exportar para CSV se solicitado
        if export_csv:
            export_path = Path(export_csv)
            if failure_manager.export_failure_report(export_path):
                click.echo(f"📄 Relatório exportado: {export_path}")
            else:
                click.echo("❌ Erro ao exportar relatório")
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro ao obter estatísticas: {e}", err=True)
        return False


@batch_enhanced_cli.command('clear-successes')
@click.confirmation_option(prompt='Tem certeza que deseja limpar todos os sucessos registrados?')
def clear_successes():
    """Limpa portfolios que tiveram sucesso da lista de falhas."""
    try:
        # Esta funcionalidade é automática no sistema atual
        # mas poderia ser expandida para limpeza manual
        click.echo("ℹ️ Sucessos são automaticamente removidos das falhas")
        click.echo("💡 Use 'failure-stats --clear-old HORAS' para limpeza geral")
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro na limpeza: {e}", err=True)
        return False