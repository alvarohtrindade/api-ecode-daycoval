#!/usr/bin/env python3
"""
Script de teste para validar configuração e funcionalidade.
"""

import json
from pathlib import Path
from datetime import datetime
from backend.apis.daycoval.api import PortfolioConfig, sanitize_filename

def test_portfolio_config():
    """Testa carregamento e validação do arquivo portfolios.json"""
    print("🧪 TESTE: Configuração de Portfolios")
    print("-" * 50)
    
    try:
        config = PortfolioConfig("portfolios.json")
        portfolios = config.get_all_portfolios()
        
        print(f"✅ Arquivo carregado com sucesso")
        print(f"✅ Total de portfolios: {len(portfolios)}")
        
        # Testar alguns portfolios específicos
        test_portfolios = ["4471709", "8205906", "18205906", "28205906"]
        
        print(f"\n📋 Teste de portfolios específicos:")
        for portfolio_id in test_portfolios:
            fund_name = config.get_portfolio_name(portfolio_id)
            print(f"   {portfolio_id} -> {fund_name}")
        
        # Testar portfolio inexistente
        fake_portfolio = "9999999"
        default_name = config.get_portfolio_name(fake_portfolio)
        print(f"   {fake_portfolio} -> {default_name} (padrão)")
        
        # Testar rate limit config
        rate_config = config.get_rate_limit_config()
        print(f"\n⚙️  Configuração Rate Limit:")
        print(f"   Max calls: {rate_config['max_calls']}")
        print(f"   Period: {rate_config['period_seconds']}s")
        print(f"   Backoff factor: {rate_config['backoff_factor']}")
        print(f"   Max retries: {rate_config['max_retries']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de configuração: {e}")
        return False

def test_filename_sanitization():
    """Testa sanitização de nomes de arquivo"""
    print("\n🧪 TESTE: Sanitização de Nomes de Arquivo")
    print("-" * 50)
    
    test_cases = [
        ("CATALISE FIC FIDC - RL", "CATALISE_FIC_FIDC_RL"),
        ("ARTANIS FUNDO DE INVESTIMENTO MULTIMERCA", "ARTANIS_FUNDO_DE_INVESTIMENTO_MULTIMERCA"),
        ("3RD - FUNDO DE INVESTIMENTO EM DIREITOS", "3RD_FUNDO_DE_INVESTIMENTO_EM_DIREITOS"),
        ("ÁGIS - FIDC NP", "AGIS_FIDC_NP"),
        ("BASÃ- FUNDO DE INVESTIMENTO EM DIREITOS", "BASA_FUNDO_DE_INVESTIMENTO_EM_DIREITOS"),
        ("BELLIN FIC FIM RESPONSABILIDADE LIMTADA", "BELLIN_FIC_FIM_RESPONSABILIDADE_LIMTADA"),
        ("", "ARQUIVO_SEM_NOME")
    ]
    
    all_passed = True
    
    for original, expected in test_cases:
        sanitized = sanitize_filename(original)
        status = "✅" if sanitized == expected else "❌"
        print(f"   {status} '{original}' -> '{sanitized}'")
        
        if sanitized != expected:
            print(f"      Esperado: '{expected}'")
            all_passed = False
    
    return all_passed

def test_filename_generation():
    """Testa geração completa de nomes de arquivo"""
    print("\n🧪 TESTE: Geração de Nomes de Arquivo PDF")
    print("-" * 50)
    
    try:
        config = PortfolioConfig("portfolios.json")
        test_date = "2025-07-29"
        date_formatted = test_date.replace('-', '')
        
        # Testar alguns portfolios
        test_portfolios = ["4471709", "8205906", "8674582", "18205906", "28205906"]
        
        for portfolio_id in test_portfolios:
            fund_name = config.get_portfolio_name(portfolio_id)
            clean_fund_name = sanitize_filename(fund_name)
            filename = f"{clean_fund_name}_{date_formatted}.pdf"
            
            print(f"   {portfolio_id}: {filename}")
            
            # Verificar se nome é válido
            if len(filename) > 255:
                print(f"      ⚠️  Nome muito longo: {len(filename)} caracteres")
            
            # Verificar caracteres inválidos
            invalid_chars = '<>:"/\\|?*'
            has_invalid = any(char in filename for char in invalid_chars)
            if has_invalid:
                print(f"      ❌ Contém caracteres inválidos")
                return False
        
        print(f"✅ Todos os nomes de arquivo são válidos")
        return True
        
    except Exception as e:
        print(f"❌ Erro na geração de nomes: {e}")
        return False

def test_json_structure():
    """Testa estrutura do arquivo JSON"""
    print("\n🧪 TESTE: Estrutura do Arquivo JSON")
    print("-" * 50)
    
    try:
        with open("portfolios.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verificar chaves obrigatórias
        required_keys = ["portfolios", "metadata"]
        for key in required_keys:
            if key in data:
                print(f"✅ Chave '{key}' presente")
            else:
                print(f"❌ Chave '{key}' ausente")
                return False
        
        # Verificar metadata
        metadata = data["metadata"]
        required_metadata = ["version", "rate_limit", "default_fund_name"]
        for key in required_metadata:
            if key in metadata:
                print(f"✅ Metadata '{key}' presente")
            else:
                print(f"❌ Metadata '{key}' ausente")
                return False
        
        # Verificar rate_limit
        rate_limit = metadata["rate_limit"]
        required_rate_keys = ["max_calls", "period_seconds", "backoff_factor", "max_retries"]
        for key in required_rate_keys:
            if key in rate_limit:
                print(f"✅ Rate limit '{key}' presente")
            else:
                print(f"❌ Rate limit '{key}' ausente")
                return False
        
        # Verificar portfolios
        portfolios = data["portfolios"]
        if isinstance(portfolios, dict):
            print(f"✅ Portfolios é um dicionário com {len(portfolios)} entradas")
        else:
            print(f"❌ Portfolios não é um dicionário")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na validação JSON: {e}")
        return False

def generate_sample_filenames():
    """Gera exemplos de nomes de arquivo para verificação manual"""
    print("\n📄 EXEMPLOS DE NOMES DE ARQUIVO GERADOS")
    print("=" * 60)
    
    try:
        config = PortfolioConfig("portfolios.json")
        portfolios = config.get_all_portfolios()
        test_date = "20250729"
        
        print(f"Data de exemplo: {test_date}")
        print(f"Formato: NOME_FUNDO_YYYYMMDD.pdf\n")
        
        # Mostrar primeiros 20 exemplos
        for i, (portfolio_id, fund_name) in enumerate(list(portfolios.items())[:20]):
            clean_name = sanitize_filename(fund_name)
            filename = f"{clean_name}_{test_date}.pdf"
            print(f"{i+1:2}. {portfolio_id} -> {filename}")
        
        total = len(portfolios)
        if total > 20:
            print(f"... e mais {total - 20} arquivos")
        
        print(f"\nTotal de arquivos que serão gerados: {total}")
        
        # Estatísticas
        lengths = []
        for fund_name in portfolios.values():
            clean_name = sanitize_filename(fund_name)
            filename = f"{clean_name}_{test_date}.pdf"
            lengths.append(len(filename))
        
        print(f"\nEstatísticas dos nomes:")
        print(f"  Menor: {min(lengths)} caracteres")
        print(f"  Maior: {max(lengths)} caracteres")
        print(f"  Média: {sum(lengths)/len(lengths):.1f} caracteres")
        
        # Verificar nomes muito longos
        long_names = [(portfolio_id, fund_name) for portfolio_id, fund_name in portfolios.items() 
                     if len(f"{sanitize_filename(fund_name)}_{test_date}.pdf") > 150]
        
        if long_names:
            print(f"\n⚠️  Nomes longos (>150 chars):")
            for portfolio_id, fund_name in long_names[:5]:
                clean_name = sanitize_filename(fund_name)
                filename = f"{clean_name}_{test_date}.pdf"
                print(f"     {portfolio_id}: {len(filename)} chars - {filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao gerar exemplos: {e}")
        return False

def validate_all_portfolio_ids():
    """Valida se todos os IDs de portfolio estão presentes"""
    print("\n🧪 TESTE: Validação de IDs de Portfolio")
    print("-" * 50)
    
    # IDs esperados do documento original
    expected_ids = [
        "4471709", "8205906", "8310432", "8351082", "8354456", "8367710", "8367779", 
        "8447055", "8482268", "8606048", "8618178", "8636281", "8636290", "8674507", 
        "8674531", "8674582", "8696977", "8745218", "8745307", "8745323", "8745390", 
        "8745838", "8745927", "8745935", "8745951", "8746079", "8746125", "8746150", 
        "8810206", "8849803", "8866872", "8881480", "8881499", "8935270", "8935289", 
        "8935335", "8935386", "8935564", "8935572", "8935580", "8936200", "8936226", 
        "8936234", "8936242", "8936277", "8936285", "8936293", "8936315", "8936323", 
        "8936331", "8936340", "8936366", "8936390", "8936404", "8936412", "9098127", 
        "9098470", "9101063", "9109935", "9619801", "9644598", "9674462", "9699139", 
        "9762760", "9776710", "9783300", "9783334", "9951865", "9955801", "10104909", 
        "10104933", "10118632", "10210024", "10344250", "10344349", "10432906", 
        "10434860", "10435131", "10502726", "10581936", "10581944", "10627715", 
        "10746072", "10784039", "10784047", "10784063", "10856250", "10873112", 
        "10873570", "10885536", "11104909", "18205906", "18606048", "18674582", 
        "18745927", "18849803", "18866872", "18935580", "18936242", "19783300", 
        "20746072", "20784047", "28205906", "28745390", "29783300", "30784047", 
        "38205906", "40784047"
    ]
    
    try:
        config = PortfolioConfig("portfolios.json")
        configured_ids = set(config.get_all_portfolios().keys())
        expected_ids_set = set(expected_ids)
        
        print(f"IDs esperados: {len(expected_ids_set)}")
        print(f"IDs configurados: {len(configured_ids)}")
        
        # Verificar IDs ausentes
        missing_ids = expected_ids_set - configured_ids
        if missing_ids:
            print(f"❌ IDs ausentes ({len(missing_ids)}):")
            for missing_id in sorted(missing_ids):
                print(f"   - {missing_id}")
            return False
        else:
            print(f"✅ Todos os IDs esperados estão presentes")
        
        # Verificar IDs extras
        extra_ids = configured_ids - expected_ids_set
        if extra_ids:
            print(f"⚠️  IDs extras ({len(extra_ids)}):")
            for extra_id in sorted(extra_ids):
                print(f"   + {extra_id}")
        
        return len(missing_ids) == 0
        
    except Exception as e:
        print(f"❌ Erro na validação de IDs: {e}")
        return False

def run_all_tests():
    """Executa todos os testes"""
    print("🚀 EXECUTANDO TODOS OS TESTES")
    print("=" * 60)
    
    tests = [
        ("Estrutura JSON", test_json_structure),
        ("Configuração Portfolio", test_portfolio_config),
        ("Sanitização de Nomes", test_filename_sanitization),
        ("Geração de Nomes PDF", test_filename_generation),
        ("Validação IDs Portfolio", validate_all_portfolio_ids)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSOU" if result else "❌ FALHOU"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            print(f"\n❌ ERRO: {test_name} - {e}")
            results.append((test_name, False))
    
    # Resumo final
    print(f"\n{'='*60}")
    print(f"RESUMO DOS TESTES")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nRESULTADO: {passed}/{total} testes passaram")
    
    if passed == total:
        print(f"🎉 TODOS OS TESTES PASSARAM! Sistema pronto para uso.")
        generate_sample_filenames()
    else:
        print(f"⚠️  Alguns testes falharam. Revise as configurações.")
    
    return passed == total

def main():
    """Função principal"""
    try:
        success = run_all_tests()
        
        if success:
            print(f"\n📋 PRÓXIMOS PASSOS:")
            print(f"   1. python cli_enhanced.py list  # Ver todos os portfolios")
            print(f"   2. python cli_enhanced.py single --portfolio 4471709 --date 2025-07-29  # Testar um")
            print(f"   3. python cli_enhanced.py batch --all-portfolios --date 2025-07-29  # Processar todos")
        
        return success
        
    except Exception as e:
        print(f"❌ Erro inesperado nos testes: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)