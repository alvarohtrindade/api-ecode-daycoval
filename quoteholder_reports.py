#!/usr/bin/env python3
"""
Módulo para geração de Relatórios de Posição de Cotistas (endpoint 45).
Reutiliza infraestrutura do sistema existente com lógica específica para cotistas.
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List

from api import (
    PortfolioConfig, 
    RateLimiter, 
    create_session_with_retries,
    sanitize_filename,
    API_KEY,
    BASE_URL
)
from utils.logging_utils import Log

class QuoteholderReportProcessor:
    """Processador de relatórios de posição de cotistas."""
    
    def __init__(self, config_file: str = "portfolios.json"):
        self.config = PortfolioConfig(config_file)
        self.quoteholder_config = self._load_quoteholder_config()
        self.rate_limit_config = self.config.get_rate_limit_config()
        self.rate_limiter = RateLimiter(
            max_calls=self.rate_limit_config["max_calls"],
            period=self.rate_limit_config["period_seconds"],
            backoff_factor=self.rate_limit_config["backoff_factor"]
        )
        self.session = create_session_with_retries(self.rate_limit_config)
    
    def _load_quoteholder_config(self) -> Dict[str, Any]:
        """Carrega configurações específicas para relatórios de cotistas."""
        quoteholder_config = self.config.config.get("quoteholder_reports", {})
        
        if not quoteholder_config:
            raise ValueError("Configuração 'quoteholder_reports' não encontrada no arquivo de configuração")
        
        return quoteholder_config
    
    def get_default_params(self) -> Dict[str, Any]:
        """Retorna parâmetros padrão para relatórios de cotistas."""
        return self.quoteholder_config.get("default_params", {}).copy()
    
    def get_portfolio_overrides(self, portfolio_id: str) -> Dict[str, Any]:
        """Retorna overrides específicos para um portfolio."""
        portfolio_overrides = self.quoteholder_config.get("portfolio_overrides", {})
        return portfolio_overrides.get(portfolio_id, {})
    
    def parse_range_parameter(self, range_str: str) -> Tuple[int, int]:
        """
        Converte string de range 'inicio:fim' para tuple de integers.
        
        Args:
            range_str: String no formato "1000:5000"
            
        Returns:
            Tuple (inicio, fim)
        """
        try:
            parts = range_str.split(':')
            if len(parts) != 2:
                raise ValueError("Range deve estar no formato 'inicio:fim'")
            
            inicio = int(parts[0].strip())
            fim = int(parts[1].strip())
            
            if inicio > fim:
                raise ValueError("Valor inicial não pode ser maior que o final")
            
            return inicio, fim
        except ValueError as e:
            raise ValueError(f"Range inválido '{range_str}': {e}")
    
    def build_request_params(
        self,
        portfolio_id: str,
        report_date: datetime,
        report_format: str,
        client_range: Optional[str] = None,
        advisor_range: Optional[str] = None,
        advisor2_range: Optional[str] = None,
        investor_class: Optional[int] = None,
        show_if_code: Optional[bool] = None,
        excel_headers: Optional[bool] = None,
        message: Optional[str] = None,
        **extra_overrides
    ) -> Dict[str, Any]:
        """
        Constrói parâmetros completos para a requisição.
        
        Args:
            portfolio_id: ID da carteira
            report_date: Data do relatório
            report_format: Formato de saída (PDF, CSVBR, etc.)
            client_range: Range de clientes "inicio:fim"
            advisor_range: Range de assessores "inicio:fim"
            advisor2_range: Range de assessores 2 "inicio:fim"
            investor_class: Classe de investidor (-1 a 21)
            show_if_code: Se deve apresentar código IF
            excel_headers: Se deve gerar headers Excel
            message: Mensagem customizada
            **extra_overrides: Outros overrides específicos
            
        Returns:
            Dicionário com parâmetros completos da requisição
        """
        # Começar com defaults
        params = self.get_default_params()
        
        # Aplicar overrides específicos do portfolio
        portfolio_overrides = self.get_portfolio_overrides(portfolio_id)
        params.update(portfolio_overrides)
        
        # Parâmetros sempre necessários
        params.update({
            "carteira": portfolio_id,
            "format": report_format.upper(),
            "data": report_date.strftime('%Y-%m-%d')
        })
        
        # Aplicar overrides da CLI
        if client_range:
            inicio, fim = self.parse_range_parameter(client_range)
            params["clienteInicial"] = inicio
            params["clienteFinal"] = fim
        
        if advisor_range:
            inicio, fim = self.parse_range_parameter(advisor_range)
            params["assessorInicial"] = inicio
            params["assessorFinal"] = fim
        
        if advisor2_range:
            inicio, fim = self.parse_range_parameter(advisor2_range)
            params["assessor2Inicial"] = inicio
            params["assessor2Final"] = fim
        
        if investor_class is not None:
            params["classeInvestidor"] = investor_class
        
        if show_if_code is not None:
            params["apresentaCodigoIF"] = show_if_code
        
        if excel_headers is not None:
            params["geraArquivoFormatoExcelHeaders"] = excel_headers
        
        if message is not None:
            params["mensagem"] = message
        
        # Aplicar overrides extras
        params.update(extra_overrides)
        
        return params
    
    def generate_filename(self, portfolio_id: str, fund_name: str, date: str, format: str) -> str:
        """
        Gera nome de arquivo para relatório de cotistas.
        
        Args:
            portfolio_id: ID da carteira
            fund_name: Nome do fundo
            date: Data no formato YYYY-MM-DD
            format: Formato do arquivo
            
        Returns:
            Nome do arquivo sanitizado
        """
        filename_config = self.quoteholder_config.get("filename_pattern", {})
        prefix = filename_config.get("prefix", "POSICAO_COTISTAS")
        
        # Sanitizar nome do fundo
        clean_fund_name = sanitize_filename(fund_name)
        
        # Converter data para formato sem hífens
        date_formatted = date.replace('-', '')
        
        # Determinar extensão
        extension_map = {
            'PDF': 'pdf',
            'CSVBR': 'csv',
            'CSVUS': 'csv',
            'TXTBR': 'txt',
            'TXTUS': 'txt'
        }
        extension = extension_map.get(format.upper(), 'txt')
        
        # Formato: POSICAO_COTISTAS_NOME_FUNDO_YYYYMMDD.ext
        filename = f"{prefix}_{clean_fund_name}_{date_formatted}.{extension}"
        
        return filename
    
    def fetch_quoteholder_report(
        self,
        portfolio_id: str,
        report_date: datetime,
        report_format: str = "PDF",
        **kwargs
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Busca relatório de posição de cotistas com retry automático.
        
        Args:
            portfolio_id: ID da carteira
            report_date: Data do relatório
            report_format: Formato de saída
            **kwargs: Parâmetros adicionais para build_request_params
            
        Returns:
            Tuple[Dict, bool]: (dados_do_relatorio, sucesso)
        """
        # Usar rate limiter
        self.rate_limiter.wait_if_needed()
        self.rate_limiter.record_call()
        
        try:
            endpoint = f"{BASE_URL}/report/reports/45"
            headers = {
                "apikey": API_KEY,
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Construir parâmetros da requisição
            request_params = self.build_request_params(
                portfolio_id=portfolio_id,
                report_date=report_date,
                report_format=report_format,
                **kwargs
            )
            
            Log.info(f"Portfolio {portfolio_id}: Buscando relatório de cotistas...")
            Log.debug(f"Portfolio {portfolio_id}: Parâmetros: {json.dumps(request_params, indent=2)}")
            
            response = self.session.post(endpoint, headers=headers, json=request_params, timeout=30)
            
            # Debug: Informações da resposta
            Log.info(f"Portfolio {portfolio_id}: Status Code: {response.status_code}")
            Log.info(f"Portfolio {portfolio_id}: Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            response.raise_for_status()
            
            # Verificar tipo de conteúdo
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'application/pdf' in content_type or report_format.upper() == 'PDF':
                # PDF
                Log.info(f"Portfolio {portfolio_id}: Resposta é um PDF")
                return {
                    'content': response.content,
                    'content_type': 'application/pdf',
                    'portfolio': portfolio_id,
                    'date': request_params['data'],
                    'request_params': request_params
                }, True
            
            elif 'application/json' in content_type:
                # JSON
                try:
                    return {
                        **response.json(),
                        'portfolio': portfolio_id,
                        'date': request_params['data'],
                        'request_params': request_params
                    }, True
                except json.JSONDecodeError as json_error:
                    Log.error(f"Portfolio {portfolio_id}: Erro ao fazer parse do JSON: {json_error}")
                    return {}, False
            
            else:
                # CSV/TXT
                Log.info(f"Portfolio {portfolio_id}: Resposta é texto ({content_type})")
                content = response.text
                
                return {
                    'content': content,
                    'content_type': content_type,
                    'portfolio': portfolio_id,
                    'date': request_params['data'],
                    'request_params': request_params
                }, True
        
        except requests.exceptions.HTTPError as e:
            Log.error(f"Portfolio {portfolio_id}: Erro HTTP: {e}")
            if hasattr(e, 'response'):
                Log.error(f"Portfolio {portfolio_id}: Status Code: {e.response.status_code}")
                Log.error(f"Portfolio {portfolio_id}: Response: {e.response.text}")
            return {}, False
        
        except requests.exceptions.RequestException as e:
            Log.error(f"Portfolio {portfolio_id}: Erro na requisição: {e}")
            return {}, False
        
        except Exception as e:
            Log.error(f"Portfolio {portfolio_id}: Erro inesperado: {e}")
            return {}, False
    
    def process_single_quoteholder_report(
        self,
        portfolio_id: str,
        report_date: datetime,
        output_dir: Path,
        report_format: str = "PDF",
        **kwargs
    ) -> Tuple[str, bool, str]:
        """
        Processa relatório de cotistas para um único portfolio.
        
        Returns:
            Tuple[portfolio_id, success, message]
        """
        try:
            fund_name = self.config.get_portfolio_name(portfolio_id)
            
            Log.info(f"Processando relatório de cotistas para portfolio {portfolio_id} ({fund_name})...")
            
            # Buscar relatório
            report_data, success = self.fetch_quoteholder_report(
                portfolio_id=portfolio_id,
                report_date=report_date,
                report_format=report_format,
                **kwargs
            )
            
            if not success or not report_data:
                error_msg = f"Falha ao obter relatório de cotistas para portfolio {portfolio_id}"
                Log.error(error_msg)
                return portfolio_id, False, error_msg
            
            # Gerar nome do arquivo
            date_str = report_date.strftime('%Y-%m-%d')
            filename = self.generate_filename(portfolio_id, fund_name, date_str, report_format)
            filepath = output_dir / filename
            
            # Verificar se arquivo já existe
            if filepath.exists():
                warning_msg = f"Arquivo já existe: {filepath}"
                Log.warning(warning_msg)
                return portfolio_id, True, f"Skipped - {warning_msg}"
            
            # Salvar arquivo
            content = report_data.get('content')
            if isinstance(content, bytes):
                with open(filepath, 'wb') as f:
                    f.write(content)
                file_size = len(content)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                file_size = len(content.encode('utf-8'))
            
            success_msg = f"Relatório de cotistas salvo: {filepath} ({file_size:,} bytes)"
            Log.info(success_msg)
            
            return portfolio_id, True, success_msg
        
        except Exception as e:
            error_msg = f"Portfolio {portfolio_id}: Erro inesperado: {str(e)}"
            Log.error(error_msg)
            return portfolio_id, False, error_msg
    
    def get_investor_class_description(self, class_code: int) -> str:
        """Retorna descrição da classe de investidor."""
        class_options = self.quoteholder_config.get("class_investor_options", {})
        return class_options.get(str(class_code), f"Classe {class_code}")
    
    def list_investor_classes(self) -> Dict[str, str]:
        """Lista todas as classes de investidor disponíveis."""
        return self.quoteholder_config.get("class_investor_options", {})

# Funções utilitárias para compatibilidade

def process_single_quoteholder_report(
    portfolio_id: str,
    config_file: str,
    report_date: datetime,
    output_dir: str,
    report_format: str = "PDF",
    **kwargs
) -> Tuple[str, bool, str]:
    """
    Função utilitária para processar um único relatório de cotistas.
    
    Args:
        portfolio_id: ID da carteira
        config_file: Caminho para arquivo de configuração
        report_date: Data do relatório
        output_dir: Diretório de saída
        report_format: Formato do relatório
        **kwargs: Parâmetros adicionais
        
    Returns:
        Tuple[portfolio_id, success, message]
    """
    processor = QuoteholderReportProcessor(config_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    return processor.process_single_quoteholder_report(
        portfolio_id=portfolio_id,
        report_date=report_date,
        output_dir=output_path,
        report_format=report_format,
        **kwargs
    )

def process_quoteholder_reports_batch(
    portfolio_ids: List[str],
    config_file: str,
    report_date: datetime,
    output_dir: str,
    report_format: str = "PDF",
    max_workers: int = 1,
    **kwargs
) -> Dict[str, List]:
    """
    Processa múltiplos relatórios de cotistas em lote.
    
    Args:
        portfolio_ids: Lista de IDs de carteira
        config_file: Caminho para arquivo de configuração
        report_date: Data do relatório
        output_dir: Diretório de saída
        report_format: Formato do relatório
        max_workers: Número de workers simultâneos
        **kwargs: Parâmetros adicionais
        
    Returns:
        Dicionário com resultados categorizados
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    processor = QuoteholderReportProcessor(config_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    total_portfolios = len(portfolio_ids)
    processed = 0
    
    Log.info(f"Iniciando processamento de {total_portfolios} relatórios de cotistas...")
    Log.info(f"Diretório de saída: {output_path.absolute()}")
    Log.info(f"Data do relatório: {report_date.strftime('%Y-%m-%d')}")
    Log.info(f"Formato: {report_format}")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter tarefas
        future_to_portfolio = {
            executor.submit(
                processor.process_single_quoteholder_report,
                portfolio_id,
                report_date,
                output_path,
                report_format,
                **kwargs
            ): portfolio_id for portfolio_id in portfolio_ids
        }
        
        # Processar resultados
        for future in as_completed(future_to_portfolio):
            portfolio_id = future_to_portfolio[future]
            processed += 1
            
            try:
                result_portfolio_id, success, message = future.result()
                fund_name = processor.config.get_portfolio_name(result_portfolio_id)
                
                if success:
                    if "Skipped" in message:
                        results['skipped'].append({
                            'portfolio_id': result_portfolio_id,
                            'fund_name': fund_name,
                            'message': message
                        })
                    else:
                        results['success'].append({
                            'portfolio_id': result_portfolio_id,
                            'fund_name': fund_name,
                            'message': message
                        })
                else:
                    results['failed'].append({
                        'portfolio_id': result_portfolio_id,
                        'fund_name': fund_name,
                        'message': message
                    })
            
            except Exception as e:
                error_msg = f"Erro ao processar resultado: {str(e)}"
                Log.error(error_msg)
                results['failed'].append({
                    'portfolio_id': portfolio_id,
                    'fund_name': processor.config.get_portfolio_name(portfolio_id),
                    'message': error_msg
                })
            
            # Log de progresso
            if processed % 10 == 0 or processed == total_portfolios:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = total_portfolios - processed
                eta = remaining / rate if rate > 0 else 0
                
                Log.info(f"Progresso: {processed}/{total_portfolios} "
                       f"({(processed/total_portfolios)*100:.1f}%) - "
                       f"Taxa: {rate:.2f}/s - ETA: {eta:.0f}s")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Log final
    success_count = len(results['success'])
    failed_count = len(results['failed'])
    skipped_count = len(results['skipped'])
    
    Log.info(f"\n{'='*60}")
    Log.info(f"RESUMO - RELATÓRIOS DE COTISTAS")
    Log.info(f"{'='*60}")
    Log.info(f"Total processados: {total_portfolios}")
    Log.info(f"Sucessos: {success_count}")
    Log.info(f"Falhas: {failed_count}")
    Log.info(f"Ignorados: {skipped_count}")
    Log.info(f"Tempo total: {total_time:.2f}s")
    Log.info(f"Taxa média: {total_portfolios/total_time:.2f} portfolios/s")
    Log.info(f"{'='*60}")
    
    return results

if __name__ == "__main__":
    # Exemplo de uso
    from datetime import date
    
    # Teste com um portfolio
    config_file = "portfolios.json"
    report_date = datetime.combine(date(2025, 7, 29), datetime.min.time())
    output_dir = "./quoteholder_reports"
    
    print("Testando relatório de cotistas...")
    result = process_single_quoteholder_report(
        portfolio_id="4471709",
        config_file=config_file,
        report_date=report_date,
        output_dir=output_dir,
        report_format="PDF"
    )
    
    portfolio_id, success, message = result
    print(f"Portfolio {portfolio_id}: {'✅' if success else '❌'} {message}")