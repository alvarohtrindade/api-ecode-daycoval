"""
Comandos CLI para relatórios diários.
"""
import os
import asyncio
from datetime import datetime
from pathlib import Path

import click

from ...config.portfolios import get_portfolio_manager
from ...services.daily_reports import create_daily_report_service
from ...core.models import ReportFormat, DailyReportRequest, ReportType
from ...core.exceptions import DaycovalError


@click.group()
def daily_cli():
    """Comandos para relatórios de carteira diária."""
    pass


@daily_cli.command('single')
@click.argument('portfolio_id')
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS', 'JSON']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--async-mode', is_flag=True, help='Usar modo assíncrono')
@click.pass_context
def single(ctx, portfolio_id: str, date: datetime, report_format: str, 
           output_dir: str, async_mode: bool):
    """Gera relatório para um único portfolio."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Obter portfolio
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"📊 Gerando relatório diário para:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        click.echo(f"   Formato: {report_format}")
        
        # Configurar serviço
        service = create_daily_report_service()
        
        # Criar requisição
        request = DailyReportRequest(
            portfolio=portfolio,
            date=date,
            format=ReportFormat(report_format),
            report_type=ReportType.DAILY
        )
        
        # Obter relatório
        if async_mode:
            report = asyncio.run(service.get_report(request))
        else:
            report = service.get_report_sync(request)
        
        # Salvar arquivo
        output_path = Path(output_dir)
        success = service.save_report(report, output_path)
        
        if success:
            click.echo(f"✅ Relatório salvo: {output_path / report.filename}")
            click.echo(f"📊 Tamanho: {report.size_mb:.2f} MB")
        else:
            click.echo("❌ Erro ao salvar relatório", err=True)
            return False
            
        return True
        
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


@daily_cli.command('batch')
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS', 'JSON']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--portfolios', help='IDs específicos (separados por vírgula)')
@click.option('--all-portfolios', is_flag=True, help='Todos os portfolios')
@click.option('--async-mode', is_flag=True, help='Usar modo assíncrono')
@click.option('--max-concurrent', default=5, help='Máximo de requisições simultâneas')
@click.pass_context
def batch(ctx, date: datetime, report_format: str, output_dir: str,
          portfolios: str, all_portfolios: bool, async_mode: bool, max_concurrent: int):
    """Gera relatórios em lote."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Determinar portfolios
        portfolio_manager = get_portfolio_manager()
        
        if all_portfolios:
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolio_list = list(portfolio_dict.values())
            click.echo(f"📊 Processando TODOS os {len(portfolio_list)} portfolios")
        elif portfolios:
            portfolio_ids = [p.strip() for p in portfolios.split(',')]
            portfolio_list = []
            for pid in portfolio_ids:
                portfolio_list.append(portfolio_manager.get_portfolio(pid))
            click.echo(f"📊 Processando {len(portfolio_list)} portfolios específicos")
        else:
            click.echo("❌ Especifique --all-portfolios ou --portfolios", err=True)
            return False
        
        click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        click.echo(f"   Formato: {report_format}")
        click.echo(f"   Modo: {'Assíncrono' if async_mode else 'Síncrono'}")
        
        # Configurar serviço
        service = create_daily_report_service()
        
        # Processar relatórios
        if async_mode:
            reports = asyncio.run(_process_batch_async(
                service, portfolio_list, date, report_format, max_concurrent
            ))
        else:
            reports = _process_batch_sync(
                service, portfolio_list, date, report_format
            )
        
        # Salvar relatórios
        output_path = Path(output_dir)
        successful, failed = service.save_multiple_reports(reports, output_path)
        
        # Estatísticas finais
        total = len(portfolio_list)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        click.echo(f"\n🎯 RESULTADO FINAL:")
        click.echo(f"   Total: {total}")
        click.echo(f"   ✅ Sucessos: {successful}")
        click.echo(f"   ❌ Falhas: {failed}")
        click.echo(f"   📈 Taxa de sucesso: {success_rate:.1f}%")
        
        return successful > 0
        
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


@daily_cli.command('validate')
@click.argument('portfolio_id')
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
def validate(portfolio_id: str, date: datetime):
    """Valida se um portfolio pode gerar relatório para uma data."""
    try:
        # Verificar portfolio
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"🔍 Validando:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        
        # Validações básicas
        if date > datetime.now():
            click.echo("❌ Data é futura")
            return False
        
        # Testar conectividade (sem fazer request real)
        from ...core.client import APIClient
        from ...config.settings import get_settings
        
        settings = get_settings()
        client = APIClient(settings.api)
        
        click.echo("✅ Portfolio válido")
        click.echo("✅ Data válida")
        click.echo("✅ Configuração OK")
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Validação falhou: {e}", err=True)
        return False


@daily_cli.command('retry-failed')
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS', 'JSON']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--failed-portfolios', help='IDs que falharam (separados por vírgula)')
@click.option('--timeout', default=120, help='Timeout em segundos para retry')
@click.pass_context
def retry_failed(ctx, date: datetime, report_format: str, output_dir: str,
                failed_portfolios: str, timeout: int):
    """Retenta portfolios que falharam com timeout maior."""
    verbose = ctx.obj.get('verbose', False)
    
    if not failed_portfolios:
        # Portfolios conhecidos por serem problemáticos
        problem_portfolios = [
            "8205906",   # Timeout frequente
            "10627715",  # Erro 500
            "18205906",  # Erro 500 
            "20784047"   # Erro 500
        ]
        click.echo(f"🔄 Testando portfolios problemáticos conhecidos:")
        for pid in problem_portfolios:
            click.echo(f"   {pid}")
    else:
        problem_portfolios = [p.strip() for p in failed_portfolios.split(',')]
        click.echo(f"🔄 Retentando {len(problem_portfolios)} portfolios específicos")
    
    try:
        # Configurar timeout maior
        os.environ['API_TIMEOUT'] = str(timeout)
        
        portfolio_manager = get_portfolio_manager()
        portfolio_list = []
        
        for pid in problem_portfolios:
            try:
                portfolio = portfolio_manager.get_portfolio(pid)
                portfolio_list.append(portfolio)
            except Exception as e:
                click.echo(f"❌ Portfolio {pid} não encontrado: {e}")
        
        if not portfolio_list:
            click.echo("❌ Nenhum portfolio válido para testar")
            return False
        
        click.echo(f"⏰ Timeout configurado: {timeout}s")
        
        # Processar com timeout maior
        service = create_daily_report_service()
        reports = _process_batch_sync(service, portfolio_list, date, report_format)
        
        # Salvar resultados
        output_path = Path(output_dir)
        successful, failed = service.save_multiple_reports(reports, output_path)
        
        click.echo(f"\n🎯 RESULTADO RETRY:")
        click.echo(f"   ✅ Sucessos: {successful}")
        click.echo(f"   ❌ Falhas: {failed}")
        
        return successful > 0
        
    except Exception as e:
        click.echo(f"❌ Erro no retry: {e}", err=True)
        return False


async def _process_batch_async(service, portfolios, date, report_format, max_concurrent):
    """Processa lote de forma assíncrona."""
    import asyncio
    from ...core.models import ReportFormat, ReportType
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single(portfolio):
        async with semaphore:
            try:
                request = DailyReportRequest(
                    portfolio=portfolio,
                    date=date,
                    format=ReportFormat(report_format),
                    report_type=ReportType.DAILY
                )
                return await service.get_report(request)
            except Exception as e:
                click.echo(f"❌ Erro no portfolio {portfolio.id}: {e}")
                return None
    
    # Executar todas as tarefas
    tasks = [process_single(p) for p in portfolios]
    results = await asyncio.gather(*tasks)
    
    # Filtrar apenas sucessos
    return [r for r in results if r is not None]


def _process_batch_sync(service, portfolios, date, report_format):
    """Processa lote de forma síncrona."""
    from ...core.models import ReportFormat, ReportType
    from ...core.exceptions import ReportProcessingError, EmptyReportError, TimeoutError
    
    reports = []
    processing_errors = []
    timeout_errors = []
    empty_errors = []
    
    for i, portfolio in enumerate(portfolios, 1):
        try:
            click.echo(f"🔄 Processando {i}/{len(portfolios)}: {portfolio.id}")
            
            request = DailyReportRequest(
                portfolio=portfolio,
                date=date,
                format=ReportFormat(report_format),
                report_type=ReportType.DAILY
            )
            
            report = service.get_report_sync(request)
            reports.append(report)
            
        except ReportProcessingError as e:
            processing_errors.append((portfolio.id, str(e)))
            click.echo(f"⏳ Portfolio {portfolio.id}: Relatório em processamento")
            
        except EmptyReportError as e:
            empty_errors.append((portfolio.id, str(e)))
            click.echo(f"📄 Portfolio {portfolio.id}: Relatório vazio")
            
        except TimeoutError as e:
            timeout_errors.append((portfolio.id, str(e)))
            click.echo(f"⏰ Portfolio {portfolio.id}: Timeout")
            
        except Exception as e:
            click.echo(f"❌ Erro no portfolio {portfolio.id}: {e}")
    
    # Mostrar estatísticas detalhadas
    if processing_errors:
        click.echo(f"\n⏳ {len(processing_errors)} portfolios em processamento:")
        for pid, _ in processing_errors[:5]:  # Mostrar primeiros 5
            click.echo(f"   {pid}")
        if len(processing_errors) > 5:
            click.echo(f"   ... e mais {len(processing_errors) - 5}")
    
    if timeout_errors:
        click.echo(f"\n⏰ {len(timeout_errors)} portfolios com timeout:")
        for pid, _ in timeout_errors[:5]:
            click.echo(f"   {pid}")
        if len(timeout_errors) > 5:
            click.echo(f"   ... e mais {len(timeout_errors) - 5}")
    
    if empty_errors:
        click.echo(f"\n📄 {len(empty_errors)} portfolios com relatórios vazios:")
        for pid, _ in empty_errors[:5]:
            click.echo(f"   {pid}")
        if len(empty_errors) > 5:
            click.echo(f"   ... e mais {len(empty_errors) - 5}")
    
    return reports