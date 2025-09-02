"""
Serviço para relatórios de carteira diária (endpoint 32).
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import requests

from ..core.client import APIClient
from ..core.models import (
    DailyReportRequest, ReportResponse, Portfolio, ReportFormat, ReportType
)
from ..core.exceptions import APIError, ValidationError, ReportProcessingError, EmptyReportError, TimeoutError
from ..utils.file_utils import sanitize_filename, generate_filename

logger = logging.getLogger(__name__)


class DailyReportService:
    """Serviço para relatórios de carteira diária."""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    def _create_request(
        self,
        portfolio: Portfolio,
        date: datetime,
        format: ReportFormat,
        **kwargs
    ) -> DailyReportRequest:
        """Cria requisição para relatório diário."""
        return DailyReportRequest(
            portfolio=portfolio,
            date=date,
            format=format,
            report_type=ReportType.DAILY,
            **kwargs
        )
    
    def _parse_response(
        self,
        response: requests.Response,
        request: DailyReportRequest
    ) -> ReportResponse:
        """Converte resposta HTTP em modelo estruturado."""
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Determinar se conteúdo é binário ou texto
        if request.format == ReportFormat.PDF or 'application/pdf' in content_type:
            content = response.content
            content_type = 'application/pdf'
            
            # Validar PDF - deve começar com %PDF e ter tamanho mínimo
            if not content.startswith(b'%PDF') or len(content) < 1000:
                raise EmptyReportError("PDF inválido ou vazio recebido")
                
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
                    pass  # Não é JSON válido, continuar
                    
            elif request.format.is_csv:
                content_type = 'text/csv'
                
                # Validar CSV - deve ter pelo menos cabeçalho
                if not content.strip() or len(content.strip().split('\n')) < 2:
                    raise EmptyReportError("CSV vazio ou inválido recebido")
                    
            else:
                content_type = 'text/plain'
                
                # Validar texto geral
                if not content.strip():
                    raise EmptyReportError("Conteúdo vazio recebido")
        
        # Gerar nome do arquivo
        filename = generate_filename(
            portfolio_name=request.portfolio.name,
            date=request.date,
            format=request.format
        )
        
        return ReportResponse(
            content=content,
            content_type=content_type,
            filename=filename,
            portfolio=request.portfolio,
            date=request.date,
            format=request.format,
            size_bytes=0,  # Será calculado automaticamente
            request_params=request.to_api_params()
        )
    
    async def get_report(self, request: DailyReportRequest) -> ReportResponse:
        """Obtém relatório diário de forma assíncrona."""
        logger.info(f"Buscando relatório diário para {request.portfolio.id} em {request.date.strftime('%Y-%m-%d')}")
        
        try:
            # Fazer requisição
            response = await self.client.post(
                "/report/reports/32",
                request.to_api_params()
            )
            
            # Processar resposta
            report_response = self._parse_response(response, request)
            
            logger.info(f"Relatório obtido com sucesso: {report_response.size_mb:.2f} MB")
            return report_response
            
        except Exception as e:
            logger.error(f"Erro ao obter relatório para {request.portfolio.id}: {e}")
            raise
    
    def get_report_sync(self, request: DailyReportRequest) -> ReportResponse:
        """Obtém relatório diário de forma síncrona."""
        logger.info(f"Buscando relatório diário para {request.portfolio.id} em {request.date.strftime('%Y-%m-%d')}")
        
        try:
            # Fazer requisição síncrona
            response = self.client.post_sync(
                "/report/reports/32",
                request.to_api_params()
            )
            
            # Processar resposta
            report_response = self._parse_response(response, request)
            
            logger.info(f"Relatório obtido com sucesso: {report_response.size_mb:.2f} MB")
            return report_response
            
        except Exception as e:
            logger.error(f"Erro ao obter relatório para {request.portfolio.id}: {e}")
            raise
    
    async def get_multiple_reports(
        self,
        portfolios: List[Portfolio],
        date: datetime,
        format: ReportFormat,
        **kwargs
    ) -> List[ReportResponse]:
        """Obtém múltiplos relatórios de forma assíncrona."""
        import asyncio
        
        tasks = []
        for portfolio in portfolios:
            request = self._create_request(portfolio, date, format, **kwargs)
            task = self.get_report(request)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separar sucessos de erros
        successful_reports = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Erro no portfolio {portfolios[i].id}: {result}")
            else:
                successful_reports.append(result)
        
        return successful_reports
    
    def get_multiple_reports_sync(
        self,
        portfolios: List[Portfolio],
        date: datetime,
        format: ReportFormat,
        **kwargs
    ) -> List[ReportResponse]:
        """Obtém múltiplos relatórios de forma síncrona."""
        results = []
        
        for portfolio in portfolios:
            try:
                request = self._create_request(portfolio, date, format, **kwargs)
                result = self.get_report_sync(request)
                results.append(result)
            except Exception as e:
                logger.error(f"Erro no portfolio {portfolio.id}: {e}")
                # Continue com os próximos
        
        return results
    
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


# Função de conveniência para compatibilidade
def create_daily_report_service() -> DailyReportService:
    """Cria instância do serviço com configurações padrão."""
    from ..config.settings import get_settings
    from ..core.client import APIClient
    
    settings = get_settings()
    client = APIClient(settings.api)
    return DailyReportService(client)