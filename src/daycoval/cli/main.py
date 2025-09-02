"""
CLI principal para a API Daycoval - versão limpa e organizada.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

import click

from ..config.settings import get_settings
from ..config.portfolios import get_portfolio_manager
from ..core.exceptions import DaycovalError
from .commands.daily import daily_cli
from .commands.quoteholder import quoteholder_cli
from .commands.profitability import profitability_cli
from .commands.batch_enhanced import batch_enhanced_cli
# from .commands.database import database_cli  # Comentado temporariamente


def setup_logging(verbose: bool = False) -> None:
    """Configura logging da aplicação."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduzir verbosidade de libs externas
    if not verbose:
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.option('--config-file', help='Arquivo de configuração personalizado')
@click.pass_context
def cli(ctx, verbose: bool, config_file: str):
    """
    CLI para API Daycoval - Relatórios automatizados.
    
    Sistema limpo e modular para geração de relatórios diários e de cotistas.
    """
    # Configurar contexto
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file
    
    # Configurar logging
    setup_logging(verbose)
    
    # Validar configurações básicas
    try:
        settings = get_settings()
        if verbose:
            click.echo(f"✅ Configurações carregadas: API={settings.api.base_url}")
    except Exception as e:
        click.echo(f"❌ Erro ao carregar configurações: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def info(ctx):
    """Mostra informações do sistema."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        settings = get_settings()
        portfolio_manager = get_portfolio_manager()
        
        click.echo("🚀 SISTEMA DAYCOVAL - INFORMAÇÕES")
        click.echo("=" * 50)
        
        # Configurações básicas
        click.echo(f"API Base URL: {settings.api.base_url}")
        click.echo(f"Rate Limit: {settings.api.rate_limit_calls} calls/{settings.api.rate_limit_period}s")
        click.echo(f"Timeout: {settings.api.timeout}s")
        
        # Database
        db_success, db_message = portfolio_manager.test_database_connection()
        db_status = "✅" if db_success else "❌"
        click.echo(f"Database: {db_status} {db_message}")
        
        # Portfolios
        try:
            stats = portfolio_manager.get_statistics()
            click.echo(f"Portfolios: {stats['total_portfolios']} carregados")
            
            if verbose and stats['sample_portfolios']:
                click.echo("\n📋 Exemplos de portfolios:")
                for pid, name in list(stats['sample_portfolios'].items())[:3]:
                    click.echo(f"  {pid}: {name}")
        except Exception as e:
            click.echo(f"Portfolios: ❌ Erro ao carregar ({e})")
        
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ Erro: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--portfolio-id', help='ID específico do portfolio')
@click.option('--limit', default=10, help='Limite de portfolios a mostrar')
def list_portfolios(portfolio_id: str, limit: int):
    """Lista portfolios disponíveis."""
    try:
        portfolio_manager = get_portfolio_manager()
        
        if portfolio_id:
            # Mostrar portfolio específico
            try:
                portfolio = portfolio_manager.get_portfolio(portfolio_id)
                click.echo(f"📂 Portfolio {portfolio.id}:")
                click.echo(f"   Nome: {portfolio.name}")
            except Exception as e:
                click.echo(f"❌ Portfolio {portfolio_id} não encontrado: {e}", err=True)
                sys.exit(1)
        else:
            # Listar todos os portfolios
            portfolios = portfolio_manager.get_all_portfolios()
            total = len(portfolios)
            
            click.echo(f"📋 PORTFOLIOS DISPONÍVEIS ({total} total)")
            click.echo("-" * 60)
            
            for i, (pid, portfolio) in enumerate(portfolios.items()):
                if i >= limit:
                    remaining = total - limit
                    click.echo(f"... e mais {remaining} portfolios")
                    break
                
                click.echo(f"{pid:>10} | {portfolio.name}")
            
            click.echo("-" * 60)
            
    except Exception as e:
        click.echo(f"❌ Erro: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('date', type=click.DateTime(['%Y-%m-%d']))
@click.option('--format', 'report_format', default='PDF', 
              type=click.Choice(['PDF', 'CSVBR', 'CSVUS', 'TXTBR', 'TXTUS', 'JSON']))
@click.option('--portfolio', help='ID do portfolio')
@click.option('--output-dir', default='./reports', help='Diretório de saída')
@click.pass_context
def quick_report(ctx, date: datetime, report_format: str, portfolio: str, output_dir: str):
    """Gera um relatório rapidamente (para testes)."""
    from ..services.daily_reports import create_daily_report_service
    from ..core.models import ReportFormat, Portfolio
    
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Configurar portfolio
        if not portfolio:
            # Usar primeiro portfolio disponível
            portfolio_manager = get_portfolio_manager()
            portfolios = portfolio_manager.get_all_portfolios()
            if not portfolios:
                click.echo("❌ Nenhum portfolio disponível", err=True)
                sys.exit(1)
            portfolio_obj = list(portfolios.values())[0]
            click.echo(f"ℹ️  Usando portfolio: {portfolio_obj.id} ({portfolio_obj.name})")
        else:
            portfolio_manager = get_portfolio_manager()
            portfolio_obj = portfolio_manager.get_portfolio(portfolio)
        
        # Configurar serviço
        service = create_daily_report_service()
        
        # Importar ReportType que estava faltando
        from ..core.models import ReportType
        
        # Criar requisição
        from ..core.models import DailyReportRequest
        
        request = DailyReportRequest(
            portfolio=portfolio_obj,
            date=date,
            format=ReportFormat(report_format),
            report_type=ReportType.DAILY
        )
        
        click.echo(f"🚀 Gerando relatório {report_format} para {portfolio_obj.name}...")
        
        # Obter relatório
        report = service.get_report_sync(request)
        
        # Salvar arquivo
        output_path = Path(output_dir)
        success = service.save_report(report, output_path)
        
        if success:
            click.echo(f"✅ Relatório salvo: {output_path / report.filename}")
            click.echo(f"📊 Tamanho: {report.size_mb:.2f} MB")
        else:
            click.echo("❌ Erro ao salvar relatório", err=True)
            sys.exit(1)
            
    except DaycovalError as e:
        click.echo(f"❌ Erro Daycoval: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Erro inesperado: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command('check-config')
@click.pass_context  
def check_config(ctx):
    """Verifica configurações e credenciais."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        import os
        from pathlib import Path
        
        click.echo("🔍 VERIFICAÇÃO DE CONFIGURAÇÕES")
        click.echo("=" * 50)
        
        # Verificar arquivo .env
        env_file = Path(".env")
        if env_file.exists():
            click.echo(f"✅ Arquivo .env encontrado: {env_file.absolute()}")
        else:
            click.echo(f"❌ Arquivo .env NÃO encontrado em: {Path('.').absolute()}")
            return
        
        # Verificar variáveis de ambiente
        click.echo("\n📋 Variáveis de ambiente:")
        
        api_key = os.getenv('APIKEY_GESTOR')
        prod_url = os.getenv('PROD_URL')
        
        if api_key:
            # Mascarar API key para segurança
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            click.echo(f"   APIKEY_GESTOR: {masked_key}")
        else:
            click.echo(f"   ❌ APIKEY_GESTOR: NÃO DEFINIDA")
        
        if prod_url:
            click.echo(f"   PROD_URL: {prod_url}")
        else:
            click.echo(f"   ❌ PROD_URL: NÃO DEFINIDA")
        
        # Verificar outras variáveis
        other_vars = [
            'AURORA_HOST', 'AURORA_USER', 'AURORA_PASSWORD', 
            'API_TIMEOUT', 'LOG_LEVEL'
        ]
        
        for var in other_vars:
            value = os.getenv(var)
            if value:
                if 'PASSWORD' in var:
                    click.echo(f"   {var}: ***")
                else:
                    click.echo(f"   {var}: {value}")
            else:
                click.echo(f"   {var}: não definida")
        
        # Testar carregamento via settings
        click.echo("\n⚙️  Teste de carregamento:")
        try:
            settings = get_settings()
            click.echo(f"   ✅ Settings carregadas")
            click.echo(f"   API URL: {settings.api.base_url}")
            click.echo(f"   API Key: {settings.api.api_key[:8]}...{settings.api.api_key[-4:]}")
            click.echo(f"   Timeout: {settings.api.timeout}s")
        except Exception as e:
            click.echo(f"   ❌ Erro ao carregar settings: {e}")
        
        # Testar requisição simples
        click.echo("\n🌐 Teste de conectividade:")
        try:
            from ..core.client import APIClient
            client = APIClient(settings.api)
            
            # Fazer uma requisição teste (pode falhar, mas deve dar erro específico)
            test_params = {"format": "JSON", "date": "2025-08-19"}
            response = client.post_sync("/report/reports/32", test_params)
            click.echo(f"   ✅ Conectividade OK (Status: {response.status_code})")
            
        except Exception as e:
            error_str = str(e)
            if "Credenciais inválidas" in error_str:
                click.echo(f"   ❌ PROBLEMA: API Key inválida ou expirada")
            elif "401" in error_str:
                click.echo(f"   ❌ PROBLEMA: Não autorizado - verifique API Key")
            elif "timeout" in error_str.lower():
                click.echo(f"   ⏰ PROBLEMA: Timeout de conexão")
            else:
                click.echo(f"   ⚠️  Erro: {error_str}")
        
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ Erro na verificação: {e}")


@cli.command('db-test')
def db_test():
    """Testa conexão com banco Aurora."""
    try:
        portfolio_manager = get_portfolio_manager()
        success, message = portfolio_manager.test_database_connection()
        
        if success:
            click.echo(f"✅ {message}")
        else:
            click.echo(f"❌ {message}")
        
    except Exception as e:
        click.echo(f"❌ Erro ao testar conexão: {e}", err=True)


@cli.command('db-refresh')  
def db_refresh():
    """Atualiza cache de portfolios."""
    try:
        portfolio_manager = get_portfolio_manager()
        success = portfolio_manager.refresh_cache()
        
        if success:
            stats = portfolio_manager.get_statistics()
            click.echo(f"✅ Cache atualizado: {stats['total_portfolios']} portfolios")
        else:
            click.echo("❌ Falha ao atualizar cache")
            
    except Exception as e:
        click.echo(f"❌ Erro: {e}", err=True)


# Adicionar subcomandos
cli.add_command(daily_cli, name='daily')
cli.add_command(quoteholder_cli, name='quoteholder') 
cli.add_command(profitability_cli, name='profitability')
cli.add_command(batch_enhanced_cli, name='batch-enhanced')
# cli.add_command(database_cli, name='db')  # Comentado temporariamente

@cli.command('test-profitability')
@click.argument('portfolio_id')
@click.option('--endpoint', default='1799', type=click.Choice(['1048', '1799']))
@click.pass_context
def test_profitability(ctx, portfolio_id: str, endpoint: str):
    """Testa rapidamente os novos endpoints de rentabilidade."""
    from ..services.profitability_reports import create_profitability_service
    from ..core.models import ReportFormat, SyntheticProfitabilityRequest, ProfitabilityRequest
    
    verbose = ctx.obj.get('verbose', False)
    
    try:
        portfolio_manager = get_portfolio_manager()
        portfolio = portfolio_manager.get_portfolio(portfolio_id)
        
        click.echo(f"🧪 Teste rápido - Endpoint {endpoint}")
        click.echo(f"   Portfolio: {portfolio.id} ({portfolio.name})")
        
        service = create_profitability_service()
        
        if endpoint == "1048":
            request = SyntheticProfitabilityRequest(
                portfolio=portfolio,
                date=datetime.now(),
                format=ReportFormat.JSON,  # JSON para debug
                report_type=1048,
                daily_base=False,
                profitability_index_type=0,
                emit_d0_opening_position=False
            )
            
            report = service.get_synthetic_profitability_report_sync(request)
            click.echo(f"✅ Relatório sintético obtido: {report.size_mb:.2f} MB")
            
        else:
            request = ProfitabilityRequest(
                portfolio=portfolio,
                date=datetime.now(),
                format=ReportFormat.JSON,  # JSON para debug
                report_type=1799,
                cdi_index="CDI"
            )
            
            report = service.get_profitability_report_sync(request)
            click.echo(f"✅ Relatório de rentabilidade obtido: {report.size_mb:.2f} MB")
        
        # Mostrar preview do conteúdo se for JSON
        if isinstance(report.content, str) and len(report.content) > 0:
            preview = report.content[:300]
            click.echo(f"📄 Preview: {preview}...")
        
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


def main():
    """Ponto de entrada principal."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n⚠️  Operação cancelada pelo usuário")
        sys.exit(130)
    except Exception as e:
        click.echo(f"❌ Erro crítico: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()