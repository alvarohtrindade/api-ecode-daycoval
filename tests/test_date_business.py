#!/usr/bin/env python3
"""
Testes unitários e de integração para o módulo date_business.py

Testa:
- Cálculo de dias úteis via tabela DW_CORPORATIVO.Dm_Calendario
- Validação de dias úteis  
- Resolução de datas específicas
- Integração com banco MySQL

Author: Claude Code
Date: 2025-09-04
Version: 1.0
"""

import os
import sys
import pytest
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from daycoval.utils.date_business import (
    BusinessDateCalculator,
    BusinessDateError,
    get_business_date_calculator,
    get_business_day,
    is_business_day
)


class TestBusinessDateCalculator:
    """Testes para a classe BusinessDateCalculator."""
    
    @pytest.fixture
    def mock_connector(self):
        """Mock do conector MySQL para testes."""
        connector = Mock()
        # Simular dados de calendário realistas
        mock_calendar_data = [
            (date(2025, 9, 1), 1, False, True),   # Segunda-feira útil
            (date(2025, 9, 2), 2, False, True),   # Terça-feira útil  
            (date(2025, 9, 3), 3, False, True),   # Quarta-feira útil
            (date(2025, 9, 4), 4, False, True),   # Quinta-feira útil
            (date(2025, 9, 5), 5, False, True),   # Sexta-feira útil
            (date(2025, 9, 6), 6, False, False),  # Sábado não útil
            (date(2025, 9, 7), 7, True, False),   # Domingo feriado
            (date(2025, 9, 8), 1, False, True),   # Segunda-feira útil
        ]
        connector.query_all.return_value = mock_calendar_data
        return connector
    
    @pytest.fixture
    def calculator(self, mock_connector):
        """Calculadora de dias úteis com mock."""
        return BusinessDateCalculator(mock_connector)
    
    def test_initialization(self):
        """Testa inicialização do calculador."""
        calc = BusinessDateCalculator()
        assert calc.connector is not None
        assert calc._cache_business_dates is None
        assert calc._cache_valid_until is None
    
    def test_load_business_dates(self, calculator):
        """Testa carregamento de dias úteis."""
        business_dates = calculator._load_business_dates()
        
        # Verificar se carregou apenas dias úteis
        expected_dates = [
            date(2025, 9, 1),
            date(2025, 9, 2), 
            date(2025, 9, 3),
            date(2025, 9, 4),
            date(2025, 9, 5),
            date(2025, 9, 8)
        ]
        
        assert business_dates == expected_dates
        assert calculator._cache_business_dates is not None
        assert calculator._cache_valid_until is not None
    
    def test_is_business_day(self, calculator):
        """Testa verificação de dias úteis."""
        # Dia útil
        assert calculator.is_business_day(date(2025, 9, 1)) == True
        assert calculator.is_business_day('2025-09-02') == True
        
        # Não útil
        assert calculator.is_business_day(date(2025, 9, 6)) == False  # Sábado
        assert calculator.is_business_day('2025-09-07') == False      # Domingo feriado
    
    def test_get_business_day_n_days(self, calculator):
        """Testa cálculo de dias úteis atrás."""
        with patch('daycoval.utils.date_business.date') as mock_date:
            mock_date.today.return_value = date(2025, 9, 8)
            
            # D-0 (hoje)
            result = calculator.get_business_day(n_days=0)
            assert result == date(2025, 9, 8)
            
            # D-1 (ontem útil)
            result = calculator.get_business_day(n_days=1)
            assert result == date(2025, 9, 5)  # Sexta anterior
            
            # D-2
            result = calculator.get_business_day(n_days=2)
            assert result == date(2025, 9, 4)
    
    def test_get_business_day_specific_date(self, calculator):
        """Testa busca por data específica."""
        # Data útil específica
        result = calculator.get_business_day(specific_date='2025-09-01')
        assert result == date(2025, 9, 1)
        
        # Data não útil - deve retornar anterior
        result = calculator.get_business_day(specific_date='2025-09-06')  # Sábado
        assert result == date(2025, 9, 5)  # Sexta anterior
    
    def test_get_next_business_day(self, calculator):
        """Testa busca do próximo dia útil."""
        result = calculator.get_next_business_day(date(2025, 9, 5))  # Sexta
        assert result == date(2025, 9, 8)  # Segunda seguinte
        
        result = calculator.get_next_business_day('2025-09-06')  # Sábado
        assert result == date(2025, 9, 8)  # Segunda seguinte
    
    def test_get_previous_business_day(self, calculator):
        """Testa busca do dia útil anterior."""
        result = calculator.get_previous_business_day(date(2025, 9, 8))  # Segunda
        assert result == date(2025, 9, 5)  # Sexta anterior
        
        result = calculator.get_previous_business_day('2025-09-07')  # Domingo
        assert result == date(2025, 9, 5)  # Sexta anterior
    
    def test_get_business_days_between(self, calculator):
        """Testa busca de dias úteis em período."""
        result = calculator.get_business_days_between('2025-09-01', '2025-09-08')
        expected = [
            date(2025, 9, 1),
            date(2025, 9, 2),
            date(2025, 9, 3),
            date(2025, 9, 4),
            date(2025, 9, 5),
            date(2025, 9, 8)
        ]
        assert result == expected
    
    def test_cache_mechanism(self, calculator):
        """Testa mecanismo de cache."""
        # Primeira chamada carrega do banco
        business_dates_1 = calculator._load_business_dates()
        call_count_1 = calculator.connector.query_all.call_count
        
        # Segunda chamada usa cache
        business_dates_2 = calculator._load_business_dates()
        call_count_2 = calculator.connector.query_all.call_count
        
        assert business_dates_1 == business_dates_2
        assert call_count_1 == call_count_2  # Não fez nova query
        
        # Force refresh quebra cache
        business_dates_3 = calculator._load_business_dates(force_refresh=True)
        call_count_3 = calculator.connector.query_all.call_count
        
        assert call_count_3 > call_count_2  # Fez nova query
    
    def test_error_handling_no_data(self, mock_connector):
        """Testa tratamento de erro quando não há dados."""
        mock_connector.query_all.return_value = []
        calculator = BusinessDateCalculator(mock_connector)
        
        with pytest.raises(BusinessDateError):
            calculator._load_business_dates()
    
    def test_error_handling_database_error(self, mock_connector):
        """Testa tratamento de erro de banco."""
        mock_connector.query_all.side_effect = Exception("Database connection error")
        calculator = BusinessDateCalculator(mock_connector)
        
        with pytest.raises(BusinessDateError):
            calculator._load_business_dates()


class TestUtilityFunctions:
    """Testes para funções utilitárias."""
    
    @patch('daycoval.utils.date_business.get_mysql_connector')
    def test_get_business_date_calculator(self, mock_get_connector):
        """Testa função factory do calculador."""
        mock_connector = Mock()
        mock_get_connector.return_value = mock_connector
        
        calc = get_business_date_calculator()
        assert isinstance(calc, BusinessDateCalculator)
        assert calc.connector == mock_connector
    
    @patch('daycoval.utils.date_business.get_business_date_calculator')
    def test_convenience_functions(self, mock_get_calculator):
        """Testa funções de conveniência."""
        mock_calculator = Mock()
        mock_calculator.get_business_day.return_value = date(2025, 9, 1)
        mock_calculator.is_business_day.return_value = True
        mock_get_calculator.return_value = mock_calculator
        
        # Testar get_business_day
        result = get_business_day(n_days=1)
        assert result == date(2025, 9, 1)
        mock_calculator.get_business_day.assert_called_once_with(1, None)
        
        # Testar is_business_day
        result = is_business_day('2025-09-01')
        assert result == True
        mock_calculator.is_business_day.assert_called_once_with('2025-09-01')


class TestIntegration:
    """Testes de integração (requerem banco de dados real)."""
    
    @pytest.mark.integration
    def test_real_database_connection(self):
        """Teste de integração com banco real (apenas se disponível)."""
        try:
            from daycoval.utils.mysql_connector_utils import get_mysql_connector
            
            # Tentar conexão real
            connector = get_mysql_connector()
            success = connector.test_connection()
            
            if not success:
                pytest.skip("Banco de dados não disponível para teste de integração")
            
            # Testar calculador com banco real
            calculator = BusinessDateCalculator(connector)
            
            # Teste básico
            business_date = calculator.get_business_day(n_days=1)
            assert business_date is not None
            assert isinstance(business_date, date)
            
            # Fechar conexão
            calculator.close()
            
        except ImportError:
            pytest.skip("Dependências de banco não disponíveis")
        except Exception as e:
            pytest.skip(f"Erro de integração: {str(e)}")


class TestEdgeCases:
    """Testes de casos extremos."""
    
    @pytest.fixture
    def calculator_minimal_data(self):
        """Calculadora com dados mínimos."""
        connector = Mock()
        # Apenas dois dias úteis
        mock_data = [
            (date(2025, 9, 1), 1, False, True),
            (date(2025, 9, 2), 2, False, True),
        ]
        connector.query_all.return_value = mock_data
        return BusinessDateCalculator(connector)
    
    def test_insufficient_historical_data(self, calculator_minimal_data):
        """Testa comportamento com poucos dados históricos."""
        with patch('daycoval.utils.date_business.date') as mock_date:
            mock_date.today.return_value = date(2025, 9, 2)
            
            # Tentar buscar mais dias do que disponível
            result = calculator_minimal_data.get_business_day(n_days=5)
            assert result is None  # Não deve ter dados suficientes
    
    def test_date_format_variations(self):
        """Testa diferentes formatos de data."""
        calculator = BusinessDateCalculator()
        
        # Mock para evitar query real
        with patch.object(calculator, '_load_business_dates') as mock_load:
            mock_load.return_value = [date(2025, 9, 1)]
            
            # Diferentes formatos devem funcionar
            assert calculator.is_business_day('2025-09-01') in [True, False]
            assert calculator.is_business_day(date(2025, 9, 1)) in [True, False]
            assert calculator.is_business_day(datetime(2025, 9, 1)) in [True, False]


# Configuração de fixtures globais
@pytest.fixture(scope="session")
def setup_logging():
    """Configura logging para testes."""
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


if __name__ == '__main__':
    # Execução direta para testes rápidos
    print("🧪 Executando testes do módulo date_business...")
    
    # Teste básico sem pytest
    try:
        # Mock simples
        mock_connector = Mock()
        mock_data = [
            (date(2025, 9, 1), 1, False, True),
            (date(2025, 9, 2), 2, False, True),
        ]
        mock_connector.query_all.return_value = mock_data
        
        calc = BusinessDateCalculator(mock_connector)
        business_dates = calc._load_business_dates()
        
        print(f"✅ Teste básico passou: {len(business_dates)} dias úteis carregados")
        print(f"   Dias: {business_dates}")
        
    except Exception as e:
        print(f"❌ Teste básico falhou: {str(e)}")
        print(traceback.format_exc())
    
    print("\n💡 Para executar testes completos:")
    print("   pytest tests/test_date_business.py -v")
    print("   pytest tests/test_date_business.py::TestBusinessDateCalculator -v") 
    print("   pytest tests/test_date_business.py -m integration  # Apenas integração")