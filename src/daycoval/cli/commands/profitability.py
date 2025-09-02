"""
Comandos CLI para relatórios de rentabilidade (endpoints 1048 e 1799).
"""
from datetime import datetime
from pathlib import Path

import click

from ...config.portfolios import get_portfolio_manager
from ...services.profitability_reports import create_profitability_service
from ...core.models import ReportFormat, SyntheticProfitabilityRequest, ProfitabilityRequest, DEFAULT_ALL_PORTFOLIOS_LABEL
from ...core.exceptions import DaycovalError


@click.group()
def profitability_cli():
    """Comandos para relatórios de rentabilidade."""
    pass


@profitability_cli.group('synthetic-profitability')
def synthetic_profitability():
    """Comandos para relatórios de rentabilidade sintética (endpoint 1048)."""
    pass

@synthetic_profitability.command('single')
@click.argument('portfolio_id')
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--daily-base', is_flag=True, help='Usar base diária (requer datas)')
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), help='Data inicial (apenas com --daily-base)')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), help='Data final (apenas com --daily-base)')
@click.option('--profitability-type', default=0, type=click.Choice(['0', '1', '2']),
              help='Tipo rentabilidade (0=Cadastro, 1=Início a Início, 2=Fim a Fim)')
@click.option('--emit-d0', is_flag=True, help='Emitir posição D0 de abertura')
@click.pass_context
def synthetic_single(ctx, portfolio_id: str, report_format: str, output_dir: str,
                    daily_base: bool, start_date: datetime, end_date: datetime,
                    profitability_type: str, emit_d0: bool):
    """Gera relatório de rentabilidade sintética para um portfolio específico."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Validações
        if daily_base and (not start_date or not end_date):
            click.echo("❌ Para base diária, --start-date e --end-date são obrigatórios", err=True)
            return False
        
        if not daily_base and (start_date or end_date):
            click.echo("⚠️  Datas fornecidas sem --daily-base serão ignoradas")
        
        # Obter portfolio
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"📊 Gerando relatório de rentabilidade sintética:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Formato: {report_format}")
        click.echo(f"   Base diária: {'Sim' if daily_base else 'Não'}")
        if daily_base:
            click.echo(f"   Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        click.echo(f"   Tipo rentabilidade: {profitability_type}")
        
        # Criar requisição
        request = SyntheticProfitabilityRequest(
            portfolio=portfolio,
            date=end_date if daily_base and end_date else datetime.now(),
            format=ReportFormat(report_format),
            report_type=1048,
            daily_base=daily_base,
            start_date=start_date if daily_base else None,
            end_date=end_date if daily_base else None,
            profitability_index_type=int(profitability_type),
            emit_d0_opening_position=emit_d0
        )
        
        # Configurar serviço
        service = create_profitability_service()
        
        output_path = Path(output_dir)
        
        # Obter relatório individual
        report = service.get_synthetic_profitability_report_sync(request)
        
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

@synthetic_profitability.command('all')
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--daily-base', is_flag=True, help='Usar base diária (requer datas)')
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), help='Data inicial (apenas com --daily-base)')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), help='Data final (apenas com --daily-base)')
@click.option('--profitability-type', default=0, type=click.Choice(['0', '1', '2']),
              help='Tipo rentabilidade (0=Cadastro, 1=Início a Início, 2=Fim a Fim)')
@click.option('--emit-d0', is_flag=True, help='Emitir posição D0 de abertura')
@click.pass_context
def synthetic_all(ctx, report_format: str, output_dir: str,
                 daily_base: bool, start_date: datetime, end_date: datetime,
                 profitability_type: str, emit_d0: bool):
    """Gera relatórios de rentabilidade sintética para todos os portfolios (individual + consolidado)."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Validações
        if daily_base and (not start_date or not end_date):
            click.echo("❌ Para base diária, --start-date e --end-date são obrigatórios", err=True)
            return False
        
        if not daily_base and (start_date or end_date):
            click.echo("⚠️  Datas fornecidas sem --daily-base serão ignoradas")
        
        click.echo(f"📊 Gerando relatório de rentabilidade sintética:")
        click.echo(f"   Portfolio: {DEFAULT_ALL_PORTFOLIOS_LABEL}")
        click.echo(f"   Formato: {report_format}")
        click.echo(f"   Base diária: {'Sim' if daily_base else 'Não'}")
        if daily_base:
            click.echo(f"   Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        click.echo(f"   Tipo rentabilidade: {profitability_type}")
        
        # Criar requisição base (sem portfolio)
        base_request = SyntheticProfitabilityRequest(
            portfolio=None,  # Todas as carteiras
            date=end_date if daily_base and end_date else datetime.now(),
            format=ReportFormat(report_format),
            report_type=1048,
            daily_base=daily_base,
            start_date=start_date if daily_base else None,
            end_date=end_date if daily_base else None,
            profitability_index_type=int(profitability_type),
            emit_d0_opening_position=emit_d0
        )
        
        # Configurar serviço
        service = create_profitability_service()
        output_path = Path(output_dir)
        
        # Gerar relatórios individuais + consolidado
        return _process_all_portfolios_synthetic(
            service, base_request, output_path, report_format, daily_base, 
            start_date, end_date, profitability_type, emit_d0
        )
        
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False

def _process_all_portfolios_synthetic(
    service, base_request, output_path: Path, report_format: str, daily_base: bool,
    start_date: datetime, end_date: datetime, profitability_type: str, emit_d0: bool
) -> bool:
    """
    Processa relatórios sintéticos para todos os portfolios.
    Gera arquivos individuais + consolidado.
    """
    try:
        # Obter todos os portfolios
        portfolio_manager = get_portfolio_manager()
        all_portfolios = portfolio_manager.get_all_portfolios()
        portfolio_list = list(all_portfolios.values())
        
        click.echo(f"📊 Processando TODOS os {len(portfolio_list)} portfolios:")
        click.echo(f"   - Arquivos individuais por fundo")
        click.echo(f"   - Arquivo consolidado final")
        click.echo(f"   Formato: {report_format}")
        if daily_base:
            click.echo(f"   Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        
        individual_reports = []
        successful = 0
        failed = 0
        
        # 1. Gerar relatórios individuais
        click.echo("\\n🔄 Gerando relatórios individuais...")
        for i, portfolio in enumerate(portfolio_list, 1):
            try:
                click.echo(f"   [{i}/{len(portfolio_list)}] {portfolio.id} ({portfolio.name})")
                
                # Criar requisição individual
                individual_request = SyntheticProfitabilityRequest(
                    portfolio=portfolio,
                    date=end_date if daily_base and end_date else datetime.now(),
                    format=ReportFormat(report_format),
                    report_type=1048,
                    daily_base=daily_base,
                    start_date=start_date if daily_base else None,
                    end_date=end_date if daily_base else None,
                    profitability_index_type=int(profitability_type),
                    emit_d0_opening_position=emit_d0
                )
                
                # Obter e salvar relatório individual
                report = service.get_synthetic_profitability_report_sync(individual_request)
                
                # Salvar arquivo individual
                if service.save_report(report, output_path):
                    individual_reports.append(report)
                    successful += 1
                    click.echo(f"      ✅ Salvo: {report.filename}")
                else:
                    failed += 1
                    click.echo(f"      ❌ Erro ao salvar")
                    
            except Exception as e:
                failed += 1
                click.echo(f"      ❌ Erro: {e}")
        
        # 2. Gerar consolidado (apenas para CSV)
        if report_format.startswith('CSV') and individual_reports:
            click.echo("\\n🔄 Gerando arquivo consolidado...")
            
            consolidation_type = "SINTETICA" if daily_base else "SINTETICA"
            date_str = (end_date or datetime.now()).strftime('%Y%m%d')
            consolidated_filename = f"CONSOLIDADO_{consolidation_type}_TODOS_FUNDOS_{date_str}.csv"
            consolidated_path = output_path / consolidated_filename
            
            if consolidate_csv_reports(individual_reports, consolidated_path, "1048"):
                click.echo(f"      ✅ Consolidado: {consolidated_filename}")
            else:
                click.echo(f"      ❌ Erro no consolidado")
        
        # 3. Estatísticas finais
        total = len(portfolio_list)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        click.echo(f"\\n🎯 RESULTADO FINAL:")
        click.echo(f"   Total portfolios: {total}")
        click.echo(f"   ✅ Sucessos: {successful}")
        click.echo(f"   ❌ Falhas: {failed}")
        click.echo(f"   📈 Taxa de sucesso: {success_rate:.1f}%")
        click.echo(f"   📁 Diretório: {output_path}")
        
        return successful > 0
        
    except Exception as e:
        click.echo(f"❌ Erro no processamento em lote: {e}")
        return False


def consolidate_csv_reports(
    reports: list, 
    output_path: Path,
    endpoint: str
) -> bool:
    """
    Consolida múltiplos CSVs em um único arquivo.
    
    Args:
        reports: Lista de relatórios em formato CSV
        output_path: Caminho do arquivo consolidado
        endpoint: Endpoint usado (1048 ou 1799)
    
    Returns:
        bool: Sucesso da operação
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        consolidated_data = []
        
        for report in reports:
            if not report.format.is_csv:
                continue
                
            # Parse do CSV
            csv_lines = report.content.split('\n')
            if len(csv_lines) < 2:  # Pelo menos header + 1 linha
                continue
                
            # Adicionar coluna identificadora do fundo
            fund_id = report.portfolio.id
            fund_name = report.portfolio.name
            
            # Processar cada linha (exceto header)
            for i, line in enumerate(csv_lines):
                if not line.strip():
                    continue
                    
                if i == 0:  # Header
                    if not consolidated_data:  # Primeira vez
                        # Adicionar colunas de identificação
                        header = f"FUND_ID;FUND_NAME;{line.strip()}"
                        consolidated_data.append(header)
                else:  # Dados
                    data_line = f"{fund_id};{fund_name};{line.strip()}"
                    consolidated_data.append(data_line)
        
        # Salvar arquivo consolidado
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(consolidated_data))
        
        logger.info(f"✅ Arquivo consolidado salvo: {output_path}")
        logger.info(f"📊 Total de linhas: {len(consolidated_data)}")
        
        return True
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Erro na consolidação: {e}")
        return False

@profitability_cli.command('standard')
@click.argument('portfolio_id')
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--date', type=click.DateTime(['%Y-%m-%d']), help='Data do relatório (base diária)')
@click.option('--cdi-index', default='CDI', help='Índice CDI para benchmark')
@click.pass_context
def standard(ctx, portfolio_id: str, report_format: str, output_dir: str,
             date: datetime, cdi_index: str):
    """Gera relatório de rentabilidade padrão (endpoint 1799)."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Obter portfolio
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"📈 Gerando relatório de rentabilidade:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        click.echo(f"   Formato: {report_format}")
        if date:
            click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        else:
            click.echo(f"   Data: Atual da carteira")
        click.echo(f"   Índice CDI: {cdi_index}")
        
        # Criar requisição
        request = ProfitabilityRequest(
            portfolio=portfolio,
            date=date or datetime.now(),
            format=ReportFormat(report_format),
            report_type=1799,
            report_date=date,
            cdi_index=cdi_index
        )
        
        # Configurar serviço
        service = create_profitability_service()
        
        # Obter relatório
        report = service.get_profitability_report_sync(request)
        
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


@profitability_cli.command('test')
@click.argument('portfolio_id')
@click.option('--endpoint', default='1799', type=click.Choice(['1048', '1799']),
              help='Endpoint a testar')
def test_endpoint(portfolio_id: str, endpoint: str):
    """Testa se endpoints 1048/1799 funcionam para um portfolio."""
    try:
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"🧪 Testando endpoint {endpoint} para:")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        
        # Testar requisição
        from ...core.client import APIClient
        from ...config.settings import get_settings
        
        settings = get_settings()
        client = APIClient(settings.api)
        
        if endpoint == "1048":
            # Teste sintético
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
        else:
            # Teste padrão
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
        return False

@profitability_cli.command('batch-consolidated')
@click.option('--format', 'report_format', default='CSVBR',
              type=click.Choice(['CSVBR', 'CSVUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--output-file', help='Nome do arquivo consolidado (opcional)')
@click.option('--portfolios', help='IDs específicos (separados por vírgula)')
@click.option('--all-portfolios', is_flag=True, help='Todos os portfolios')
@click.option('--endpoint', default='1799', type=click.Choice(['1048', '1799']))
@click.option('--date', type=click.DateTime(['%Y-%m-%d']), help='Data do relatório')
@click.pass_context
def batch_consolidated(ctx, report_format: str, output_dir: str, output_file: str,
                      portfolios: str, all_portfolios: bool, endpoint: str, date: datetime):
    """Gera arquivo consolidado com todos os fundos em CSV único."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Determinar portfolios
        portfolio_manager = get_portfolio_manager()
        
        if all_portfolios:
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolio_list = list(portfolio_dict.values())
            click.echo(f"📊 Processando TODOS os {len(portfolio_list)} portfolios (consolidado)")
        elif portfolios:
            portfolio_ids = [p.strip() for p in portfolios.split(',')]
            portfolio_list = []
            for pid in portfolio_ids:
                portfolio_list.append(portfolio_manager.get_portfolio(pid))
            click.echo(f"📊 Processando {len(portfolio_list)} portfolios específicos")
        else:
            click.echo("❌ Especifique --all-portfolios ou --portfolios", err=True)
            return False
        
        click.echo(f"   Formato: {report_format}")
        click.echo(f"   Endpoint: {endpoint}")
        if date:
            click.echo(f"   Data: {date.strftime('%Y-%m-%d')}")
        
        # Processar relatórios
        service = create_profitability_service()
        reports = []
        
        for i, portfolio in enumerate(portfolio_list, 1):
            try:
                click.echo(f"🔄 Processando {i}/{len(portfolio_list)}: {portfolio.id}")
                
                if endpoint == "1048":
                    request = SyntheticProfitabilityRequest(
                        portfolio=portfolio,
                        date=date or datetime.now(),
                        format=ReportFormat(report_format),
                        report_type=1048,
                        daily_base=False,
                        profitability_index_type=0
                    )
                    report = service.get_synthetic_profitability_report_sync(request)
                else:
                    request = ProfitabilityRequest(
                        portfolio=portfolio,
                        date=date or datetime.now(),
                        format=ReportFormat(report_format),
                        report_type=1799,
                        report_date=date,
                        cdi_index="CDI"
                    )
                    report = service.get_profitability_report_sync(request)
                
                reports.append(report)
                
            except Exception as e:
                click.echo(f"❌ Erro no portfolio {portfolio.id}: {e}")
        
        # Consolidar relatórios
        if not reports:
            click.echo("❌ Nenhum relatório foi gerado", err=True)
            return False
        
        # Definir nome do arquivo consolidado
        if not output_file:
            consolidation_type = "SINTETICA" if endpoint == "1048" else "RENTABILIDADE"
            date_str = (date or datetime.now()).strftime('%Y%m%d')
            output_file = f"CONSOLIDADO_{consolidation_type}_TODOS_FUNDOS_{date_str}.csv"
        
        output_path = Path(output_dir) / output_file
        
        # Executar consolidação
        success = consolidate_csv_reports(reports, output_path, endpoint)
        
        if success:
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            click.echo(f"✅ Arquivo consolidado salvo: {output_path}")
            click.echo(f"📊 Tamanho: {file_size:.2f} MB")
            click.echo(f"📈 Fundos incluídos: {len(reports)}")
        else:
            click.echo("❌ Erro na consolidação", err=True)
            return False
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False
    
@profitability_cli.command('batch-synthetic')
@click.option('--format', 'report_format', default='PDF',
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']))
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.option('--portfolios', help='IDs específicos (separados por vírgula)')
@click.option('--all-portfolios', is_flag=True, help='Todos os portfolios')
@click.option('--daily-base', is_flag=True, help='Usar base diária')
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), help='Data inicial')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), help='Data final')
@click.option('--profitability-type', default=0, type=click.Choice(['0', '1', '2']))
@click.pass_context
def batch_synthetic(ctx, report_format: str, output_dir: str, portfolios: str,
                   all_portfolios: bool, daily_base: bool, start_date: datetime,
                   end_date: datetime, profitability_type: str):
    """Gera relatórios sintéticos em lote."""
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
            click.echo(f"📊 Processando TODOS os {len(portfolio_list)} portfolios (sintético)")
        elif portfolios:
            portfolio_ids = [p.strip() for p in portfolios.split(',')]
            portfolio_list = []
            for pid in portfolio_ids:
                portfolio_list.append(portfolio_manager.get_portfolio(pid))
            click.echo(f"📊 Processando {len(portfolio_list)} portfolios específicos")
        else:
            click.echo("❌ Especifique --all-portfolios ou --portfolios", err=True)
            return False
        
        click.echo(f"   Formato: {report_format}")
        if daily_base:
            click.echo(f"   Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        
        # Processar relatórios
        reports = _process_synthetic_batch_sync(
            portfolio_list, report_format, daily_base, start_date, end_date, profitability_type
        )
        
        # Salvar relatórios
        service = create_profitability_service()
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
        
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def _process_synthetic_batch_sync(portfolios, report_format, daily_base, start_date, end_date, profitability_type):
    """Processa lote de relatórios sintéticos de forma síncrona."""
    from ...core.exceptions import ReportProcessingError, EmptyReportError, TimeoutError
    
    service = create_profitability_service()
    reports = []
    processing_errors = []
    timeout_errors = []
    empty_errors = []
    
    for i, portfolio in enumerate(portfolios, 1):
        try:
            click.echo(f"🔄 Processando {i}/{len(portfolios)}: {portfolio.id}")
            
            request = SyntheticProfitabilityRequest(
                portfolio=portfolio,
                date=end_date if daily_base and end_date else datetime.now(),
                format=ReportFormat(report_format),
                report_type=1048,
                daily_base=daily_base,
                start_date=start_date if daily_base else None,
                end_date=end_date if daily_base else None,
                profitability_index_type=int(profitability_type),
                emit_d0_opening_position=False
            )
            
            report = service.get_synthetic_profitability_report_sync(request)
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
    _show_batch_statistics(processing_errors, timeout_errors, empty_errors)
    
    return reports


def _show_batch_statistics(processing_errors, timeout_errors, empty_errors):
    """Mostra estatísticas detalhadas do processamento em lote."""
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


# Comando direto para endpoint 1048 seguindo especificação exata
@profitability_cli.command('relatorio-rentabilidade-sintetica')
@click.option('--carteiraId', type=int, help='Código da Carteira (opcional)')
@click.option('--format', required=True, type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']),
              help='Formato do relatório')
@click.option('--baseDiaria', is_flag=True, help='Habilitar base diária')
@click.option('--dataInicial', help='Data inicial (YYYY-MM-DD) - obrigatório se baseDiaria=true')
@click.option('--dataFinal', help='Data final (YYYY-MM-DD) - obrigatório se baseDiaria=true') 
@click.option('--nomeRelatorioEsquerda', is_flag=True, default=True, help='Nome relatório à esquerda')
@click.option('--omiteLogotipo', is_flag=True, help='Omitir logotipo')
@click.option('--usaNomeCurtoCarteira', is_flag=True, help='Usar nome curto da carteira')
@click.option('--tipoRentabilidadeIndice', default=0, type=click.Choice([0, 1, 2]),
              help='Tipo rentabilidade: 0|1|2')
@click.option('--emitirPosicaoDeD0Abertura', is_flag=True, help='Emitir posição D0 de abertura')
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.pass_context
def relatorio_rentabilidade_sintetica(ctx, carteiraid: int, format: str, basediaria: bool,
                                     datainicial: str, datafinal: str, nomerelatorioesquerda: bool,
                                     omitelogotipo: bool, usanomecurtocarteira: bool,
                                     tiporentabilidadeindice: int, emitirposicaoded0abertura: bool,
                                     output_dir: str):
    """Endpoint POST /relatorio-rentabilidade-sintetica (ID: 1048)."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Validações condicionais da especificação
        if basediaria and (not datainicial or not datafinal):
            click.echo("❌ Para baseDiaria=true, dataInicial e dataFinal são obrigatórios", err=True)
            return False
        
        # Obter portfolio se especificado
        portfolio = None
        if carteiraid:
            portfolio_manager = get_portfolio_manager()
            portfolio = portfolio_manager.get_portfolio(str(carteiraid))
        
        # Criar requisição usando a especificação exata
        from datetime import datetime
        
        request_date = datetime.now()
        start_date = None
        end_date = None
        
        if basediaria and datainicial and datafinal:
            start_date = datetime.strptime(datainicial, '%Y-%m-%d')
            end_date = datetime.strptime(datafinal, '%Y-%m-%d')
            request_date = end_date
        
        # Criar requisição 
        request = SyntheticProfitabilityRequest(
            portfolio=portfolio,
            date=request_date,
            format=ReportFormat(format),
            report_type=1048,
            daily_base=basediaria,
            start_date=start_date,
            end_date=end_date,
            profitability_index_type=tiporentabilidadeindice,
            emit_d0_opening_position=emitirposicaoded0abertura,
            left_report_name=nomerelatorioesquerda,
            omit_logo=omitelogotipo,
            use_short_portfolio_name=usanomecurtocarteira
        )
        
        click.echo(f"🚀 Executando endpoint 1048 - Relatório Rentabilidade Sintética")
        if portfolio:
            click.echo(f"   Carteira: {portfolio.id} ({portfolio.name})")
        else:
            click.echo(f"   Carteira: {DEFAULT_ALL_PORTFOLIOS_LABEL} (carteiraId omitido)")
        click.echo(f"   Formato: {format}")
        
        # Configurar serviço e executar
        service = create_profitability_service()
        report = service.get_synthetic_profitability_report_sync(request)
        
        # Salvar arquivo
        from pathlib import Path
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