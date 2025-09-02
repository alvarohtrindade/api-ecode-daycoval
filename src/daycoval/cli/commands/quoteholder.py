"""
Comandos CLI para relatórios de cotistas (endpoint 45).
"""
import os
import asyncio
from datetime import datetime
from pathlib import Path

import click

from ...config.portfolios import get_portfolio_manager
from ...core.models import ReportFormat, ReportType
from ...core.exceptions import DaycovalError


@click.group()
def quoteholder_cli():
    """Comandos para relatórios de posição de cotistas."""
    pass


@quoteholder_cli.command('single')
@click.argument('portfolio_id')
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--auto-dir', is_flag=True, help='Criar diretório automático baseado na data')
@click.option('--base-drive', default='F:', help='Drive base para diretório automático')
@click.pass_context
def single(ctx, portfolio_id: str, date: datetime, report_format: str, 
           output_dir: str, auto_dir: bool, base_drive: str):
    """Gera relatório de cotistas para um único portfolio."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Obter portfolio
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"👥 Gerando relatório de cotistas para:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        click.echo(f"   Formato: {report_format}")
        
        # Configurar diretório de saída
        if auto_dir:
            from ...utils.file_utils import create_endpoint_directory
            output_path = create_endpoint_directory(45, base_drive, date)
            click.echo(f"📁 Diretório criado: {output_path}")
        else:
            output_path = Path(output_dir)
        
        # Criar serviço de cotistas
        service = _create_quoteholder_service()
        
        # Obter relatório
        report = service.get_quoteholder_report_sync(portfolio, date, report_format)
        
        # Salvar arquivo
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


@quoteholder_cli.command('batch')
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--portfolios', help='IDs específicos (separados por vírgula)')
@click.option('--all-portfolios', is_flag=True, help='Todos os portfolios')
@click.option('--auto-dir', is_flag=True, help='Criar diretório automático baseado na data')
@click.option('--base-drive', default='F:', help='Drive base para diretório automático')
@click.pass_context
def batch(ctx, date: datetime, report_format: str, output_dir: str,
          portfolios: str, all_portfolios: bool, auto_dir: bool, base_drive: str):
    """Gera relatórios de cotistas em lote."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Determinar portfolios
        portfolio_manager = get_portfolio_manager()
        
        if all_portfolios:
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolio_list = [p for p in portfolio_dict.values() if p.id and p.id.strip()]  # Filtrar portfolios válidos
            click.echo(f"👥 Processando TODOS os {len(portfolio_list)} portfolios de cotistas")
        elif portfolios:
            portfolio_ids = [p.strip() for p in portfolios.split(',')]
            portfolio_list = []
            for pid in portfolio_ids:
                portfolio_list.append(portfolio_manager.get_portfolio(pid))
            click.echo(f"👥 Processando {len(portfolio_list)} portfolios específicos")
        else:
            click.echo("❌ Especifique --all-portfolios ou --portfolios", err=True)
            return False
        
        click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        click.echo(f"   Formato: {report_format}")
        
        # Configurar diretório de saída
        if auto_dir:
            from ...utils.file_utils import create_endpoint_directory
            output_path = create_endpoint_directory(45, base_drive, date)
            click.echo(f"📁 Diretório criado: {output_path}")
        else:
            output_path = Path(output_dir)
        
        # Criar serviço
        service = _create_quoteholder_service()
        
        # Processar relatórios
        reports = _process_quoteholder_batch_sync(service, portfolio_list, date, report_format)
        
        # Salvar relatórios
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


@quoteholder_cli.command('test')
@click.argument('portfolio_id')
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
def test_endpoint(portfolio_id: str, date: datetime):
    """Testa se endpoint 45 funciona para um portfolio."""
    try:
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"🧪 Testando endpoint 45 para:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        
        # Testar apenas a requisição
        from ...core.client import APIClient
        from ...config.settings import get_settings
        
        settings = get_settings()
        client = APIClient(settings.api)
        
        params = {
            "carteira": portfolio.id,
            "format": "JSON",  # JSON para debug
            "data": date.strftime('%Y-%m-%d'),
            "nomeRelatorioEsquerda": True,
            "omiteLogotipo": False,
            "usaNomeCurtoCarteira": False,
            "clienteInicial": 1,
            "clienteFinal": 999999999999,
            "assessorInicial": 1,
            "assessorFinal": 99999,
            "assessor2Inicial": 0,
            "assessor2Final": 0,
            "classeInvestidor": -1,
            "apresentaCodigoIF": True,
            "geraArquivoFormatoExcelHeaders": False,
            "mensagem": ""
        }
        
        click.echo("🔄 Fazendo requisição para endpoint 45...")
        response = client.post_sync("/report/reports/45", params)
        
        click.echo(f"✅ Resposta recebida:")
        click.echo(f"   Status: {response.status_code}")
        click.echo(f"   Content-Type: {response.headers.get('Content-Type')}")
        click.echo(f"   Tamanho: {len(response.text)} chars")
        
        # Mostrar início da resposta
        preview = response.text[:200]
        click.echo(f"   Preview: {preview}...")
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro no teste: {e}")
        return False


def _create_quoteholder_service():
    """Cria serviço de cotistas simplificado."""
    from ...services.daily_reports import create_daily_report_service
    from ...core.client import APIClient
    from ...config.settings import get_settings
    
    class QuoteholderService:
        def __init__(self):
            settings = get_settings()
            self.client = APIClient(settings.api)
        
        def get_quoteholder_report_sync(self, portfolio, date, format):
            from ...core.models import ReportResponse
            from ...utils.file_utils import generate_filename
            
            # Fazer requisição para endpoint 45
            endpoint = "/report/reports/45"
            params = {
                "carteira": portfolio.id,
                "format": format,
                "data": date.strftime('%Y-%m-%d'),
                "nomeRelatorioEsquerda": True,
                "omiteLogotipo": False,
                "usaNomeCurtoCarteira": False,
                "clienteInicial": 1,
                "clienteFinal": 999999999999,
                "assessorInicial": 1,
                "assessorFinal": 99999,
                "assessor2Inicial": 0,
                "assessor2Final": 0,
                "classeInvestidor": -1,
                "apresentaCodigoIF": True,
                "geraArquivoFormatoExcelHeaders": False,
                "mensagem": ""
            }
            
            response = self.client.post_sync(endpoint, params)
            
            # Processar resposta
            if format == 'PDF':
                content = response.content
                content_type = 'application/pdf'
            else:
                content = response.text
                content_type = 'text/plain'
            
            filename = f"POSICAO_COTISTAS_{generate_filename(portfolio.name, date, ReportFormat(format)).replace('.pdf', '').replace('.csv', '')}.{format.lower()}"
            
            return ReportResponse(
                content=content,
                content_type=content_type,
                filename=filename,
                portfolio=portfolio,
                date=date,
                format=ReportFormat(format),
                size_bytes=0
            )
        
        def save_report(self, report, output_dir):
            file_path = output_dir / report.filename
            return report.save_to_file(file_path)
        
        def save_multiple_reports(self, reports, output_dir):
            output_dir.mkdir(parents=True, exist_ok=True)
            successful = 0
            failed = 0
            
            for report in reports:
                if self.save_report(report, output_dir):
                    successful += 1
                else:
                    failed += 1
            
            return successful, failed
    
    return QuoteholderService()


def _process_quoteholder_batch_sync(service, portfolios, date, report_format):
    """Processa lote de cotistas de forma síncrona."""
    reports = []
    
    for i, portfolio in enumerate(portfolios, 1):
        try:
            click.echo(f"🔄 Processando {i}/{len(portfolios)}: {portfolio.id}")
            
            # Verificar se portfolio é válido
            if not portfolio.id or not portfolio.id.strip():
                click.echo(f"⚠️  Portfolio inválido ignorado")
                continue
                
            report = service.get_quoteholder_report_sync(portfolio, date, report_format)
            reports.append(report)
            
        except Exception as e:
            click.echo(f"❌ Erro no portfolio {portfolio.id}: {e}")
    
    return reports