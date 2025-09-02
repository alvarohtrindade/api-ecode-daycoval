import requests
import json
import re
import csv
import os
import time
import random
import sys
from io import StringIO
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logging_utils import Log
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("APIKEY_GESTOR")
BASE_URL = os.getenv("PROD_URL")

class PortfolioConfig:
    """Classe para gerenciar configurações de carteiras."""
    
    def __init__(self, config_file: str = "portfolios.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo JSON."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_file}")
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao ler arquivo JSON: {e}")
    
    def get_portfolio_name(self, portfolio_id: str) -> str:
        """Retorna o nome do fundo baseado no ID da carteira."""
        portfolio_id = str(portfolio_id).strip()
        portfolios = self.config.get("portfolios", {})
        return portfolios.get(portfolio_id, self.config["metadata"]["default_fund_name"])
    
    def get_all_portfolios(self) -> Dict[str, str]:
        """Retorna todos os portfolios mapeados."""
        return self.config.get("portfolios", {})
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Retorna configurações de rate limiting."""
        return self.config["metadata"]["rate_limit"]

class RateLimiter:
    """Implementa rate limiting com exponential backoff."""
    
    def __init__(self, max_calls: int = 30, period: int = 60, backoff_factor: float = 2):
        self.max_calls = max_calls
        self.period = period
        self.backoff_factor = backoff_factor
        self.calls = []
        self.last_reset = time.time()
    
    def _cleanup_old_calls(self):
        """Remove chamadas antigas da lista."""
        current_time = time.time()
        self.calls = [call_time for call_time in self.calls 
                     if current_time - call_time < self.period]
    
    def can_make_call(self) -> bool:
        """Verifica se pode fazer uma chamada."""
        self._cleanup_old_calls()
        return len(self.calls) < self.max_calls
    
    def wait_if_needed(self):
        """Aguarda se necessário para respeitar rate limit."""
        self._cleanup_old_calls()
        
        if len(self.calls) >= self.max_calls:
            # Calcula tempo de espera baseado na chamada mais antiga
            oldest_call = min(self.calls)
            wait_time = self.period - (time.time() - oldest_call)
            
            if wait_time > 0:
                # Adiciona um pouco de jitter para evitar thundering herd
                jitter = random.uniform(0.1, 0.5)
                total_wait = wait_time + jitter
                
                Log.info(f"Rate limit atingido. Aguardando {total_wait:.2f} segundos...")
                time.sleep(total_wait)
                self._cleanup_old_calls()
    
    def record_call(self):
        """Registra uma chamada."""
        self.calls.append(time.time())

def create_session_with_retries(rate_limit_config: Dict[str, Any]) -> requests.Session:
    """Cria uma sessão requests com retry automático e rate limiting."""
    session = requests.Session()
    
    # Configurar retry strategy
    retry_strategy = Retry(
        total=rate_limit_config["max_retries"],
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=rate_limit_config["backoff_factor"],
        respect_retry_after_header=True
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def sanitize_filename(filename: str) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres inválidos e aplicando regras específicas.
    
    Args:
        filename: Nome original do arquivo
        
    Returns:
        Nome sanitizado compatível com sistemas de arquivo
    """
    import unicodedata
    
    # Normalizar unicode (remover acentos)
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ASCII', 'ignore').decode('ASCII')
    
    # Converter para maiúsculas
    filename = filename.upper()
    
    # Remover caracteres inválidos para nomes de arquivo
    invalid_chars = r'<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Substituir espaços e outros separadores por underscore
    filename = re.sub(r'[\s\-\.\(\)\[\]]+', '_', filename)
    
    # Remover caracteres não alfanuméricos exceto underscore
    filename = re.sub(r'[^\w_]', '_', filename)
    
    # Remover underscores consecutivos
    filename = re.sub(r'_+', '_', filename)
    
    # Remover underscores no início e fim
    filename = filename.strip('_')
    
    # Garantir que não está vazio
    if not filename:
        filename = 'ARQUIVO_SEM_NOME'
    
    # Limitar tamanho (max 100 caracteres para compatibilidade)
    if len(filename) > 100:
        filename = filename[:100].rstrip('_')
    
    return filename

def clean_text_data(content, file_format):
    """
    Limpa os dados de texto removendo espaços excessivos e formatando adequadamente
    """
    if not isinstance(content, str):
        return content
    
    # Para formatos CSV/TXT, aplicar limpeza de espaços
    if file_format.upper() in ['CSV', 'CSVBR', 'CSVUS', 'TXT', 'TXTBR']:
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if line.strip():  # Pular linhas vazias
                # Se for CSV (separado por ; ou ,), limpar cada campo
                if ';' in line or ',' in line:
                    delimiter = ';' if ';' in line else ','
                    fields = line.split(delimiter)
                    # Remover espaços extras de cada campo, mas preservar a estrutura
                    cleaned_fields = [field.strip() for field in fields]
                    cleaned_lines.append(delimiter.join(cleaned_fields))
                else:
                    # Para outros formatos, aplicar limpeza mais geral
                    # Remover múltiplos espaços consecutivos
                    cleaned_line = re.sub(r'\s+', ' ', line.strip())
                    cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    return content

def format_csv_data(content, delimiter=';'):
    """
    Formata dados CSV para melhor legibilidade, removendo espaços desnecessários
    """
    try:
        # Usar StringIO para tratar o conteúdo como arquivo
        csv_file = StringIO(content)
        csv_reader = csv.reader(csv_file, delimiter=delimiter)
        
        formatted_rows = []
        for row in csv_reader:
            # Limpar cada campo da linha
            cleaned_row = [field.strip() for field in row]
            formatted_rows.append(cleaned_row)
        
        # Recriar o CSV com os dados limpos
        output = StringIO()
        csv_writer = csv.writer(output, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerows(formatted_rows)
        
        return output.getvalue()
    except Exception as e:
        Log.warning(f"Erro ao formatar CSV: {e}. Retornando conteúdo original.")
        return content

def fetch_daily_report_with_retry(
    report_date, 
    report_format, 
    portfolio=None, 
    clean_data=True,
    rate_limiter: Optional[RateLimiter] = None,
    session: Optional[requests.Session] = None
) -> Tuple[Dict[str, Any], bool]:
    """
    Obtém o relatório diário com retry automático e rate limiting.
    
    Returns:
        Tuple[Dict, bool]: (dados_do_relatorio, sucesso)
    """
    # Validação dos parâmetros
    if report_date is None:
        raise ValueError("report_date não pode ser None")
    if report_format is None:
        raise ValueError("report_format não pode ser None")
    
    # Usar rate limiter se fornecido
    if rate_limiter:
        rate_limiter.wait_if_needed()
        rate_limiter.record_call()
    
    # Usar sessão fornecida ou criar uma nova
    if session is None:
        session = requests.Session()
    
    try:
        endpoint = f"{BASE_URL}/report/reports/32"
        headers = {
            "apikey": API_KEY,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        body = {
            "format": report_format,
            "date": report_date.strftime('%Y-%m-%d'),
            "breakLevel": 1,
            "leftReportName": False,
            "omitLogotype": False,
            "detailFixedIncome": True,
            "detailNetWorth": False,
            "showInvestorQty": True,
            "showMarketZeroedSecurity": True,
            "consolidatedRC12": False,
            "showUntilMaturityMark": False,
            "considersCompensation": False,
            "detailsCompensation": False,
            "showTwoRentabilities": False,
            "showQuotaWithoutAmortization": False,
            "showQuotaBeforeAmortization": False,
            "showNetWorthPercentual": False
        }

        # Adiciona o portfolio apenas se estiver definido
        if portfolio is not None:
            body["portfolio"] = portfolio

        response = session.post(endpoint, headers=headers, json=body, timeout=30)
        
        # Debug: Imprimir informações da resposta
        Log.info(f"Portfolio {portfolio}: Status Code: {response.status_code}")
        Log.info(f"Portfolio {portfolio}: Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        response.raise_for_status()
        
        # Verificar o tipo de conteúdo - MELHORADO para priorizar formato solicitado
        content_type = response.headers.get('Content-Type', '').lower()
        requested_format = report_format.upper()
        
        # Para PDF - verificar se realmente é PDF
        if requested_format == 'PDF':
            # Verificar se o conteúdo começa com header PDF
            if response.content.startswith(b'%PDF'):
                Log.info(f"Portfolio {portfolio}: Resposta é um PDF válido - retornando conteúdo binário")
                return {
                    'content': response.content,
                    'content_type': 'application/pdf',
                    'portfolio': portfolio,
                    'date': body['date'],
                    'format': requested_format
                }, True
            else:
                Log.warning(f"Portfolio {portfolio}: Formato PDF solicitado mas conteúdo não é PDF válido")
        
        # Para formatos CSV
        elif requested_format in ['CSVBR', 'CSVUS', 'CSV']:
            Log.info(f"Portfolio {portfolio}: Processando como CSV - limpando conteúdo")
            content = response.text
            
            if clean_data:
                content = format_csv_data(content, delimiter=';')
                Log.info(f"Portfolio {portfolio}: Dados CSV limpos e formatados")
            
            return {
                'content': content,
                'content_type': 'text/csv',
                'portfolio': portfolio,
                'date': body['date'],
                'format': requested_format,
                'cleaned': clean_data
            }, True
        
        # Para formatos TXT
        elif requested_format in ['TXTBR', 'TXTUS', 'TXT']:
            Log.info(f"Portfolio {portfolio}: Processando como TXT")
            content = response.text
            
            if clean_data:
                content = clean_text_data(content, requested_format)
                Log.info(f"Portfolio {portfolio}: Dados TXT limpos")
            
            return {
                'content': content,
                'content_type': 'text/plain',
                'portfolio': portfolio,
                'date': body['date'],
                'format': requested_format,
                'cleaned': clean_data
            }, True
        
        # Para JSON
        elif requested_format == 'JSON':
            try:
                json_content = response.json()
                Log.info(f"Portfolio {portfolio}: Resposta JSON processada")
                return {
                    'content': json.dumps(json_content, indent=2, ensure_ascii=False),
                    'content_type': 'application/json',
                    'portfolio': portfolio,
                    'date': body['date'],
                    'format': requested_format,
                    'data': json_content
                }, True
            except json.JSONDecodeError as json_error:
                Log.error(f"Portfolio {portfolio}: Erro ao fazer parse do JSON: {json_error}")
                return {}, False
        
        # Fallback: tentar detectar pelo Content-Type se o formato solicitado falhou
        else:
            Log.warning(f"Portfolio {portfolio}: Formato {requested_format} não reconhecido, tentando detectar pelo Content-Type")
            
            if 'application/pdf' in content_type:
                return {
                    'content': response.content,
                    'content_type': 'application/pdf',
                    'portfolio': portfolio,
                    'date': body['date'],
                    'format': 'PDF'
                }, True
            elif 'csv' in content_type or 'text' in content_type:
                content = response.text
                if clean_data:
                    content = clean_text_data(content, 'TXT')
                
                return {
                    'content': content,
                    'content_type': content_type,
                    'portfolio': portfolio,
                    'date': body['date'],
                    'format': 'TXT',
                    'cleaned': clean_data
                }, True
            else:
                # Último recurso - retornar como texto
                return {
                    'content': response.text,
                    'content_type': content_type,
                    'portfolio': portfolio,
                    'date': body['date'],
                    'format': 'TXT'
                }, True
        
    except requests.exceptions.HTTPError as e:
        Log.error(f"Portfolio {portfolio}: Erro HTTP: {e}")
        if hasattr(e, 'response'):
            Log.error(f"Portfolio {portfolio}: Status Code: {e.response.status_code}")
            Log.error(f"Portfolio {portfolio}: Response: {e.response.text}")
        return {}, False
    except requests.exceptions.RequestException as e:
        Log.error(f"Portfolio {portfolio}: Erro na requisição: {e}")
        return {}, False
    except Exception as e:
        Log.error(f"Portfolio {portfolio}: Erro inesperado: {e}")
        return {}, False

# Mantém a função original para compatibilidade
def fetch_daily_report(report_date, report_format, portfolio=None, clean_data=True):
    """Função original mantida para compatibilidade."""
    result, success = fetch_daily_report_with_retry(
        report_date, report_format, portfolio, clean_data
    )
    if success:
        return result
    else:
        raise Exception(f"Falha ao obter relatório para portfolio {portfolio}")