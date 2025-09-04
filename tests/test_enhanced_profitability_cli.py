#!/usr/bin/env python3
"""
Testes para os comandos CLI aprimorados com --n-days e --consolidar.

Testa:
- Comandos CLI rentabilidade-sintetica e carteira
- Integração com date_business para --n-days
- Funcionalidade de consolidação
- Validação de parâmetros

Author: Claude Code
Date: 2025-09-04
Version: 1.0
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from click.testing import CliRunner

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from daycoval.cli.commands.enhanced_profitability import (
    enhanced_profitability_cli,
    rentabilidade_sintetica,
    carteira,
    test_n_days
)


class TestEnhancedProfitabilityCLI:
    """Testes para comandos CLI aprimorados."""
    
    @pytest.fixture
    def runner(self):
        """Runner do Click para testes."""
        return CliRunner()
    
    @pytest.fixture
    def mock_portfolio_manager(self):
        """Mock do portfolio manager."""
        manager = Mock()
        
        # Portfolio mock
        portfolio = Mock()
        portfolio.id = "12345"
        portfolio.name = "FUNDO TESTE FIDC"
        
        manager.get_portfolio.return_value = portfolio
        manager.get_all_portfolios.return_value = {"12345": portfolio}
        
        return manager
    
    @pytest.fixture
    def mock_service(self):
        """Mock do serviço de relatórios."""
        service = Mock()
        
        # Report mock
        report = Mock()
        report.filename = "FUNDO_TESTE_FIDC_20250904.csv"
        report.content = "FUNDO,DATA,RENTABILIDADE\nTESTE,2025-09-04,0.15"
        report.size_mb = 1.5
        
        service.get_synthetic_profitability_report_sync.return_value = report
        service.save_report.return_value = True
        
        return service
    
    @pytest.fixture
    def mock_calculator(self):
        """Mock do calculador de dias úteis."""
        calc = Mock()
        calc.get_business_day.return_value = date(2025, 9, 4)
        calc.is_business_day.return_value = True
        return calc
    
    def test_rentabilidade_sintetica_basic(self, runner, mock_portfolio_manager, mock_service):
        """Testa comando básico de rentabilidade sintética."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_profitability_service') as mock_cs, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            mock_pm.return_value = mock_portfolio_manager
            mock_cs.return_value = mock_service
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--carteiraId', '12345',
                '--format', 'CSVBR',
                '--saida', tmpdir
            ])
            
            assert result.exit_code == 0
            assert "Executando endpoint 1048" in result.output
            assert "Carteira: 12345" in result.output
            assert "Formato: CSVBR" in result.output
    
    def test_rentabilidade_sintetica_with_n_days(self, runner, mock_portfolio_manager, mock_service, mock_calculator):
        """Testa comando com --n-days."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_profitability_service') as mock_cs, \
             patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            mock_pm.return_value = mock_portfolio_manager
            mock_cs.return_value = mock_service
            mock_calc.return_value = mock_calculator
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--carteiraId', '12345',
                '--format', 'CSVBR',
                '--n-days', '2',
                '--saida', tmpdir
            ])
            
            assert result.exit_code == 0
            assert "Calculando data útil D-2" in result.output
            assert "Data de referência: 2025-09-04" in result.output
            mock_calculator.get_business_day.assert_called_with(n_days=2)
    
    def test_rentabilidade_sintetica_with_consolidar(self, runner, mock_portfolio_manager, mock_service):
        """Testa comando com --consolidar."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_profitability_service') as mock_cs, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            mock_pm.return_value = mock_portfolio_manager
            mock_cs.return_value = mock_service
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--format', 'CSVBR',  # Sem carteiraId = todas as carteiras
                '--consolidar',
                '--formato-consolidado', 'csv',
                '--saida', tmpdir
            ])
            
            assert result.exit_code == 0
            assert "TODAS AS CARTEIRAS" in result.output
            assert "Consolidação: ✅ ATIVA" in result.output
    
    def test_rentabilidade_sintetica_all_portfolios(self, runner, mock_portfolio_manager, mock_service):
        """Testa comando para todas as carteiras."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_profitability_service') as mock_cs, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            # Múltiplos portfolios
            portfolio1 = Mock()
            portfolio1.id = "12345"
            portfolio1.name = "FUNDO A FIDC"
            
            portfolio2 = Mock()
            portfolio2.id = "67890"  
            portfolio2.name = "FUNDO B FIDC"
            
            mock_portfolio_manager.get_all_portfolios.return_value = {
                "12345": portfolio1,
                "67890": portfolio2
            }
            
            mock_pm.return_value = mock_portfolio_manager
            mock_cs.return_value = mock_service
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--format', 'CSVBR',  # Sem carteiraId
                '--saida', tmpdir
            ])
            
            assert result.exit_code == 0
            assert "TODAS AS CARTEIRAS (2)" in result.output
            assert "Processando 1/2: 12345" in result.output
            assert "Processando 2/2: 67890" in result.output
    
    def test_carteira_command(self, runner, mock_portfolio_manager):
        """Testa comando de carteira."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_daily_report_service') as mock_ds, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            # Mock do serviço de relatórios diários
            service = Mock()
            report = Mock()
            report.filename = "CARTEIRA_12345_20250904.csv"
            service.get_report_sync.return_value = report
            service.save_report.return_value = True
            
            mock_pm.return_value = mock_portfolio_manager
            mock_ds.return_value = service
            
            result = runner.invoke(carteira, [
                '--portfolio', '12345',
                '--data', '2025-09-04',
                '--formato', 'csv',
                '--saida', tmpdir
            ])
            
            assert result.exit_code == 0
            assert "Relatório de Carteira - Portfolio 12345" in result.output
            assert "Data: 2025-09-04" in result.output
            assert "Formato: CSV" in result.output
    
    def test_carteira_with_n_days(self, runner, mock_portfolio_manager, mock_calculator):
        """Testa comando carteira com --n-days."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_daily_report_service') as mock_ds, \
             patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            service = Mock()
            report = Mock()
            report.filename = "CARTEIRA_12345_20250904.csv"
            service.get_report_sync.return_value = report
            service.save_report.return_value = True
            
            mock_pm.return_value = mock_portfolio_manager
            mock_ds.return_value = service
            mock_calc.return_value = mock_calculator
            
            result = runner.invoke(carteira, [
                '--portfolio', '12345',
                '--n-days', '1',
                '--formato', 'csv',
                '--saida', tmpdir
            ])
            
            assert result.exit_code == 0
            assert "Calculando data útil D-1" in result.output
            assert "Data calculada: 2025-09-04" in result.output
            mock_calculator.get_business_day.assert_called_with(n_days=1)
    
    def test_carteira_all_portfolios_with_consolidar(self, runner, mock_portfolio_manager):
        """Testa comando carteira para todos portfolios com consolidação."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_daily_report_service') as mock_ds, \
             patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            # Múltiplos portfolios
            portfolio1 = Mock()
            portfolio1.id = "12345"
            portfolio1.name = "FUNDO A FIDC"
            
            portfolio2 = Mock()
            portfolio2.id = "67890"
            portfolio2.name = "FUNDO B FIDC"
            
            mock_portfolio_manager.get_all_portfolios.return_value = {
                "12345": portfolio1,
                "67890": portfolio2
            }
            
            # Mock calculator
            calc = Mock()
            calc.get_business_day.return_value = date(2025, 9, 4)
            
            # Mock service
            service = Mock()
            report = Mock()
            report.filename = "CARTEIRA_TEST.csv"
            report.content = "DATA,ATIVO,VALOR\n2025-09-04,CDB,1000"
            service.get_report_sync.return_value = report
            service.save_report.return_value = True
            
            mock_pm.return_value = mock_portfolio_manager
            mock_ds.return_value = service
            mock_calc.return_value = calc
            
            result = runner.invoke(carteira, [
                '--n-days', '0',  # Sem portfolio = todos
                '--consolidar',
                '--formato', 'csv',
                '--saida', tmpdir
            ])
            
            assert result.exit_code == 0
            assert "TODOS OS PORTFOLIOS (2)" in result.output
            assert "Consolidação: ✅ ATIVA" in result.output
    
    def test_test_n_days_command(self, runner, mock_calculator):
        """Testa comando de teste de dias úteis."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc:
            
            mock_calculator.get_business_day.side_effect = [
                date(2025, 9, 4),  # Para n_days=2
                date(2025, 8, 30)  # Para data específica
            ]
            
            mock_calc.return_value = mock_calculator
            
            result = runner.invoke(test_n_days, ['--n-days', '2'])
            
            assert result.exit_code == 0
            assert "Testando cálculo de dias úteis (D-2)" in result.output
            assert "Data útil D-2: 2025-09-04" in result.output
    
    def test_error_handling_invalid_portfolio(self, runner):
        """Testa tratamento de erro para portfolio inválido."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm:
            
            mock_pm.return_value.get_portfolio.side_effect = Exception("Portfolio not found")
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--carteiraId', '99999',
                '--format', 'CSVBR'
            ])
            
            assert result.exit_code == 0  # CLI deve capturar erro
            assert "❌ Erro inesperado" in result.output
    
    def test_error_handling_date_calculation_failure(self, runner, mock_portfolio_manager):
        """Testa tratamento de erro no cálculo de data."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc:
            
            # Calculator que falha
            calc = Mock()
            calc.get_business_day.return_value = None  # Simula falha
            
            mock_pm.return_value = mock_portfolio_manager
            mock_calc.return_value = calc
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--carteiraId', '12345',
                '--format', 'CSVBR',
                '--n-days', '10'
            ])
            
            assert result.exit_code == 0  # CLI deve capturar erro
            assert "❌ Erro ao calcular dia útil" in result.output
    
    def test_validation_basediaria_without_dates(self, runner, mock_portfolio_manager):
        """Testa validação de base diária sem datas."""
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm:
            
            mock_pm.return_value = mock_portfolio_manager
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--carteiraId', '12345',
                '--format', 'CSVBR',
                '--baseDiaria'  # Sem dataInicial/dataFinal nem n-days
            ])
            
            assert result.exit_code == 0
            assert "❌ Para base diária sem --n-days, --dataInicial e --dataFinal são obrigatórios" in result.output


class TestConsolidationFunctions:
    """Testes para funções de consolidação."""
    
    def test_consolidate_csv_files(self):
        """Testa consolidação de arquivos CSV."""
        from daycoval.cli.commands.enhanced_profitability import _consolidate_csv_files
        
        # Mock reports
        report1 = Mock()
        report1.filename = "FUNDO_A.csv"
        report1.content = "COLUNA1,COLUNA2\nvalor1,valor2\n"
        
        report2 = Mock()
        report2.filename = "FUNDO_B.csv"
        report2.content = "COLUNA1,COLUNA2\nvalor3,valor4\n"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "consolidado.csv"
            
            result = _consolidate_csv_files([report1, report2], output_path)
            
            assert result == True
            assert output_path.exists()
            
            # Verificar conteúdo
            content = output_path.read_text()
            assert "FUNDO_ORIGEM" in content
            assert "FUNDO_A" in content
            assert "FUNDO_B" in content
            assert "valor1" in content
            assert "valor3" in content
    
    def test_consolidate_csv_files_empty_reports(self):
        """Testa consolidação com relatórios vazios."""
        from daycoval.cli.commands.enhanced_profitability import _consolidate_csv_files
        
        # Reports vazios ou sem conteúdo
        empty_reports = [Mock(content=""), Mock(content=None)]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "consolidado.csv"
            
            result = _consolidate_csv_files(empty_reports, output_path)
            
            assert result == False


# Configuração para testes
@pytest.fixture(scope="session")
def setup_test_environment():
    """Configura ambiente de teste."""
    # Configurar paths se necessário
    pass


if __name__ == '__main__':
    # Execução direta para testes rápidos
    print("🧪 Executando testes dos comandos CLI aprimorados...")
    
    runner = CliRunner()
    
    # Teste básico do help
    try:
        result = runner.invoke(enhanced_profitability_cli, ['--help'])
        if result.exit_code == 0:
            print("✅ Teste básico do help passou")
        else:
            print(f"❌ Teste básico falhou: {result.output}")
            
    except Exception as e:
        print(f"❌ Erro no teste básico: {str(e)}")
    
    print("\n💡 Para executar testes completos:")
    print("   pytest tests/test_enhanced_profitability_cli.py -v")
    print("   pytest tests/test_enhanced_profitability_cli.py::TestEnhancedProfitabilityCLI -v")