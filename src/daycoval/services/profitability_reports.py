#!/usr/bin/env python3
"""
Serviço para relatórios de rentabilidade (endpoints 1048 e 1799).
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests

from ..core.client import APIClient
from ..core.models import (
    ReportResponse, Portfolio, ReportFormat, DEFAULT_ALL_PORTFOLIOS_LABEL,
    ProfitabilityRequest, BankStatementRequest
)
from ..core.exceptions import APIError, ValidationError, ReportProcessingError, EmptyReportError, TimeoutError
from ..utils.file_utils import sanitize_filename

logger = logging.getLogger(__name__)


class ProfitabilityReportService:
    """Serviço para relatórios de rentabilidade."""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    def _parse_response(
        self,
        response: requests.Response,
        request,
        endpoint: str
    ) -> ReportResponse:
        """Converte resposta HTTP em modelo estruturado."""
        content_type = response.headers.get('Content-Type', '').lower()
        
        # LOGGING AGRESSIVO para debugging conforme recomendação do Gemini
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Content-Type recebido: {content_type}")
        logger.info(f"Headers da resposta: {dict(response.headers)}")
        
        # Log das primeiras linhas da resposta para identificar erros
        if response.content:
            try:
                preview = response.content[:500].decode('utf-8', errors='ignore')
                logger.info(f"Preview do conteúdo (500 chars): {repr(preview)}")
            except:
                logger.info(f"Conteúdo binário, tamanho: {len(response.content)} bytes")
        
        # VALIDAÇÃO POR STATUS CODE primeiro
        if response.status_code != 200:
            error_body = response.text if hasattr(response, 'text') else str(response.content[:1000])
            raise APIError(f"API retornou status {response.status_code}: {error_body}")
        
        # Determinar se conteúdo é binário ou texto
        if request.format == ReportFormat.PDF or 'application/pdf' in content_type:
            content = response.content
            content_type = 'application/pdf'
            
            # VALIDAÇÃO MELHORADA DE PDF
            if not content or len(content) == 0:
                raise EmptyReportError("Resposta vazia recebida da API")
            
            if not content.startswith(b'%PDF'):
                # Se não é PDF, pode ser erro em formato texto - vamos logar
                try:
                    error_text = content.decode('utf-8', errors='ignore')[:1000]
                    logger.error(f"Conteúdo recebido não é PDF válido. Conteúdo: {error_text}")
                    raise EmptyReportError(f"API retornou erro em vez de PDF: {error_text}")
                except:
                    raise EmptyReportError("PDF inválido ou vazio recebido")
            
            if len(content) < 1000:
                logger.warning(f"PDF muito pequeno: {len(content)} bytes")
                raise EmptyReportError(f"PDF muito pequeno ({len(content)} bytes) - possível erro da API")
                
        else:
            content = response.text
            if 'application/json' in content_type:
                content_type = 'application/json'
                
                # Verificar se é mensagem de "em processamento"
                try:
                    import json
                    json_data = json.loads(content)
                    if isinstance(json_data, dict):
                        metadata = json_data.get('metadata', {})
                        if metadata.get('type') == -100:
                            message = metadata.get('message', 'Relatório em processamento')
                            raise ReportProcessingError(f"Relatório ainda em processamento: {message}")
                except json.JSONDecodeError:
                    pass
                    
            elif request.format.is_csv:
                content_type = 'text/csv'
                
                # Validar CSV
                if not content.strip() or len(content.strip().split('\n')) < 2:
                    raise EmptyReportError("CSV vazio ou inválido recebido")
                    
            else:
                content_type = 'text/plain'
                
                # Validar texto geral
                if not content.strip():
                    raise EmptyReportError("Conteúdo vazio recebido")
        
        # CORREÇÃO: Usar função padrão para gerar nome do arquivo
        from ..utils.file_utils import generate_filename
        
        # Determinar prefixo baseado no endpoint
        if endpoint == "1048":
            report_type = "RENTABILIDADE_SINTETICA"
        elif endpoint == "1799":
            report_type = "RENTABILIDADE"
        else:
            report_type = "RELATORIO"
        
        # Usar a função padrão que já consulta CADFUN
        # Se portfolio for None (todos os portfolios), usar nome genérico
        portfolio_name = request.portfolio.name if request.portfolio else DEFAULT_ALL_PORTFOLIOS_LABEL
        filename = generate_filename(
            portfolio_name=portfolio_name,
            date=request.date if hasattr(request, 'date') and request.date else datetime.now(),
            format=request.format,
            report_type=report_type
        )
        
        return ReportResponse(
            content=content,
            content_type=content_type,
            filename=filename,
            portfolio=request.portfolio,
            date=request.date if hasattr(request, 'date') else datetime.now(),
            format=request.format,
            size_bytes=0,  # Será calculado automaticamente
            request_params=request.to_api_params()
        )
    
    def get_synthetic_profitability_report_sync(self, request) -> ReportResponse:
        """Versão síncrona do relatório sintético."""
        portfolio_info = f"{request.portfolio.id}" if request.portfolio else DEFAULT_ALL_PORTFOLIOS_LABEL
        logger.info(f"Buscando relatório de rentabilidade sintética para {portfolio_info}")
        
        try:
            response = self.client.post_sync(
                "/report/reports/1048",
                request.to_api_params()
            )
            
            report_response = self._parse_response(response, request, "1048")
            
            logger.info(f"Relatório sintético obtido com sucesso: {report_response.size_mb:.2f} MB")
            return report_response
            
        except Exception as e:
            logger.error(f"Erro ao obter relatório sintético para {portfolio_info}: {e}")
            raise
    
    def get_profitability_report_sync(self, request) -> ReportResponse:
        """Versão síncrona do relatório de rentabilidade."""
        logger.info(f"Buscando relatório de rentabilidade para {request.portfolio.id}")
        
        try:
            response = self.client.post_sync(
                "/report/reports/1799",
                request.to_api_params()
            )
            
            report_response = self._parse_response(response, request, "1799")
            
            logger.info(f"Relatório de rentabilidade obtido com sucesso: {report_response.size_mb:.2f} MB")
            return report_response
            
        except Exception as e:
            logger.error(f"Erro ao obter relatório de rentabilidade para {request.portfolio.id}: {e}")
            raise
    
    def get_bank_statement_report_sync(self, request) -> ReportResponse:
        """Obter relatório de Extrato Conta Corrente (endpoint 1988) de forma síncrona."""
        logger.info(f"Buscando extrato conta corrente para carteira {request.portfolio.id}")
        
        try:
            response = self.client.post_sync(
                "/report/reports/1988",
                request.to_api_params()
            )
            
            report_response = self._parse_response(response, request, "1988")
            
            logger.info(f"Extrato conta corrente obtido com sucesso: {report_response.size_mb:.2f} MB")
            return report_response
            
        except Exception as e:
            logger.error(f"Erro ao obter extrato conta corrente para {request.portfolio.id}: {e}")
            raise
    
    def save_report(self, report: ReportResponse, output_dir: Path) -> bool:
        """Salva relatório em arquivo."""
        try:
            file_path = output_dir / report.filename
            success = report.save_to_file(file_path)
            
            if success:
                logger.info(f"Relatório salvo: {file_path}")
            else:
                logger.error(f"Erro ao salvar relatório: {file_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao salvar relatório {report.filename}: {e}")
            return False
    
    def save_multiple_reports(
        self,
        reports: List[ReportResponse],
        output_dir: Path
    ) -> tuple[int, int]:
        """Salva múltiplos relatórios."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        successful = 0
        failed = 0
        
        for report in reports:
            if self.save_report(report, output_dir):
                successful += 1
            else:
                failed += 1
        
        logger.info(f"Salvos {successful} relatórios, {failed} falharam")
        return successful, failed
    
    def consolidate_csv_reports(
        reports: List[ReportResponse], 
        output_path: Path,
        consolidation_type: str = "rentabilidade"
    ) -> bool:
        """
        Consolida múltiplos CSVs em um único arquivo.
        
        Args:
            reports: Lista de relatórios em formato CSV
            output_path: Caminho do arquivo consolidado
            consolidation_type: Tipo de consolidação (rentabilidade, sintetica)
        
        Returns:
            bool: Sucesso da operação
        """
        try:
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
            logger.error(f"❌ Erro na consolidação: {e}")
            return False


# Função de conveniência para compatibilidade
def create_profitability_service() -> ProfitabilityReportService:
    """Cria instância do serviço com configurações padrão."""
    from ..config.settings import get_settings
    from ..core.client import APIClient
    
    settings = get_settings()
    client = APIClient(settings.api)
    return ProfitabilityReportService(client)