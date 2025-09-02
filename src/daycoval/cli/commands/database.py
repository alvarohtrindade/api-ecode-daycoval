"""
Comandos CLI para operações de banco de dados.
"""
import click

from ...config.portfolios import get_portfolio_manager


@click.group()
def database_cli():
    """Comandos para operações de banco de dados."""
    pass


@database_cli.command('test')
@click.pass_context
def test_connection(ctx):
    """Testa conexão com banco Aurora/CADFUN."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        portfolio_manager = get_portfolio_manager()
        
        click.echo("🔗 Testando conexão com banco CADFUN...")
        
        success, message = portfolio_manager.test_database_connection()
        
        if success:
            click.echo(f"✅ {message}")
            
            if verbose:
                # Mostrar informações adicionais
                from ...config.settings import get_settings
                settings = get_settings()
                click.echo(f"   Host: {settings.database.host}")
                click.echo(f"   Database: {settings.database.database}")
                click.echo(f"   Port: {settings.database.port}")
        else:
            click.echo(f"❌ {message}")
            return False
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro ao testar conexão: {e}", err=True)
        return False


@database_cli.command('refresh')
@click.pass_context
def refresh_portfolios(ctx):
    """Atualiza cache de portfolios do banco."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        portfolio_manager = get_portfolio_manager()
        
        click.echo("🔄 Atualizando cache de portfolios...")
        
        success = portfolio_manager.refresh_cache()
        
        if success:
            stats = portfolio_manager.get_statistics()
            click.echo(f"✅ Cache atualizado com sucesso")
            click.echo(f"📊 Total de portfolios: {stats['total_portfolios']}")
            
            if verbose and stats['sample_portfolios']:
                click.echo("\n📋 Exemplos atualizados:")
                for pid, name in list(stats['sample_portfolios'].items())[:5]:
                    click.echo(f"   {pid}: {name}")
        else:
            click.echo("❌ Falha ao atualizar cache")
            return False
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro ao atualizar cache: {e}", err=True)
        return False


@database_cli.command('clear-cache')
def clear_cache():
    """Limpa cache de portfolios."""
    try:
        portfolio_manager = get_portfolio_manager()
        
        portfolio_manager.clear_cache()
        click.echo("✅ Cache limpo com sucesso")
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro ao limpar cache: {e}", err=True)
        return False


@database_cli.command('stats')
@click.pass_context
def show_statistics(ctx):
    """Mostra estatísticas do banco e cache."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        portfolio_manager = get_portfolio_manager()
        
        click.echo("📊 ESTATÍSTICAS DO BANCO DE DADOS")
        click.echo("=" * 50)
        
        # Testar conexão
        db_success, db_message = portfolio_manager.test_database_connection()
        click.echo(f"Conexão: {'✅' if db_success else '❌'} {db_message}")
        
        # Estatísticas dos portfolios
        try:
            stats = portfolio_manager.get_statistics()
            
            click.echo(f"Portfolios carregados: {stats['total_portfolios']}")
            click.echo(f"Cache ativo: {'✅' if stats['cache_loaded'] else '❌'}")
            click.echo(f"Arquivo fallback: {'✅' if stats['fallback_file_exists'] else '❌'}")
            
            if verbose:
                # Verificar cache em disco
                from pathlib import Path
                import json
                
                cache_file = Path("cache/fund_names_cache.json")
                if cache_file.exists():
                    try:
                        with open(cache_file, 'r') as f:
                            cache_data = json.load(f)
                        
                        metadata = cache_data.get('metadata', {})
                        click.echo(f"Cache em disco: ✅")
                        click.echo(f"   Fonte: {metadata.get('source', 'N/A')}")
                        click.echo(f"   Timestamp: {metadata.get('timestamp', 'N/A')}")
                        click.echo(f"   Total no cache: {metadata.get('total_count', 'N/A')}")
                    except Exception:
                        click.echo(f"Cache em disco: ❌ Erro ao ler")
                else:
                    click.echo(f"Cache em disco: ❌ Não existe")
                
                # Amostras de portfolios
                if stats['sample_portfolios']:
                    click.echo("\n📋 Amostras de portfolios:")
                    for pid, name in stats['sample_portfolios'].items():
                        click.echo(f"   {pid}: {name}")
        
        except Exception as e:
            click.echo(f"Erro ao obter estatísticas: {e}")
        
        click.echo("=" * 50)
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro ao mostrar estatísticas: {e}", err=True)
        return False


@database_cli.command('check-portfolio')
@click.argument('portfolio_id')
@click.pass_context
def check_portfolio(ctx, portfolio_id: str):
    """Verifica informações específicas de um portfolio."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        portfolio_manager = get_portfolio_manager()
        
        click.echo(f"🔍 Verificando portfolio {portfolio_id}...")
        
        # Verificar se existe
        exists = portfolio_manager.portfolio_exists(portfolio_id)
        
        if exists:
            portfolio = portfolio_manager.get_portfolio(portfolio_id)
            click.echo(f"✅ Portfolio encontrado:")
            click.echo(f"   ID: {portfolio.id}")
            click.echo(f"   Nome: {portfolio.name}")
            
            if verbose:
                # Informações adicionais se disponíveis
                click.echo(f"   Nome sanitizado: {portfolio.name}")
        else:
            click.echo(f"❌ Portfolio {portfolio_id} não encontrado")
            
            # Sugerir portfolios similares
            all_portfolios = portfolio_manager.get_all_portfolios()
            similar = [pid for pid in all_portfolios.keys() if portfolio_id in pid]
            
            if similar:
                click.echo("🔍 Portfolios similares encontrados:")
                for pid in similar[:5]:  # Mostrar até 5
                    click.echo(f"   {pid}: {all_portfolios[pid].name}")
            
            return False
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro ao verificar portfolio: {e}", err=True)
        return False


@database_cli.command('export')
@click.option('--output-file', default='portfolios_export.json', help='Arquivo de saída')
@click.option('--format', 'export_format', default='json', 
              type=click.Choice(['json', 'csv']), help='Formato de exportação')
@click.pass_context
def export_portfolios(ctx, output_file: str, export_format: str):
    """Exporta lista de portfolios."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        portfolio_manager = get_portfolio_manager()
        portfolios = portfolio_manager.get_all_portfolios()
        
        click.echo(f"📤 Exportando {len(portfolios)} portfolios...")
        
        from pathlib import Path
        output_path = Path(output_file)
        
        if export_format == 'json':
            import json
            
            export_data = {
                'portfolios': {p.id: p.name for p in portfolios.values()},
                'metadata': {
                    'export_timestamp': str(datetime.now()),
                    'total_count': len(portfolios),
                    'source': 'daycoval_cli'
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
        elif export_format == 'csv':
            import csv
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['portfolio_id', 'fund_name'])
                
                for portfolio in portfolios.values():
                    writer.writerow([portfolio.id, portfolio.name])
        
        click.echo(f"✅ Portfolios exportados para: {output_path}")
        click.echo(f"📊 Tamanho do arquivo: {output_path.stat().st_size} bytes")
        
        return True
        
    except Exception as e:
        click.echo(f"❌ Erro ao exportar: {e}", err=True)
        return False