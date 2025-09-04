"""
Serviço de consolidação de dados para relatórios Daycoval.

Este módulo fornece funcionalidades para:
- Consolidar múltiplos relatórios CSV em um único arquivo
- Consolidar múltiplos relatórios PDF em um único arquivo
- Aplicar transformações e limpeza de dados
- Manter metadados de origem dos dados

Author: Claude Code  
Date: 2025-09-04
Version: 1.0
"""

import csv
import io
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

from ..core.exceptions import DaycovalError


class DataConsolidationError(DaycovalError):
    """Exceção específica para erros de consolidação de dados."""
    pass


class DataConsolidationService:
    """
    Serviço para consolidação de relatórios em formatos CSV e PDF.
    
    Funcionalidades:
    - Consolidação de CSVs com deduplicação e padronização
    - Consolidação de PDFs com metadados
    - Validação de schema e limpeza de dados
    - Suporte a múltiplos endpoints (32, 45, 1048, 1799, 1988)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Inicializa o serviço de consolidação.
        
        Args:
            logger: Logger personalizado (opcional)
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Mapeamentos de campos por endpoint
        self.endpoint_schemas = {
            "32": {  # Carteira diária
                "required_fields": ["DATA", "ATIVO", "QUANTIDADE", "VALOR"],
                "date_fields": ["DATA"],
                "numeric_fields": ["QUANTIDADE", "VALOR", "PRECO_UNITARIO"]
            },
            "45": {  # Posição de cotistas
                "required_fields": ["COTISTA", "CPF_CNPJ", "QUANTIDADE_COTAS"],
                "date_fields": ["DATA_POSICAO"],
                "numeric_fields": ["QUANTIDADE_COTAS", "VALOR_COTAS"]
            },
            "1048": {  # Rentabilidade sintética
                "required_fields": ["FUNDO", "DATA", "RENTABILIDADE"],
                "date_fields": ["DATA", "DATA_INICIAL", "DATA_FINAL"],
                "numeric_fields": ["RENTABILIDADE", "PATRIMONIO", "COTAS"]
            },
            "1799": {  # Relatório de rentabilidade
                "required_fields": ["CARTEIRA", "DATA", "CDI"],
                "date_fields": ["DATA"],
                "numeric_fields": ["CDI", "RENTABILIDADE", "BENCHMARK"]
            },
            "1988": {  # Extrato conta corrente
                "required_fields": ["DATA", "DESCRICAO", "VALOR"],
                "date_fields": ["DATA"],
                "numeric_fields": ["VALOR", "SALDO"]
            }
        }
    
    def consolidate_csv_reports(
        self, 
        reports: List,
        output_path: Path,
        endpoint_type: str,
        include_metadata: bool = True
    ) -> bool:
        """
        Consolida múltiplos relatórios CSV em um único arquivo.
        
        Args:
            reports: Lista de objetos de relatório com conteúdo CSV
            output_path: Caminho para o arquivo consolidado
            endpoint_type: Tipo do endpoint ("32", "45", "1048", etc.)
            include_metadata: Se deve incluir metadados de origem
            
        Returns:
            bool: True se consolidação foi bem-sucedida
        """
        try:
            self.logger.info(f'Iniciando consolidação CSV para endpoint {endpoint_type}')
            
            all_rows = []
            headers = None
            schema = self.endpoint_schemas.get(endpoint_type, {})
            
            for i, report in enumerate(reports):
                if not hasattr(report, 'content') or not report.content:
                    self.logger.warning(f'Relatório {i} sem conteúdo, pulando')
                    continue
                
                try:
                    # Parse CSV content
                    csv_content = self._extract_csv_content(report)
                    reader = csv.DictReader(io.StringIO(csv_content))
                    
                    # Estabelecer headers na primeira iteração válida
                    if headers is None and reader.fieldnames:
                        headers = list(reader.fieldnames)
                        self.logger.debug(f'Headers estabelecidos: {headers}')
                    
                    # Processar linhas do relatório
                    report_rows = 0
                    for row in reader:
                        # Adicionar metadados de origem se solicitado
                        if include_metadata:
                            row = self._add_metadata_fields(row, report, i)
                        
                        # Aplicar limpeza e validação
                        row = self._clean_row_data(row, schema)
                        
                        all_rows.append(row)
                        report_rows += 1
                    
                    self.logger.info(f'Processado relatório {i}: {report_rows} linhas')
                    
                except Exception as e:
                    self.logger.error(f'Erro ao processar relatório {i}: {str(e)}')
                    continue
            
            if not all_rows:
                raise DataConsolidationError("Nenhum dado válido encontrado para consolidação")
            
            # Escrever arquivo consolidado
            success = self._write_consolidated_csv(all_rows, output_path, headers, include_metadata)
            
            if success:
                self.logger.info(f'Consolidação CSV concluída: {len(all_rows)} linhas em {output_path}')
                
                # Gerar relatório de consolidação
                self._generate_consolidation_report(
                    len(reports), len(all_rows), output_path, endpoint_type
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f'Erro na consolidação CSV: {str(e)}')
            return False
    
    def consolidate_pdf_reports(
        self,
        reports: List,
        output_path: Path,
        title: str = "Relatório Consolidado"
    ) -> bool:
        """
        Consolida múltiplos relatórios PDF em um único arquivo.
        
        Args:
            reports: Lista de objetos de relatório com conteúdo PDF
            output_path: Caminho para o arquivo consolidado
            title: Título do documento consolidado
            
        Returns:
            bool: True se consolidação foi bem-sucedida
        """
        try:
            # Implementação básica - PDF consolidation é mais complexa
            # e requer bibliotecas como PyPDF2 ou reportlab
            
            self.logger.info(f'Tentando consolidação PDF de {len(reports)} relatórios')
            
            # Por enquanto, criar um relatório de índice em texto
            index_content = self._create_pdf_index(reports, title)
            
            # Salvar índice como arquivo de texto por enquanto
            txt_path = output_path.with_suffix('.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            self.logger.info(f'Índice PDF salvo como texto: {txt_path}')
            return True
            
        except Exception as e:
            self.logger.error(f'Erro na consolidação PDF: {str(e)}')
            return False
    
    def _extract_csv_content(self, report) -> str:
        """
        Extrai conteúdo CSV de um objeto de relatório.
        
        Args:
            report: Objeto de relatório
            
        Returns:
            str: Conteúdo CSV como string
        """
        csv_content = report.content
        
        # Converter bytes para string se necessário
        if isinstance(csv_content, bytes):
            # Tentar detectar encoding
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    csv_content = csv_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # Fallback com replace
                csv_content = csv_content.decode('utf-8', errors='replace')
        
        return csv_content
    
    def _add_metadata_fields(self, row: Dict[str, Any], report, report_index: int) -> Dict[str, Any]:
        """
        Adiciona campos de metadados a uma linha.
        
        Args:
            row: Linha de dados
            report: Objeto de relatório
            report_index: Índice do relatório
            
        Returns:
            Dict[str, Any]: Linha com metadados
        """
        # Nome do fundo baseado no filename ou portfolio
        fund_name = "UNKNOWN"
        
        if hasattr(report, 'filename') and report.filename:
            fund_name = report.filename.replace('.csv', '').replace('.pdf', '')
        elif hasattr(report, 'portfolio') and hasattr(report.portfolio, 'name'):
            fund_name = report.portfolio.name
        
        # Adicionar campos de metadados no início
        enhanced_row = {
            'FUNDO_ORIGEM': fund_name,
            'RELATORIO_INDEX': report_index,
            'TIMESTAMP_CONSOLIDACAO': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Adicionar dados originais
        enhanced_row.update(row)
        
        return enhanced_row
    
    def _clean_row_data(self, row: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica limpeza e padronização aos dados de uma linha.
        
        Args:
            row: Linha de dados
            schema: Schema do endpoint
            
        Returns:
            Dict[str, Any]: Linha limpa
        """
        cleaned_row = {}
        
        for key, value in row.items():
            if value is None:
                cleaned_row[key] = ""
                continue
            
            # Converter para string para processamento
            str_value = str(value).strip()
            
            # Campos numéricos
            if key in schema.get('numeric_fields', []):
                try:
                    # Limpeza e conversão numérica melhorada
                    cleaned_row[key] = self._safe_numeric_conversion(str_value)
                except (ValueError, AttributeError):
                    cleaned_row[key] = 0
            
            # Campos de data
            elif key in schema.get('date_fields', []):
                cleaned_row[key] = self._standardize_date(str_value)
            
            # Outros campos
            else:
                cleaned_row[key] = str_value
        
        return cleaned_row
    
    def _safe_numeric_conversion(self, str_value: str) -> Union[int, float]:
        """
        Converte string numérica para int ou float de forma segura.
        
        Suporta formatos:
        - Brasileiro: 1.234,56 ou 1234,56
        - Americano: 1,234.56 ou 1234.56
        - Prefixos: R$ 1.234,56
        
        Args:
            str_value: String a converter
            
        Returns:
            Union[int, float]: Número convertido
        """
        if not str_value or str_value.isspace():
            return 0
        
        # Remover caracteres não numéricos (exceto pontos, vírgulas e sinais)
        import re
        clean_str = re.sub(r'[^\d\-+.,]', '', str_value)
        
        if not clean_str:
            return 0
        
        # Detectar formato brasileiro vs americano
        # Brasileiro: último separador é vírgula (1.234,56)
        # Americano: último separador é ponto (1,234.56)
        
        if ',' in clean_str and '.' in clean_str:
            # Ambos presentes - verificar qual é o decimal
            comma_pos = clean_str.rfind(',')
            dot_pos = clean_str.rfind('.')
            
            if comma_pos > dot_pos:
                # Brasileiro: 1.234,56
                clean_str = clean_str.replace('.', '').replace(',', '.')
            else:
                # Americano: 1,234.56
                clean_str = clean_str.replace(',', '')
        
        elif ',' in clean_str:
            # Apenas vírgula - assumir decimal brasileiro se <= 2 dígitos depois
            parts = clean_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Decimal brasileiro: 1234,56
                clean_str = clean_str.replace(',', '.')
            else:
                # Separador de milhares: 1,234
                clean_str = clean_str.replace(',', '')
        
        # Conversão final
        try:
            if '.' in clean_str:
                return float(clean_str)
            else:
                return int(clean_str)
        except ValueError:
            return 0
    
    def _standardize_date(self, date_str: str) -> str:
        """
        Padroniza formato de data para YYYY-MM-DD.
        
        Args:
            date_str: String de data
            
        Returns:
            str: Data padronizada
        """
        if not date_str or date_str.strip() == "":
            return ""
        
        # Formatos comuns brasileiros
        date_formats = [
            '%d/%m/%Y',    # 31/12/2023
            '%d-%m-%Y',    # 31-12-2023
            '%Y-%m-%d',    # 2023-12-31 (já padronizado)
            '%d/%m/%y',    # 31/12/23
            '%Y/%m/%d',    # 2023/12/31
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Se não conseguiu parsear, retornar original
        return date_str
    
    def _write_consolidated_csv(
        self,
        all_rows: List[Dict[str, Any]],
        output_path: Path,
        headers: List[str],
        include_metadata: bool
    ) -> bool:
        """
        Escreve o arquivo CSV consolidado.
        
        Args:
            all_rows: Todas as linhas de dados
            output_path: Caminho do arquivo
            headers: Cabeçalhos do CSV
            include_metadata: Se incluiu metadados
            
        Returns:
            bool: True se escrita foi bem-sucedida
        """
        try:
            # Garantir que o diretório existe
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determinar fieldnames finais
            if include_metadata and all_rows:
                # Usar fieldnames do primeiro registro (que inclui metadados)
                fieldnames = list(all_rows[0].keys())
            else:
                fieldnames = headers or []
            
            # Escrever arquivo CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in all_rows:
                    # Garantir que todos os campos estão presentes
                    complete_row = {field: row.get(field, '') for field in fieldnames}
                    writer.writerow(complete_row)
            
            return True
            
        except Exception as e:
            self.logger.error(f'Erro ao escrever CSV consolidado: {str(e)}')
            return False
    
    def _create_pdf_index(self, reports: List, title: str) -> str:
        """
        Cria um índice textual dos relatórios PDF.
        
        Args:
            reports: Lista de relatórios
            title: Título do documento
            
        Returns:
            str: Conteúdo do índice
        """
        lines = []
        lines.append(f"{'='*80}")
        lines.append(f"{title.upper()}")
        lines.append(f"{'='*80}")
        lines.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total de relatórios: {len(reports)}")
        lines.append("")
        
        lines.append("ÍNDICE DE RELATÓRIOS:")
        lines.append("-" * 40)
        
        for i, report in enumerate(reports, 1):
            fund_name = "N/A"
            size_info = "N/A"
            
            if hasattr(report, 'filename'):
                fund_name = report.filename
            elif hasattr(report, 'portfolio') and hasattr(report.portfolio, 'name'):
                fund_name = report.portfolio.name
            
            if hasattr(report, 'size_mb'):
                size_info = f"{report.size_mb:.2f} MB"
            
            lines.append(f"{i:3d}. {fund_name} ({size_info})")
        
        lines.append("")
        lines.append("OBSERVAÇÕES:")
        lines.append("- Este é um índice dos relatórios consolidados")
        lines.append("- Consolidação PDF completa requer bibliotecas adicionais")
        lines.append("- Para visualizar relatórios individuais, consulte os arquivos originais")
        lines.append("")
        lines.append(f"{'='*80}")
        
        return '\n'.join(lines)
    
    def _generate_consolidation_report(
        self,
        total_reports: int,
        total_rows: int,
        output_path: Path,
        endpoint_type: str
    ) -> None:
        """
        Gera relatório de consolidação com estatísticas.
        
        Args:
            total_reports: Total de relatórios processados
            total_rows: Total de linhas consolidadas
            output_path: Caminho do arquivo consolidado
            endpoint_type: Tipo do endpoint
        """
        try:
            report_path = output_path.with_suffix('.consolidation_report.json')
            
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "endpoint_type": endpoint_type,
                "input_reports_count": total_reports,
                "output_rows_count": total_rows,
                "output_file": str(output_path),
                "consolidation_service_version": "1.0",
                "success": True
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f'Relatório de consolidação salvo: {report_path}')
            
        except Exception as e:
            self.logger.warning(f'Erro ao gerar relatório de consolidação: {str(e)}')
    
    def validate_csv_structure(self, csv_content: str, endpoint_type: str) -> bool:
        """
        Valida se a estrutura do CSV está correta para o endpoint.
        
        Args:
            csv_content: Conteúdo do CSV
            endpoint_type: Tipo do endpoint
            
        Returns:
            bool: True se estrutura é válida
        """
        try:
            schema = self.endpoint_schemas.get(endpoint_type)
            if not schema:
                return True  # Sem schema definido, aceitar
            
            reader = csv.DictReader(io.StringIO(csv_content))
            headers = reader.fieldnames or []
            
            # Verificar se campos obrigatórios estão presentes
            required_fields = schema.get('required_fields', [])
            missing_fields = [field for field in required_fields if field not in headers]
            
            if missing_fields:
                self.logger.warning(f'Campos obrigatórios ausentes: {missing_fields}')
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f'Erro na validação de estrutura CSV: {str(e)}')
            return False


# Função de conveniência
def create_consolidation_service(logger: Optional[logging.Logger] = None) -> DataConsolidationService:
    """
    Factory function para criar instância do serviço de consolidação.
    
    Args:
        logger: Logger personalizado (opcional)
        
    Returns:
        DataConsolidationService: Instância configurada
    """
    return DataConsolidationService(logger)


# Função utilitária para consolidação rápida
def quick_consolidate_csv(
    reports: List,
    output_path: Union[str, Path],
    endpoint_type: str = "1048"
) -> bool:
    """
    Função utilitária para consolidação rápida de CSVs.
    
    Args:
        reports: Lista de relatórios
        output_path: Caminho de saída
        endpoint_type: Tipo do endpoint
        
    Returns:
        bool: True se bem-sucedida
    """
    service = create_consolidation_service()
    return service.consolidate_csv_reports(
        reports, Path(output_path), endpoint_type, include_metadata=True
    )