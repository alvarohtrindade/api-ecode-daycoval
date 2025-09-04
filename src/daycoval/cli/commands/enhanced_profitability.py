#!/usr/bin/env python3
"""
Comandos CLI aprimorados para relatórios de rentabilidade com suporte a --n-days e --consolidar.

Novos comandos implementados:
- rentabilidade-sintetica: Endpoint 1048 com dias úteis e consolidação
- carteira: Endpoint 32 com dias úteis e consolidação

Author: Claude Code
Date: 2025-09-04
Version: 1.0
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click

from ...config.portfolios import get_portfolio_manager
from ...core.models import (
    ReportFormat, SyntheticProfitabilityRequest, DailyReportRequest,
    ReportType, DEFAULT_ALL_PORTFOLIOS_LABEL
)
from ...core.exceptions import DaycovalError
from ...utils.date_business import get_business_date_calculator


@click.group()
def enhanced_profitability_cli():
    """Comandos aprimorados para relatórios com suporte a dias úteis e consolidação."""
    pass


@enhanced_profitability_cli.command('rentabilidade-sintetica')
@click.option('--carteiraId', type=int, help='Código da Carteira (opcional - se omitido, todas as carteiras)')
@click.option('--format', required=True, type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']),
              help='Formato do relatório')
@click.option('--baseDiaria', is_flag=True, help='Base diária')
@click.option('--dataInicial', help='Data inicial (YYYY-MM-DD) - obrigatório com --baseDiaria')
@click.option('--dataFinal', help='Data final (YYYY-MM-DD) - obrigatório com --baseDiaria')
@click.option('--n-days', type=int, help='Usar data útil n dias atrás (substitui dataInicial/dataFinal)')
@click.option('--consolidar', is_flag=True, help='Consolidar todos os fundos em único arquivo')
@click.option('--formato-consolidado', type=click.Choice(['csv', 'pdf']), default='csv',
              help='Formato do arquivo consolidado (apenas com --consolidar)')
@click.option('--saida', default='./reports', help='Diretório de saída')
@click.option('--nomeRelatorioEsquerda', is_flag=True, default=True, help='Nome relatório à esquerda')
@click.option('--omiteLogotipo', is_flag=True, help='Omitir logotipo')
@click.option('--usaNomeCurtoCarteira', is_flag=True, help='Usar nome curto da carteira')
@click.option('--tipoRentabilidadeIndice', default=0, type=click.Choice(['0', '1', '2']),
              help='Tipo de rentabilidade (0=Cadastro, 1=Início a Início, 2=Fim a Fim)')
@click.option('--emitirPosicaoDeD0Abertura', is_flag=True, help='Emitir posição D0 abertura')
@click.pass_context
def rentabilidade_sintetica(ctx, carteiraid: int, format: str, basediaria: bool, datainicial: str,
                           datafinal: str, n_days: int, consolidar: bool, formato_consolidado: str,
                           saida: str, nomerelatorioesquerda: bool, omitelogotipo: bool,
                           usanomecurtocarteira: bool, tiporentabilidadeindice: str,
                           emitirposicaoded0abertura: bool):
    """Endpoint 1048 - Relatório de Rentabilidade Sintética com suporte a --n-days e --consolidar."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Resolução de data com --n-days
        start_date = None
        end_date = None
        
        if n_days is not None:
            click.echo(f"🗓️  Calculando data útil D-{n_days}...")
            calculator = get_business_date_calculator()
            
            if basediaria:
                # Para base diária, calcular período
                end_business_date = calculator.get_business_day(n_days=n_days)
                start_business_date = calculator.get_business_day(n_days=n_days+1)  # Um dia útil antes
                
                if not end_business_date or not start_business_date:
                    click.echo(f"❌ Erro ao calcular dias úteis para n_days={n_days}", err=True)
                    return False
                
                start_date = datetime.combine(start_business_date, datetime.min.time())
                end_date = datetime.combine(end_business_date, datetime.min.time())
                
                click.echo(f"   Período calculado: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
            else:
                # Para não base diária, apenas usar data de referência
                business_date = calculator.get_business_day(n_days=n_days)
                if not business_date:
                    click.echo(f"❌ Erro ao calcular dia útil para n_days={n_days}", err=True)
                    return False
                
                end_date = datetime.combine(business_date, datetime.min.time())
                click.echo(f"   Data de referência: {end_date.strftime('%Y-%m-%d')}")
        
        elif basediaria:
            # Usar datas fornecidas explicitamente
            if not datainicial or not datafinal:
                click.echo("❌ Para base diária sem --n-days, --dataInicial e --dataFinal são obrigatórios", err=True)
                return False
            
            start_date = datetime.strptime(datainicial, '%Y-%m-%d')
            end_date = datetime.strptime(datafinal, '%Y-%m-%d')
        else:
            # Não base diária - usar data atual
            end_date = datetime.now()
        
        # Configuração de portfolios
        portfolio_manager = get_portfolio_manager()
        
        if carteiraid:
            # Portfolio específico
            portfolio = portfolio_manager.get_portfolio(str(carteiraid))
            portfolios_list = [portfolio]
            click.echo(f"📊 Executando endpoint 1048 - Rentabilidade Sintética")
            click.echo(f"   Carteira: {portfolio.id} ({portfolio.name})")
        else:
            # Todas as carteiras
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolios_list = list(portfolio_dict.values())
            click.echo(f"📊 Executando endpoint 1048 - TODAS AS CARTEIRAS ({len(portfolios_list)})")
        
        click.echo(f"   Formato: {format}")
        if basediaria and start_date and end_date:
            click.echo(f"   Base diária: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        elif end_date:
            click.echo(f"   Data de referência: {end_date.strftime('%Y-%m-%d')}")
        
        if consolidar:
            click.echo(f"   Consolidação: ✅ ATIVA (formato: {formato_consolidado.upper()})")
        
        # Criar requisições
        from ...services.profitability_reports import create_profitability_service
        
        service = create_profitability_service()
        successful_reports = []
        failed_count = 0
        
        output_path = Path(saida)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Processar cada portfolio
        for i, portfolio in enumerate(portfolios_list, 1):
            click.echo(f"🔄 Processando {i}/{len(portfolios_list)}: {portfolio.id} ({portfolio.name})")
            
            try:
                request = SyntheticProfitabilityRequest(
                    portfolio=portfolio,
                    date=end_date or datetime.now(),
                    format=ReportFormat(format),
                    report_type=1048,
                    daily_base=basediaria,
                    start_date=start_date if basediaria else None,
                    end_date=end_date if basediaria else None,
                    left_report_name=nomerelatorioesquerda,
                    omit_logo=omitelogotipo,
                    use_short_portfolio_name=usanomecurtocarteira,
                    profitability_index_type=int(tiporentabilidadeindice),
                    emit_d0_opening_position=emitirposicaoded0abertura
                )
                
                # Obter relatório
                report = service.get_synthetic_profitability_report_sync(request)
                
                # Salvar arquivo individual (sempre)
                if service.save_report(report, output_path):
                    successful_reports.append(report)
                    click.echo(f"      ✅ Salvo: {report.filename} ({report.size_mb:.2f} MB)")
                else:
                    click.echo(f"      ❌ Erro ao salvar")
                    failed_count += 1
                    
            except Exception as e:
                click.echo(f"      ❌ Falha: {str(e)}")
                failed_count += 1
        
        # Consolidação de dados (se solicitada)
        consolidated_success = True
        if consolidar and successful_reports:
            click.echo(f"\n🔄 Consolidando {len(successful_reports)} relatórios...")
            
            try:
                # Nome do arquivo consolidado
                date_str = (end_date or datetime.now()).strftime('%Y%m%d')
                if n_days is not None:
                    consolidated_filename = f"CONSOLIDADO_SINTETICA_D{n_days}_{date_str}.{formato_consolidado}"
                else:
                    consolidated_filename = f"CONSOLIDADO_SINTETICA_{date_str}.{formato_consolidado}"
                
                consolidated_path = output_path / consolidated_filename
                
                # Implementação básica de consolidação CSV
                if formato_consolidado == 'csv' and format.startswith('CSV'):
                    consolidated_success = _consolidate_csv_files(
                        successful_reports, consolidated_path
                    )
                elif formato_consolidado == 'pdf':
                    # PDF consolidation seria implementada aqui
                    click.echo(f"      ⚠️  Consolidação PDF não implementada ainda")
                    consolidated_success = False
                else:
                    click.echo(f"      ⚠️  Formato não suportado para consolidação: {format}")
                    consolidated_success = False
                
                if consolidated_success:
                    click.echo(f"      ✅ Consolidado: {consolidated_filename}")
                else:
                    click.echo(f"      ❌ Erro na consolidação")
                    
            except Exception as e:
                click.echo(f"      ❌ Erro na consolidação: {str(e)}")
                consolidated_success = False
        
        # Estatísticas finais
        total_portfolios = len(portfolios_list)
        success_count = len(successful_reports)
        success_rate = (success_count / total_portfolios * 100) if total_portfolios > 0 else 0
        
        click.echo(f"\n🎯 RESULTADO FINAL:")
        click.echo(f"   Total portfolios: {total_portfolios}")
        click.echo(f"   ✅ Sucessos: {success_count}")
        click.echo(f"   ❌ Falhas: {failed_count}")
        click.echo(f"   📈 Taxa de sucesso: {success_rate:.1f}%")
        if consolidar:
            status_consolidado = "✅" if consolidated_success else "❌"
            click.echo(f"   📋 Consolidação: {status_consolidado}")
        click.echo(f"   📁 Diretório: {output_path}")
        
        return success_count > 0
        
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


@enhanced_profitability_cli.command('carteira')
@click.option('--portfolio', type=int, help='ID do portfolio')
@click.option('--data', help='Data específica (YYYY-MM-DD)')
@click.option('--n-days', type=int, help='Usar data útil n dias atrás')
@click.option('--consolidar', is_flag=True, help='Consolidar todos os fundos em único arquivo')
@click.option('--formato', type=click.Choice(['csv', 'pdf']), default='csv',
              help='Formato do arquivo')
@click.option('--saida', default='./reports', help='Diretório de saída')
@click.pass_context
def carteira(ctx, portfolio: int, data: str, n_days: int, consolidar: bool, formato: str, saida: str):
    """Endpoint 32 - Relatório de Carteira com suporte a --n-days e --consolidar."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Resolver data
        target_date = None
        
        if n_days is not None:
            click.echo(f"🗓️  Calculando data útil D-{n_days}...")
            calculator = get_business_date_calculator()
            
            business_date = calculator.get_business_day(n_days=n_days)
            if not business_date:
                click.echo(f"❌ Erro ao calcular dia útil para n_days={n_days}", err=True)
                return False
                
            target_date = datetime.combine(business_date, datetime.min.time())
            click.echo(f"   Data calculada: {target_date.strftime('%Y-%m-%d')}")
            
        elif data:
            target_date = datetime.strptime(data, '%Y-%m-%d')
        else:
            # Usar data atual ou último dia útil
            calculator = get_business_date_calculator()
            business_date = calculator.get_business_day(n_days=0)  # Hoje ou último dia útil
            if business_date:
                target_date = datetime.combine(business_date, datetime.min.time())
                click.echo(f"   Usando último dia útil: {target_date.strftime('%Y-%m-%d')}")
            else:
                target_date = datetime.now()
                click.echo(f"   Usando data atual: {target_date.strftime('%Y-%m-%d')}")
        
        # Configurar portfolios
        portfolio_manager = get_portfolio_manager()
        
        if portfolio:
            portfolio_obj = portfolio_manager.get_portfolio(str(portfolio))
            portfolios_list = [portfolio_obj]
            click.echo(f"📂 Relatório de Carteira - Portfolio {portfolio}")
        else:
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolios_list = list(portfolio_dict.values())
            click.echo(f"📂 Relatório de Carteira - TODOS OS PORTFOLIOS ({len(portfolios_list)})")
        
        click.echo(f"   Data: {target_date.strftime('%Y-%m-%d')}")
        click.echo(f"   Formato: {formato.upper()}")
        if consolidar:
            click.echo(f"   Consolidação: ✅ ATIVA")
        
        # Processar relatórios
        from ...services.daily_reports import create_daily_report_service
        
        service = create_daily_report_service()
        successful_reports = []
        failed_count = 0
        
        output_path = Path(saida)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for i, portfolio_obj in enumerate(portfolios_list, 1):
            click.echo(f"🔄 Processando {i}/{len(portfolios_list)}: {portfolio_obj.id} ({portfolio_obj.name})")
            
            try:
                request = DailyReportRequest(
                    portfolio=portfolio_obj,
                    date=target_date,
                    format=ReportFormat(formato.upper() if formato.upper() in ['PDF', 'CSVBR'] else 'PDF'),
                    report_type=ReportType.DAILY
                )
                
                report = service.get_report_sync(request)
                
                if service.save_report(report, output_path):
                    successful_reports.append(report)
                    click.echo(f"      ✅ Salvo: {report.filename}")
                else:
                    failed_count += 1
                    click.echo(f"      ❌ Erro ao salvar")
                    
            except Exception as e:
                failed_count += 1
                click.echo(f"      ❌ Falha: {str(e)}")
        
        # Consolidação (se solicitada)
        if consolidar and successful_reports:
            click.echo(f"\n🔄 Consolidando {len(successful_reports)} relatórios...")
            
            try:
                date_str = target_date.strftime('%Y%m%d')
                consolidated_filename = f"CONSOLIDADO_CARTEIRA_{date_str}.{formato}"
                consolidated_path = output_path / consolidated_filename
                
                if formato == 'csv':
                    success = _consolidate_csv_files(successful_reports, consolidated_path)
                else:
                    click.echo(f"      ⚠️  Consolidação PDF não implementada ainda")
                    success = False
                
                if success:
                    click.echo(f"      ✅ Consolidado: {consolidated_filename}")
                else:
                    click.echo(f"      ❌ Erro na consolidação")
                    
            except Exception as e:
                click.echo(f"      ❌ Erro na consolidação: {str(e)}")
        
        # Estatísticas finais
        total = len(portfolios_list)
        success_count = len(successful_reports)
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        click.echo(f"\n🎯 RESULTADO FINAL:")
        click.echo(f"   Total portfolios: {total}")
        click.echo(f"   ✅ Sucessos: {success_count}")
        click.echo(f"   ❌ Falhas: {failed_count}")
        click.echo(f"   📈 Taxa de sucesso: {success_rate:.1f}%")
        click.echo(f"   📁 Diretório: {output_path}")
        
        return success_count > 0
        
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def _consolidate_csv_files(reports: List, output_path: Path) -> bool:
    """
    Consolida múltiplos relatórios CSV em um único arquivo.
    
    Args:
        reports: Lista de objetos de relatório com conteúdo CSV
        output_path: Caminho para o arquivo consolidado
        
    Returns:
        bool: True se consolidação foi bem-sucedida
    """
    try:
        import csv
        import io
        from collections import OrderedDict
        
        all_rows = []
        headers = None
        
        for report in reports:
            if not hasattr(report, 'content') or not report.content:
                continue
                
            # Parse CSV content
            csv_content = report.content
            if isinstance(csv_content, bytes):
                csv_content = csv_content.decode('utf-8')
                
            reader = csv.DictReader(io.StringIO(csv_content))
            
            # Estabelecer headers na primeira iteração
            if headers is None:
                headers = reader.fieldnames
                
            # Adicionar coluna de fonte (nome do fundo)
            for row in reader:
                # Adicionar identificador do fundo baseado no filename
                fund_name = getattr(report, 'filename', 'Unknown').replace('.csv', '')
                row['FUNDO_ORIGEM'] = fund_name
                all_rows.append(row)
        
        if not all_rows:
            return False
            
        # Escrever arquivo consolidado
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Adicionar coluna FUNDO_ORIGEM no início
            if headers and 'FUNDO_ORIGEM' not in headers:
                headers = ['FUNDO_ORIGEM'] + list(headers)
                
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for row in all_rows:
                writer.writerow(row)
        
        return True
        
    except Exception as e:
        click.echo(f"Erro na consolidação CSV: {str(e)}")
        return False


# Comando de conveniência para testes
@enhanced_profitability_cli.command('test-n-days')
@click.option('--n-days', default=1, help='Número de dias úteis atrás para testar')
@click.pass_context
def test_n_days(ctx, n_days: int):
    """Testa o cálculo de dias úteis."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        click.echo(f"🧪 Testando cálculo de dias úteis (D-{n_days})")
        
        calculator = get_business_date_calculator()
        
        # Teste básico
        business_date = calculator.get_business_day(n_days=n_days)
        if business_date:
            click.echo(f"   ✅ Data útil D-{n_days}: {business_date}")
        else:
            click.echo(f"   ❌ Erro ao calcular D-{n_days}")
            return False
        
        # Teste com data específica
        test_date = '2025-01-01'  # Provável feriado
        specific_result = calculator.get_business_day(specific_date=test_date)
        if specific_result:
            click.echo(f"   ✅ Data útil para {test_date}: {specific_result}")
        else:
            click.echo(f"   ❌ Erro ao calcular data útil para {test_date}")
        
        # Teste de verificação
        is_business = calculator.is_business_day(business_date)
        click.echo(f"   ✅ {business_date} é dia útil: {is_business}")
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro no teste: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


@enhanced_profitability_cli.command('relatorio-rentabilidade')
@click.option('--carteira', type=int, help='Código da Carteira (opcional - se omitido, todas as carteiras)')
@click.option('--format', required=True, type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']),
              help='Formato do relatório')
@click.option('--data', help='Data de referência (YYYY-MM-DD)')
@click.option('--n-days', type=int, help='Usar data útil n dias atrás (substitui --data)')
@click.option('--consolidar', is_flag=True, help='Consolidar todos os fundos em único arquivo')
@click.option('--formato-consolidado', type=click.Choice(['csv', 'pdf']), default='csv',
              help='Formato do arquivo consolidado (apenas com --consolidar)')
@click.option('--saida', default='./reports', help='Diretório de saída')
@click.option('--nomeRelatorioEsquerda', is_flag=True, default=True, help='Nome relatório à esquerda')
@click.option('--omiteLogotipo', is_flag=True, help='Omitir logotipo')
@click.option('--usaNomeCurtoCarteira', is_flag=True, help='Usar nome curto da carteira')
@click.option('--usaNomeLongoTitulo', is_flag=True, help='Usar nome longo no título')
@click.option('--trataMovimentoAjusteComp', is_flag=True, default=True, help='Tratar movimento de ajuste compartilhado')
@click.option('--indiceCDI', default='CDI', help='Índice CDI (default: CDI)')
@click.pass_context
def relatorio_rentabilidade_enhanced(ctx, carteira: int, format: str, data: str, n_days: int,
                                    consolidar: bool, formato_consolidado: str, saida: str,
                                    nomerelatorioesquerda: bool, omitelogotipo: bool,
                                    usanomecurtocarteira: bool, usanomelongotitulo: bool,
                                    tratamovimentoajustecomp: bool, indicecdi: str):
    """Endpoint 1799 - Relatório de Rentabilidade com suporte a --n-days e --consolidar."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Resolução de data com --n-days
        report_date = None
        
        if n_days is not None:
            click.echo(f"🗓️  Calculando data útil D-{n_days}...")
            calculator = get_business_date_calculator()
            business_date = calculator.get_business_day(n_days=n_days)
            
            if not business_date:
                click.echo(f"❌ Erro ao calcular dia útil para n_days={n_days}", err=True)
                return False
                
            report_date = datetime.combine(business_date, datetime.min.time())
            click.echo(f"   Data de referência: {report_date.strftime('%Y-%m-%d')}")
            
        elif data:
            # Usar data fornecida explicitamente
            report_date = datetime.strptime(data, '%Y-%m-%d')
        else:
            # Usar data atual
            report_date = datetime.now()
        
        # Configuração de portfolios
        portfolio_manager = get_portfolio_manager()
        
        if carteira:
            # Portfolio específico
            portfolio = portfolio_manager.get_portfolio(str(carteira))
            portfolios_list = [portfolio]
            click.echo(f"📈 Executando endpoint 1799 - Relatório de Rentabilidade")
            click.echo(f"   Carteira: {portfolio.id} ({portfolio.name})")
        else:
            # Todas as carteiras
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolios_list = list(portfolio_dict.values())
            click.echo(f"📈 Executando endpoint 1799 - TODAS AS CARTEIRAS ({len(portfolios_list)})")
        
        click.echo(f"   Formato: {format}")
        if report_date:
            click.echo(f"   Data de referência: {report_date.strftime('%Y-%m-%d')}")
        click.echo(f"   Índice CDI: {indicecdi}")
        
        if consolidar:
            click.echo(f"   Consolidação: ✅ ATIVA (formato: {formato_consolidado.upper()})")
        
        # Criar requisições e processar
        from ...services.profitability_reports import create_profitability_service
        from ...core.models import ProfitabilityRequest
        
        service = create_profitability_service()
        successful_reports = []
        failed_count = 0
        
        output_path = Path(saida)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Processar cada portfolio
        for i, portfolio in enumerate(portfolios_list, 1):
            click.echo(f"🔄 Processando {i}/{len(portfolios_list)}: {portfolio.id} ({portfolio.name})")
            
            try:
                request = ProfitabilityRequest(
                    portfolio=portfolio,
                    date=report_date or datetime.now(),
                    format=ReportFormat(format),
                    report_type=1799,
                    report_date=report_date,
                    left_report_name=nomerelatorioesquerda,
                    omit_logo=omitelogotipo,
                    use_short_portfolio_name=usanomecurtocarteira,
                    use_long_title_name=usanomelongotitulo,
                    handle_shared_adjustment_movement=tratamovimentoajustecomp,
                    cdi_index=indicecdi
                )
                
                report = service.get_profitability_report_sync(request)
                
                if not consolidar:
                    # Salvar arquivo individual
                    success = service.save_report(report, output_path)
                    if success:
                        successful_reports.append(report)
                        click.echo(f"   ✅ Salvo: {report.filename}")
                    else:
                        failed_count += 1
                        click.echo(f"   ❌ Erro ao salvar")
                else:
                    # Apenas coletar para consolidação
                    successful_reports.append(report)
                    click.echo(f"   ✅ Dados coletados para consolidação")
                    
            except Exception as e:
                failed_count += 1
                click.echo(f"   ❌ Erro: {str(e)[:100]}...")
                if verbose:
                    click.echo(f"      Erro completo: {e}")
        
        # Consolidar se solicitado
        if consolidar and successful_reports:
            click.echo(f"\n🔄 Consolidando {len(successful_reports)} relatórios...")
            
            from ...services.data_consolidation import create_consolidation_service
            consolidation_service = create_consolidation_service()
            
            if formato_consolidado == 'csv':
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                consolidated_filename = f"relatório_rentabilidade_consolidado_{timestamp}.csv"
                consolidated_path = output_path / consolidated_filename
                
                success = consolidation_service.consolidate_csv_reports(
                    successful_reports, 
                    consolidated_path,
                    endpoint_type="1799",
                    include_metadata=True
                )
                
                if success:
                    click.echo(f"   ✅ Arquivo consolidado: {consolidated_filename}")
                else:
                    click.echo(f"   ❌ Erro na consolidação")
        
        # Estatísticas finais
        total = len(portfolios_list)
        success_count = len(successful_reports)
        success_rate = (success_count / total) * 100 if total > 0 else 0
        
        click.echo(f"\n✅ Processamento concluído!")
        click.echo(f"   Total: {total}")
        click.echo(f"   Sucessos: {success_count}")
        click.echo(f"   Falhas: {failed_count}")
        click.echo(f"   Taxa de sucesso: {success_rate:.1f}%")
        
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


@enhanced_profitability_cli.command('extrato-conta-corrente')
@click.option('--carteira', type=int, help='Código da Carteira (opcional - se omitido, todas as carteiras)')
@click.option('--format', required=True, type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']),
              help='Formato do relatório')
@click.option('--dataInicial', help='Data inicial (YYYY-MM-DD)')
@click.option('--dataFinal', help='Data final (YYYY-MM-DD) - opcional')
@click.option('--n-days', type=int, help='Usar período D-(n+1) a D-n (substitui --dataInicial/dataFinal)')
@click.option('--consolidar', is_flag=True, help='Consolidar todos os fundos em único arquivo')
@click.option('--formato-consolidado', type=click.Choice(['csv', 'pdf']), default='csv',
              help='Formato do arquivo consolidado (apenas com --consolidar)')
@click.option('--saida', default='./reports', help='Diretório de saída')
@click.option('--agencia', required=True, help='Código da agência')
@click.option('--conta', required=True, help='Número da conta')
@click.option('--dias', default=0, type=int, help='Número de dias (default: 0)')
@click.option('--nomeRelatorioEsquerda', is_flag=True, default=True, help='Nome relatório à esquerda')
@click.option('--omiteLogotipo', is_flag=True, help='Omitir logotipo')
@click.option('--usaNomeCurtoCarteira', is_flag=True, help='Usar nome curto da carteira')
@click.pass_context
def extrato_conta_corrente_enhanced(ctx, carteira: int, format: str, datainicial: str, datafinal: str,
                                   n_days: int, consolidar: bool, formato_consolidado: str, saida: str,
                                   agencia: str, conta: str, dias: int, nomerelatorioesquerda: bool,
                                   omitelogotipo: bool, usanomecurtocarteira: bool):
    """Endpoint 1988 - Extrato Conta Corrente com suporte a --n-days e --consolidar."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Resolução de datas com --n-days
        start_date = None
        end_date = None
        
        if n_days is not None:
            click.echo(f"🗓️  Calculando período útil D-{n_days+1} a D-{n_days}...")
            calculator = get_business_date_calculator()
            
            # Para extrato, usar período de n+1 dias úteis até n dias úteis
            end_business_date = calculator.get_business_day(n_days=n_days)
            start_business_date = calculator.get_business_day(n_days=n_days+1)
            
            if not end_business_date or not start_business_date:
                click.echo(f"❌ Erro ao calcular dias úteis para n_days={n_days}", err=True)
                return False
            
            start_date = datetime.combine(start_business_date, datetime.min.time())
            end_date = datetime.combine(end_business_date, datetime.min.time())
            
            click.echo(f"   Período calculado: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
            
        else:
            # Usar datas fornecidas explicitamente
            if not datainicial:
                click.echo("❌ --dataInicial é obrigatório quando --n-days não é fornecido", err=True)
                return False
            
            start_date = datetime.strptime(datainicial, '%Y-%m-%d')
            if datafinal and datafinal.strip():
                end_date = datetime.strptime(datafinal, '%Y-%m-%d')
        
        # Configuração de portfolios
        portfolio_manager = get_portfolio_manager()
        
        if carteira:
            # Portfolio específico
            portfolio = portfolio_manager.get_portfolio(str(carteira))
            portfolios_list = [portfolio]
            click.echo(f"🏦 Executando endpoint 1988 - Extrato Conta Corrente")
            click.echo(f"   Carteira: {portfolio.id} ({portfolio.name})")
        else:
            # Todas as carteiras
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolios_list = list(portfolio_dict.values())
            click.echo(f"🏦 Executando endpoint 1988 - TODAS AS CARTEIRAS ({len(portfolios_list)})")
        
        click.echo(f"   Formato: {format}")
        click.echo(f"   Período: {start_date.strftime('%Y-%m-%d')}" + (f" a {end_date.strftime('%Y-%m-%d')}" if end_date else ""))
        click.echo(f"   Agência: {agencia}, Conta: {conta}")
        
        if consolidar:
            click.echo(f"   Consolidação: ✅ ATIVA (formato: {formato_consolidado.upper()})")
        
        # Criar requisições e processar
        from ...services.profitability_reports import create_profitability_service
        from ...core.models import BankStatementRequest
        
        service = create_profitability_service()
        successful_reports = []
        failed_count = 0
        
        output_path = Path(saida)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Processar cada portfolio
        for i, portfolio in enumerate(portfolios_list, 1):
            click.echo(f"🔄 Processando {i}/{len(portfolios_list)}: {portfolio.id} ({portfolio.name})")
            
            try:
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
                
                report = service.get_bank_statement_report_sync(request)
                
                if not consolidar:
                    # Salvar arquivo individual
                    success = service.save_report(report, output_path)
                    if success:
                        successful_reports.append(report)
                        click.echo(f"   ✅ Salvo: {report.filename}")
                    else:
                        failed_count += 1
                        click.echo(f"   ❌ Erro ao salvar")
                else:
                    # Apenas coletar para consolidação
                    successful_reports.append(report)
                    click.echo(f"   ✅ Dados coletados para consolidação")
                    
            except Exception as e:
                failed_count += 1
                click.echo(f"   ❌ Erro: {str(e)[:100]}...")
                if verbose:
                    click.echo(f"      Erro completo: {e}")
        
        # Consolidar se solicitado
        if consolidar and successful_reports:
            click.echo(f"\n🔄 Consolidando {len(successful_reports)} relatórios...")
            
            from ...services.data_consolidation import create_consolidation_service
            consolidation_service = create_consolidation_service()
            
            if formato_consolidado == 'csv':
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                consolidated_filename = f"extrato_conta_corrente_consolidado_{timestamp}.csv"
                consolidated_path = output_path / consolidated_filename
                
                success = consolidation_service.consolidate_csv_reports(
                    successful_reports, 
                    consolidated_path,
                    endpoint_type="1988",
                    include_metadata=True
                )
                
                if success:
                    click.echo(f"   ✅ Arquivo consolidado: {consolidated_filename}")
                else:
                    click.echo(f"   ❌ Erro na consolidação")
        
        # Estatísticas finais
        total = len(portfolios_list)
        success_count = len(successful_reports)
        success_rate = (success_count / total) * 100 if total > 0 else 0
        
        click.echo(f"\n✅ Processamento concluído!")
        click.echo(f"   Total: {total}")
        click.echo(f"   Sucessos: {success_count}")
        click.echo(f"   Falhas: {failed_count}")
        click.echo(f"   Taxa de sucesso: {success_rate:.1f}%")
        
        return True
        
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return False@enhanced_profitability_cli.command('posicao-cotistas')
@click.option('--carteira', type=int, help='Código da Carteira (opcional - se omitido, todas as carteiras)')
@click.option('--format', required=True, type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS']),
              help='Formato do relatório')
@click.option('--data', help='Data de referência (YYYY-MM-DD)')
@click.option('--n-days', type=int, help='Usar data útil n dias atrás (substitui --data)')
@click.option('--consolidar', is_flag=True, help='Consolidar todos os fundos em único arquivo')
@click.option('--formato-consolidado', type=click.Choice(['csv', 'pdf']), default='csv',
              help='Formato do arquivo consolidado (apenas com --consolidar)')
@click.option('--saida', default='./reports', help='Diretório de saída')
@click.option('--nomeRelatorioEsquerda', is_flag=True, default=True, help='Nome relatório à esquerda')
@click.option('--omiteLogotipo', is_flag=True, help='Omitir logotipo')
@click.option('--usaNomeCurtoCarteira', is_flag=True, help='Usar nome curto da carteira')
@click.option('--clienteInicial', default=1, type=int, help='Cliente inicial (default: 1)')
@click.option('--clienteFinal', default=999999999999, type=int, help='Cliente final (default: 999999999999)')
@click.option('--assessorInicial', default=1, type=int, help='Assessor inicial (default: 1)')
@click.option('--assessorFinal', default=99999, type=int, help='Assessor final (default: 99999)')
@click.option('--classeInvestidor', default=-1, type=int, help='Classe investidor (default: -1)')
@click.option('--apresentaCodigoIF', is_flag=True, default=True, help='Apresenta código IF')
@click.pass_context
def posicao_cotistas_enhanced(ctx, carteira: int, format: str, data: str, n_days: int,
                             consolidar: bool, formato_consolidado: str, saida: str,
                             nomerelatorioesquerda: bool, omitelogotipo: bool,
                             usanomecurtocarteira: bool, clienteinicial: int,
                             clientefinal: int, assessorinicial: int, assessorfinal: int,
                             classeinvestidor: int, apresentacodigoif: bool):
    """Endpoint 45 - Posição de Cotistas com suporte a --n-days e --consolidar."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Resolução de data com --n-days
        report_date = None
        
        if n_days is not None:
            click.echo(f"🗓️  Calculando data útil D-{n_days}...")
            calculator = get_business_date_calculator()
            business_date = calculator.get_business_day(n_days=n_days)
            
            if not business_date:
                click.echo(f"❌ Erro ao calcular dia útil para n_days={n_days}", err=True)
                return False
                
            report_date = datetime.combine(business_date, datetime.min.time())
            click.echo(f"   Data de referência: {report_date.strftime('%Y-%m-%d')}")
            
        elif data:
            # Usar data fornecida explicitamente
            report_date = datetime.strptime(data, '%Y-%m-%d')
        else:
            # Usar data atual
            report_date = datetime.now()
        
        # Configuração de portfolios
        portfolio_manager = get_portfolio_manager()
        
        if carteira:
            # Portfolio específico
            portfolio = portfolio_manager.get_portfolio(str(carteira))
            portfolios_list = [portfolio]
            click.echo(f"👥 Executando endpoint 45 - Posição de Cotistas")
            click.echo(f"   Carteira: {portfolio.id} ({portfolio.name})")
        else:
            # Todas as carteiras
            portfolio_dict = portfolio_manager.get_all_portfolios()
            portfolios_list = list(portfolio_dict.values())
            click.echo(f"👥 Executando endpoint 45 - TODAS AS CARTEIRAS ({len(portfolios_list)})")
        
        click.echo(f"   Formato: {format}")
        if report_date:
            click.echo(f"   Data de referência: {report_date.strftime('%Y-%m-%d')}")
        
        if consolidar:
            click.echo(f"   Consolidação: ✅ ATIVA (formato: {formato_consolidado.upper()})")
        
        # Criar serviço de cotistas e processar
        from ...core.client import APIClient
        from ...config.settings import get_settings
        from ...core.models import ReportResponse
        
        settings = get_settings()
        client = APIClient(settings.api)
        
        successful_reports = []
        failed_count = 0
        
        output_path = Path(saida)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Processar cada portfolio
        for i, portfolio in enumerate(portfolios_list, 1):
            click.echo(f"🔄 Processando {i}/{len(portfolios_list)}: {portfolio.id} ({portfolio.name})")
            
            try:
                # Parâmetros para endpoint 45
                params = {
                    "carteira": int(portfolio.id),
                    "format": format,
                    "data": report_date.strftime('%Y-%m-%d'),
                    "nomeRelatorioEsquerda": nomerelatorioesquerda,
                    "omiteLogotipo": omitelogotipo,
                    "usaNomeCurtoCarteira": usanomecurtocarteira,
                    "clienteInicial": clienteinicial,
                    "clienteFinal": clientefinal,
                    "assessorInicial": assessorinicial,
                    "assessorFinal": assessorfinal,
                    "assessor2Inicial": 0,
                    "assessor2Final": 0,
                    "classeInvestidor": classeinvestidor,
                    "apresentaCodigoIF": apresentacodigoif,
                    "geraArquivoFormatoExcelHeaders": False,
                    "mensagem": ""
                }
                
                # Fazer requisição
                response = client.post_sync("/report/reports/45", params)
                
                # Processar resposta
                if format == 'PDF':
                    content = response.content
                    content_type = 'application/pdf'
                    ext = 'pdf'
                else:
                    content = response.text
                    content_type = 'text/plain'
                    ext = format.lower()
                
                filename = f"POSICAO_COTISTAS_{portfolio.name}_{report_date.strftime('%Y%m%d')}.{ext}"
                filename = filename.replace('/', '_').replace(' ', '_')
                
                report = ReportResponse(
                    content=content,
                    content_type=content_type,
                    filename=filename,
                    portfolio=portfolio,
                    date=report_date,
                    format=ReportFormat(format),
                    size_bytes=len(content) if isinstance(content, str) else len(content)
                )
                
                if not consolidar:
                    # Salvar arquivo individual
                    file_path = output_path / report.filename
                    success = report.save_to_file(file_path)
                    if success:
                        successful_reports.append(report)
                        click.echo(f"   ✅ Salvo: {report.filename}")
                    else:
                        failed_count += 1
                        click.echo(f"   ❌ Erro ao salvar")
                else:
                    # Apenas coletar para consolidação
                    successful_reports.append(report)
                    click.echo(f"   ✅ Dados coletados para consolidação")
                    
            except Exception as e:
                failed_count += 1
                click.echo(f"   ❌ Erro: {str(e)[:100]}...")
                if verbose:
                    click.echo(f"      Erro completo: {e}")
        
        # Consolidar se solicitado
        if consolidar and successful_reports:
            click.echo(f"\n🔄 Consolidando {len(successful_reports)} relatórios...")
            
            from ...services.data_consolidation import create_consolidation_service
            consolidation_service = create_consolidation_service()
            
            if formato_consolidado == 'csv':
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                consolidated_filename = f"posicao_cotistas_consolidado_{timestamp}.csv"
                consolidated_path = output_path / consolidated_filename
                
                success = consolidation_service.consolidate_csv_reports(
                    successful_reports, 
                    consolidated_path,
                    endpoint_type="45",
                    include_metadata=True
                )
                
                if success:
                    click.echo(f"   ✅ Arquivo consolidado: {consolidated_filename}")
                else:
                    click.echo(f"   ❌ Erro na consolidação")
        
        # Estatísticas finais
        total = len(portfolios_list)
        success_count = len(successful_reports)
        success_rate = (success_count / total) * 100 if total > 0 else 0
        
        click.echo(f"\n✅ Processamento concluído!")
        click.echo(f"   Total: {total}")
        click.echo(f"   Sucessos: {success_count}")
        click.echo(f"   Falhas: {failed_count}")
        click.echo(f"   Taxa de sucesso: {success_rate:.1f}%")
        
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