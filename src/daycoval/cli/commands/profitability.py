#!/usr/bin/env python3
"""
Comandos CLI para relatórios de rentabilidade (endpoints 1048, 1799 e 1988).
"""
from datetime import datetime
from pathlib import Path

import click

from ...config.portfolios import get_portfolio_manager
from ...services.profitability_reports import create_profitability_service
from ...core.models import (
    ReportFormat, SyntheticProfitabilityRequest, ProfitabilityRequest, 
    BankStatementRequest, DEFAULT_ALL_PORTFOLIOS_LABEL
)
from ...core.exceptions import DaycovalError


@click.group()
def profitability_cli():
    """Comandos para relatórios de rentabilidade."""
    pass


# Comando direto para endpoint 1988 - Extrato Conta Corrente
@profitability_cli.command('extrato-conta-corrente')
@click.option('--carteira', required=True, type=int, help='Código da Carteira')
@click.option('--format', required=True, type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']),
              help='Formato do relatório')
@click.option('--dataInicial', required=True, help='Data inicial (YYYY-MM-DD)')
@click.option('--dataFinal', help='Data final (YYYY-MM-DD) - opcional')
@click.option('--agencia', required=True, help='Código da agência')
@click.option('--conta', required=True, help='Número da conta')
@click.option('--dias', default=0, type=int, help='Número de dias (default: 0)')
@click.option('--nomeRelatorioEsquerda', is_flag=True, default=True,
              help='Nome relatório à esquerda')
@click.option('--omiteLogotipo', is_flag=True, help='Omitir logotipo')
@click.option('--usaNomeCurtoCarteira', is_flag=True, help='Usar nome curto da carteira')
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.pass_context
def extrato_conta_corrente(ctx, carteira: int, format: str, datainicial: str, datafinal: str,
                          agencia: str, conta: str, dias: int, nomerelatorioesquerda: bool,
                          omitelogotipo: bool, usanomecurtocarteira: bool, output_dir: str):
    """Endpoint POST /extrato-conta-corrente (ID: 1988)."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Obter portfolio
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(str(carteira))
        
        # Converter datas
        start_date = datetime.strptime(datainicial, '%Y-%m-%d')
        end_date = None
        if datafinal and datafinal.strip():
            end_date = datetime.strptime(datafinal, '%Y-%m-%d')
        
        # Criar requisição
        request = BankStatementRequest(
            portfolio=portfolio,
            date=start_date,
            format=ReportFormat(format),
            report_type=1988,
            start_date=start_date,
            end_date=end_date,
            agency=agencia,
            account=conta,
            days=dias,
            left_report_name=nomerelatorioesquerda,
            omit_logo=omitelogotipo,
            use_short_portfolio_name=usanomecurtocarteira
        )
        
        click.echo(f"🏦 Executando endpoint 1988 - Extrato Conta Corrente")
        click.echo(f"   Carteira: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Formato: {format}")
        click.echo(f"   Período: {datainicial}" + (f" a {datafinal}" if datafinal else ""))
        click.echo(f"   Agência: {agencia}, Conta: {conta}")
        
        # Configurar serviço e executar
        service = create_profitability_service()
        report = service.get_bank_statement_report_sync(request)
        
        # Salvar arquivo
        output_path = Path(output_dir)
        success = service.save_report(report, output_path)
        
        if success:
            click.echo(f"✅ Extrato salvo: {output_path / report.filename}")
            click.echo(f"📊 Tamanho: {report.size_mb:.2f} MB")
            return True
        else:
            click.echo("❌ Erro ao salvar extrato", err=True)
            return False
            
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


# Comando direto para endpoint 1799 - Relatório de Rentabilidade
@profitability_cli.command('relatorio-rentabilidade')
@click.option('--carteira', required=True, type=int, help='Código da Carteira')
@click.option('--format', required=True, type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']),
              help='Formato do relatório')
@click.option('--data', help='Data de referência (YYYY-MM-DD) - opcional')
@click.option('--nomeRelatorioEsquerda', is_flag=True, default=True,
              help='Nome relatório à esquerda')
@click.option('--omiteLogotipo', is_flag=True, help='Omitir logotipo')
@click.option('--usaNomeCurtoCarteira', is_flag=True, help='Usar nome curto da carteira')
@click.option('--usaNomeLongoTitulo', is_flag=True, help='Usar nome longo no título')
@click.option('--trataMovimentoAjusteComp', is_flag=True, default=True,
              help='Tratar movimento de ajuste compartilhado')
@click.option('--indiceCDI', default='CDI', help='Índice CDI (default: CDI)')
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.pass_context
def relatorio_rentabilidade(ctx, carteira: int, format: str, data: str, nomerelatorioesquerda: bool,
                           omitelogotipo: bool, usanomecurtocarteira: bool, usanomolongotitulo: bool,
                           tratamovimentoajustecomp: bool, indicecdi: str, output_dir: str):
    """Endpoint POST /relatorio-rentabilidade (ID: 1799)."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Obter portfolio
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(str(carteira))
        
        # Converter data se fornecida
        report_date = None
        if data and data.strip():
            report_date = datetime.strptime(data, '%Y-%m-%d')
        
        # Criar requisição
        request = ProfitabilityRequest(
            portfolio=portfolio,
            date=report_date or datetime.now(),
            format=ReportFormat(format),
            report_type=1799,
            report_date=report_date,
            left_report_name=nomerelatorioesquerda,
            omit_logo=omitelogotipo,
            use_short_portfolio_name=usanomecurtocarteira,
            use_long_title_name=usanomolongotitulo,
            handle_shared_adjustment_movement=tratamovimentoajustecomp,
            cdi_index=indicecdi
        )
        
        click.echo(f"📈 Executando endpoint 1799 - Relatório de Rentabilidade")
        click.echo(f"   Carteira: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Formato: {format}")
        if report_date:
            click.echo(f"   Data: {report_date.strftime('%Y-%m-%d')}")
        click.echo(f"   Índice CDI: {indicecdi}")
        
        # Configurar serviço e executar
        service = create_profitability_service()
        report = service.get_profitability_report_sync(request)
        
        # Salvar arquivo
        output_path = Path(output_dir)
        success = service.save_report(report, output_path)
        
        if success:
            click.echo(f"✅ Relatório salvo: {output_path / report.filename}")
            click.echo(f"📊 Tamanho: {report.size_mb:.2f} MB")
            return True
        else:
            click.echo("❌ Erro ao salvar relatório", err=True)
            return False
            
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


# Comando teste para todos os endpoints
@profitability_cli.command('test-endpoint')
@click.argument('portfolio_id')
@click.option('--endpoint', default='1799', type=click.Choice(['1048', '1799', '1988']),
              help='Endpoint a testar')
@click.pass_context
def test_endpoint(ctx, portfolio_id: str, endpoint: str):
    """Testa rapidamente os endpoints de rentabilidade."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        from ...core.client import APIClient
        from ...config.settings import get_settings
        
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"🧪 Testando endpoint {endpoint} para:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        
        # Configurar cliente
        settings = get_settings()
        client = APIClient(settings.api)
        
        # Parâmetros para cada endpoint
        if endpoint == "1048":
            params = {
                "carteiraId": int(portfolio.id),
                "format": "JSON",
                "baseDiaria": False,
                "nomeRelatorioEsquerda": True,
                "omiteLogotipo": False,
                "usaNomeCurtoCarteira": False,
                "tipoRentabilidadeIndice": 0,
                "emitirPosicaoDeD0Abertura": False
            }
        elif endpoint == "1799":
            params = {
                "carteira": int(portfolio.id),
                "format": "JSON",
                "nomeRelatorioEsquerda": True,
                "omiteLogotipo": False,
                "usaNomeCurtoCarteira": False,
                "usaNomeLongoTitulo": False,
                "trataMovimentoAjusteComp": True,
                "indiceCDI": "CDI"
            }
        else:  # 1988
            params = {
                "carteira": int(portfolio.id),
                "format": "JSON",
                "dataInicial": "2024-05-01",
                "dataFinal": "",
                "agencia": "00019",
                "conta": "0000000123",
                "dias": 0,
                "nomeRelatorioEsquerda": True,
                "omiteLogotipo": False,
                "usaNomeCurtoCarteira": False
            }
        
        click.echo(f"🔄 Fazendo requisição para endpoint {endpoint}...")
        response = client.post_sync(f"/report/reports/{endpoint}", params)
        
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
        if verbose:
            import traceback
            traceback.print_exc()
        return False