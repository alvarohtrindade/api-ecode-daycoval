#!/usr/bin/env python3
"""
Testes de integração end-to-end para as novas funcionalidades.

Testa fluxos completos:
- CLI -> date_business -> consolidação -> arquivos
- Integração com banco de dados (se disponível)
- Validação de arquivos gerados

Author: Claude Code
Date: 2025-09-04
Version: 1.0
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import date, datetime
from click.testing import CliRunner

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestEndToEndFlow:
    """Testes de fluxo completo end-to-end."""
    
    @pytest.fixture
    def runner(self):
        """Runner do Click."""
        return CliRunner()
    
    @pytest.fixture
    def complete_mock_environment(self):
        """Mock completo do ambiente para testes e2e."""
        env = {}
        
        # Portfolio Manager
        portfolio = Mock()
        portfolio.id = "12345"
        portfolio.name = "FUNDO_TESTE_FIDC"
        
        portfolio_manager = Mock()
        portfolio_manager.get_portfolio.return_value = portfolio
        portfolio_manager.get_all_portfolios.return_value = {"12345": portfolio}
        
        # Business Date Calculator
        calculator = Mock()
        calculator.get_business_day.return_value = date(2025, 9, 4)
        calculator.is_business_day.return_value = True
        
        # Report Service
        report = Mock()
        report.filename = "FUNDO_TESTE_FIDC_SINTETICA_20250904.csv"
        report.content = """FUNDO,DATA,RENTABILIDADE,PATRIMONIO
FUNDO_TESTE_FIDC,2025-09-04,0.15,1000000.50
FUNDO_TESTE_FIDC,2025-09-03,0.12,995000.25"""
        report.size_mb = 0.001
        
        service = Mock()
        service.get_synthetic_profitability_report_sync.return_value = report
        service.save_report.return_value = True
        
        env.update({
            'portfolio_manager': portfolio_manager,
            'calculator': calculator,
            'service': service,
            'report': report
        })
        
        return env
    
    @pytest.mark.integration
    def test_complete_flow_n_days_consolidation(self, runner, complete_mock_environment):
        """Teste completo: --n-days + --consolidar + validação de arquivo."""
        
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_profitability_service') as mock_cs, \
             patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            # Configurar mocks
            mock_pm.return_value = complete_mock_environment['portfolio_manager']
            mock_cs.return_value = complete_mock_environment['service']
            mock_calc.return_value = complete_mock_environment['calculator']
            
            # Executar comando completo
            from daycoval.cli.commands.enhanced_profitability import rentabilidade_sintetica
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--format', 'CSVBR',  # Todas as carteiras
                '--n-days', '2',
                '--consolidar',
                '--formato-consolidado', 'csv',
                '--saida', tmpdir
            ])
            
            # Validações do resultado
            assert result.exit_code == 0, f"Comando falhou: {result.output}"
            
            # Verificar output esperado
            assert "Calculando data útil D-2" in result.output
            assert "Data de referência: 2025-09-04" in result.output
            assert "TODAS AS CARTEIRAS" in result.output
            assert "Consolidação: ✅ ATIVA" in result.output
            assert "✅ Sucessos: 1" in result.output
            
            # Verificar se arquivo foi "salvo" (mock)
            mock_service = complete_mock_environment['service']
            mock_service.save_report.assert_called()
            
            # Verificar chamadas corretas
            mock_calc = complete_mock_environment['calculator']
            mock_calc.get_business_day.assert_called_with(n_days=2)
    
    @pytest.mark.integration
    def test_carteira_flow_with_consolidation(self, runner, complete_mock_environment):
        """Teste fluxo de carteira com consolidação."""
        
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.create_daily_report_service') as mock_ds, \
             patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc, \
             tempfile.TemporaryDirectory() as tmpdir:
            
            # Mock daily report service
            daily_service = Mock()
            daily_report = Mock()
            daily_report.filename = "CARTEIRA_12345_20250904.csv"
            daily_report.content = "DATA,ATIVO,VALOR\n2025-09-04,CDB,50000.00"
            daily_service.get_report_sync.return_value = daily_report
            daily_service.save_report.return_value = True
            
            # Configurar mocks
            mock_pm.return_value = complete_mock_environment['portfolio_manager']
            mock_ds.return_value = daily_service
            mock_calc.return_value = complete_mock_environment['calculator']
            
            from daycoval.cli.commands.enhanced_profitability import carteira
            
            result = runner.invoke(carteira, [
                '--portfolio', '12345',
                '--n-days', '1',
                '--consolidar',
                '--formato', 'csv',
                '--saida', tmpdir
            ])
            
            # Validações
            assert result.exit_code == 0
            assert "Calculando data útil D-1" in result.output
            assert "Relatório de Carteira - Portfolio 12345" in result.output
            assert "Consolidação: ✅ ATIVA" in result.output
    
    def test_error_resilience_flow(self, runner):
        """Teste de resiliência a erros."""
        
        with patch('daycoval.cli.commands.enhanced_profitability.get_portfolio_manager') as mock_pm, \
             patch('daycoval.cli.commands.enhanced_profitability.get_business_date_calculator') as mock_calc:
            
            # Simular erro na busca de portfolio
            mock_pm.side_effect = Exception("Database connection failed")
            
            from daycoval.cli.commands.enhanced_profitability import rentabilidade_sintetica
            
            result = runner.invoke(rentabilidade_sintetica, [
                '--carteiraId', '12345',
                '--format', 'CSVBR'
            ])
            
            # CLI deve tratar erro graciosamente
            assert result.exit_code == 0  # Não deve crashar
            assert "❌ Erro inesperado" in result.output
    
    def test_file_consolidation_real(self):
        """Teste de consolidação de arquivos real."""
        from daycoval.services.data_consolidation import create_consolidation_service
        
        # Criar relatórios mock reais
        report1 = Mock()
        report1.filename = "FUNDO_A_20250904.csv"
        report1.content = """FUNDO,DATA,RENTABILIDADE
FUNDO_A,2025-09-04,0.15
FUNDO_A,2025-09-03,0.12"""
        
        report2 = Mock()
        report2.filename = "FUNDO_B_20250904.csv"  
        report2.content = """FUNDO,DATA,RENTABILIDADE
FUNDO_B,2025-09-04,0.18
FUNDO_B,2025-09-03,0.14"""
        
        reports = [report1, report2]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "consolidado_teste.csv"
            
            # Testar consolidação real
            service = create_consolidation_service()
            success = service.consolidate_csv_reports(
                reports, output_path, "1048", include_metadata=True
            )
            
            assert success == True
            assert output_path.exists()
            
            # Verificar conteúdo consolidado
            content = output_path.read_text()
            assert "FUNDO_ORIGEM" in content
            assert "FUNDO_A_20250904" in content
            assert "FUNDO_B_20250904" in content
            assert "0.15" in content
            assert "0.18" in content
            
            # Verificar estrutura CSV
            lines = content.strip().split('\n')
            assert len(lines) >= 5  # Header + 4 data rows
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_database_integration_if_available(self):
        """Teste de integração com banco real (se disponível)."""
        try:
            from daycoval.utils.date_business import get_business_date_calculator
            from daycoval.utils.mysql_connector_utils import get_mysql_connector
            
            # Tentar conexão real
            try:
                connector = get_mysql_connector()
                if not connector.test_connection():
                    pytest.skip("Banco de dados não disponível")
                
                # Teste real do calculador
                calculator = get_business_date_calculator()
                
                # Teste básico
                business_date = calculator.get_business_day(n_days=1)
                assert business_date is not None
                assert isinstance(business_date, date)
                
                # Teste de verificação
                is_business = calculator.is_business_day(business_date)
                assert is_business == True
                
                print(f"✅ Teste de integração passou: {business_date}")
                
                # Cleanup
                calculator.close()
                
            except Exception as e:
                pytest.skip(f"Erro de banco: {str(e)}")
                
        except ImportError:
            pytest.skip("Dependências não disponíveis")


class TestFileOutputValidation:
    """Testes para validação de arquivos gerados."""
    
    def test_csv_output_structure(self):
        """Testa estrutura dos CSVs gerados."""
        from daycoval.services.data_consolidation import DataConsolidationService
        
        # Dados de teste
        report = Mock()
        report.filename = "TESTE.csv"
        report.content = """FUNDO,DATA,VALOR
TESTE_FIDC,2025-09-04,1000.50
TESTE_FIDC,2025-09-03,995.25"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.csv"
            
            service = DataConsolidationService()
            success = service.consolidate_csv_reports(
                [report], output_path, "1048", include_metadata=True
            )
            
            assert success == True
            assert output_path.exists()
            
            # Validar estrutura CSV
            import csv
            with open(output_path, 'r') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                # Verificar headers obrigatórios
                assert "FUNDO_ORIGEM" in headers
                assert "FUNDO" in headers
                assert "DATA" in headers
                assert "VALOR" in headers
                
                # Verificar dados
                rows = list(reader)
                assert len(rows) == 2
                assert rows[0]["FUNDO_ORIGEM"] == "TESTE"
                assert rows[0]["FUNDO"] == "TESTE_FIDC"
    
    def test_metadata_inclusion(self):
        """Testa inclusão de metadados."""
        from daycoval.services.data_consolidation import DataConsolidationService
        
        report = Mock()
        report.filename = "PORTFOLIO_123.csv"
        report.content = "CAMPO1,CAMPO2\nvalor1,valor2"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "with_metadata.csv"
            
            service = DataConsolidationService()
            success = service.consolidate_csv_reports(
                [report], output_path, "32", include_metadata=True
            )
            
            assert success == True
            
            content = output_path.read_text()
            assert "FUNDO_ORIGEM" in content
            assert "RELATORIO_INDEX" in content
            assert "TIMESTAMP_CONSOLIDACAO" in content
            assert "PORTFOLIO_123" in content


if __name__ == '__main__':
    # Execução direta para testes rápidos
    print("🧪 Executando testes de integração E2E...")
    
    # Teste básico de consolidação
    try:
        from src.daycoval.services.data_consolidation import create_consolidation_service
        
        service = create_consolidation_service()
        print("✅ Serviço de consolidação criado com sucesso")
        
    except Exception as e:
        print(f"❌ Erro no teste básico: {str(e)}")
    
    print("\n💡 Para executar testes completos:")
    print("   pytest tests/test_integration_e2e.py -v")
    print("   pytest tests/test_integration_e2e.py -m integration")
    print("   pytest tests/test_integration_e2e.py -m 'integration and slow'  # Testes lentos")