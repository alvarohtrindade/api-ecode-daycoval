#!/usr/bin/env python3
"""
Gerenciador de diretórios melhorado para estrutura personalizada.
Cria automaticamente a estrutura: F:\\12. Carteira Diária\\Daycoval\\2025\\08 Agosto\\12.08\\
"""

import os
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from utils.logging_utils import Log

class EnhancedDirectoryManager:
    """Gerenciador inteligente de diretórios com estrutura personalizada."""
    
    def __init__(self, base_drive: str = "F:"):
        self.base_drive = base_drive
        self.directory_mappings = {
            32: "12. Carteira Diária",           # Endpoint 32 - Relatórios diários
            45: "13. Posição Cotistas",         # Endpoint 45 - Relatórios de cotistas
            1048: "14. Rentabilidade Sintética", # Endpoint 1048 - Rentabilidade Sintética
            1799: "15. Rentabilidade"           # Endpoint 1799 - Rentabilidade
        }
        self.month_names = {
            1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
            5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
            9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
        }
    
    def build_directory_path(
        self,
        endpoint: int,
        report_date: datetime,
        format_type: str = "PDF",
        is_consolidated: bool = False
    ) -> Path:
        """
        Constrói caminho do diretório seguindo estrutura personalizada.

        Estrutura: F:\\12. Carteira Diária\\Daycoval\\2025\\08 Agosto\\12.08\\PDF\\
        
        Args:
            endpoint: Número do endpoint (32 ou 45)
            report_date: Data do relatório
            format_type: Tipo do formato (PDF, CSV, etc.)
            is_consolidated: Se é arquivo consolidado
            
        Returns:
            Path: Caminho completo do diretório
        """
        # Componentes do caminho
        endpoint_folder = self.directory_mappings.get(endpoint, f"Endpoint_{endpoint}")
        year = str(report_date.year)
        month = self.month_names[report_date.month]
        day = f"{report_date.day:02d}.{report_date.month:02d}"
        
        # Construir caminho base
        base_path = Path(self.base_drive) / endpoint_folder / "Daycoval" / year / month / day
        
        # Adicionar subpasta para formato
        if is_consolidated:
            final_path = base_path / "Consolidado"
        else:
            final_path = base_path / format_type.upper()
        
        return final_path
    
    def create_directory_structure(
        self,
        endpoint: int,
        report_date: datetime,
        formats: List[str],
        create_consolidated: bool = False
    ) -> Dict[str, Path]:
        """
        Cria estrutura completa de diretórios.
        
        Args:
            endpoint: Número do endpoint
            report_date: Data do relatório
            formats: Lista de formatos a criar
            create_consolidated: Se deve criar pasta Consolidado
            
        Returns:
            Dict[str, Path]: Mapeamento {formato: caminho}
        """
        created_paths = {}
        
        try:
            Log.info(f"Criando estrutura de diretórios para endpoint {endpoint}, data {report_date.strftime('%Y-%m-%d')}")
            
            # Criar diretórios para cada formato
            for format_type in formats:
                dir_path = self.build_directory_path(endpoint, report_date, format_type)
                dir_path.mkdir(parents=True, exist_ok=True)
                created_paths[format_type] = dir_path
                Log.debug(f"✅ Criado: {dir_path}")
            
            # Criar pasta consolidado se solicitado
            if create_consolidated:
                consolidated_path = self.build_directory_path(endpoint, report_date, is_consolidated=True)
                consolidated_path.mkdir(parents=True, exist_ok=True)
                created_paths["Consolidado"] = consolidated_path
                Log.debug(f"✅ Consolidado: {consolidated_path}")
            
            Log.info(f"✅ Estrutura criada com {len(created_paths)} diretórios")
            return created_paths
            
        except Exception as e:
            Log.error(f"Erro ao criar estrutura de diretórios: {e}")
            return {}
    
    def clean_day_directory(
        self,
        endpoint: int,
        report_date: datetime,
        confirm: bool = False
    ) -> Tuple[bool, str]:
        """
        Limpa diretório específico do dia.
        
        Args:
            endpoint: Número do endpoint
            report_date: Data do relatório
            confirm: Confirmação de limpeza
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        if not confirm:
            return False, "Limpeza cancelada - confirmação necessária"
        
        try:
            # Obter diretório base do dia
            base_path = self.build_directory_path(endpoint, report_date).parent
            
            if not base_path.exists():
                return True, f"Diretório não existe: {base_path}"
            
            files_removed = 0
            folders_removed = 0
            
            Log.info(f"🧹 Limpando diretório do dia: {base_path}")
            
            # Remover todos os arquivos e subpastas
            for item in base_path.rglob('*'):
                if item.is_file():
                    try:
                        item.unlink()
                        files_removed += 1
                    except Exception as e:
                        Log.warning(f"Erro ao remover arquivo {item}: {e}")
                elif item.is_dir() and item != base_path:
                    try:
                        item.rmdir()
                        folders_removed += 1
                    except Exception as e:
                        Log.debug(f"Pasta não vazia ou erro: {item}")
            
            success_msg = f"✅ Limpeza concluída: {files_removed} arquivos, {folders_removed} pastas removidas"
            Log.info(success_msg)
            
            return True, success_msg
            
        except Exception as e:
            error_msg = f"Erro na limpeza: {e}"
            Log.error(error_msg)
            return False, error_msg
    
    def get_day_directory_stats(
        self,
        endpoint: int,
        report_date: datetime
    ) -> Dict[str, any]:
        """
        Obtém estatísticas do diretório do dia.
        
        Returns:
            Dict: Estatísticas do diretório
        """
        try:
            base_path = self.build_directory_path(endpoint, report_date).parent
            
            if not base_path.exists():
                return {"exists": False}
            
            stats = {
                "exists": True,
                "path": str(base_path),
                "total_files": 0,
                "total_size_bytes": 0,
                "formats": {},
                "last_modified": None
            }
            
            for item in base_path.rglob('*'):
                if item.is_file():
                    stats["total_files"] += 1
                    file_size = item.stat().st_size
                    stats["total_size_bytes"] += file_size
                    
                    # Contar por formato
                    parent_name = item.parent.name
                    if parent_name not in stats["formats"]:
                        stats["formats"][parent_name] = {"files": 0, "size": 0}
                    
                    stats["formats"][parent_name]["files"] += 1
                    stats["formats"][parent_name]["size"] += file_size
                    
                    # Última modificação
                    file_time = datetime.fromtimestamp(item.stat().st_mtime)
                    if stats["last_modified"] is None or file_time > stats["last_modified"]:
                        stats["last_modified"] = file_time
            
            stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)
            
            if stats["last_modified"]:
                stats["last_modified"] = stats["last_modified"].isoformat()
            
            return stats
            
        except Exception as e:
            Log.error(f"Erro ao obter estatísticas: {e}")
            return {"exists": False, "error": str(e)}
    
    def prepare_aws_backup_structure(
        self,
        endpoint: int,
        report_date: datetime
    ) -> Dict[str, str]:
        """
        Prepara estrutura para backup AWS S3.
        Retorna mapeamento de caminhos locais para S3.
        
        Returns:
            Dict[str, str]: {caminho_local: caminho_s3}
        """
        backup_mappings = {}
        
        try:
            base_path = self.build_directory_path(endpoint, report_date).parent
            
            if not base_path.exists():
                return {}
            
            # Estrutura S3: daycoval-reports/endpoint_32/2025/08/12/
            s3_base = f"daycoval-reports/endpoint_{endpoint}/{report_date.year}/{report_date.month:02d}/{report_date.day:02d}"
            
            for item in base_path.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(base_path)
                    s3_path = f"{s3_base}/{relative_path.as_posix()}"
                    backup_mappings[str(item)] = s3_path
            
            Log.info(f"📦 Preparados {len(backup_mappings)} arquivos para backup S3")
            return backup_mappings
            
        except Exception as e:
            Log.error(f"Erro ao preparar backup: {e}")
            return {}
    
    def create_directory_index(
        self,
        endpoint: int,
        report_date: datetime
    ) -> bool:
        """Cria arquivo índice do diretório."""
        try:
            base_path = self.build_directory_path(endpoint, report_date).parent
            
            if not base_path.exists():
                return False
            
            index_data = {
                "directory_info": {
                    "endpoint": endpoint,
                    "endpoint_name": self.directory_mappings.get(endpoint, f"Endpoint_{endpoint}"),
                    "report_date": report_date.strftime('%Y-%m-%d'),
                    "created_at": datetime.now().isoformat(),
                    "base_path": str(base_path)
                },
                "statistics": self.get_day_directory_stats(endpoint, report_date),
                "backup_ready": len(self.prepare_aws_backup_structure(endpoint, report_date)) > 0
            }
            
            index_file = base_path / "directory_index.json"
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            Log.info(f"📋 Índice criado: {index_file}")
            return True
            
        except Exception as e:
            Log.error(f"Erro ao criar índice: {e}")
            return False

class DirectoryAutomation:
    """Automação de operações de diretório."""
    
    def __init__(self, manager: EnhancedDirectoryManager):
        self.manager = manager
    
    def auto_setup_for_report(
        self,
        endpoint: int,
        report_date: datetime,
        report_format: str,
        enable_consolidated: bool = False,
        auto_clean: bool = True
    ) -> Tuple[Path, Dict[str, any]]:
        """
        Configuração automática completa para relatório.
        
        Args:
            endpoint: Número do endpoint
            report_date: Data do relatório
            report_format: Formato principal
            enable_consolidated: Se deve criar pasta consolidado
            auto_clean: Se deve limpar pasta do dia
            
        Returns:
            Tuple[Path, Dict]: (diretório_principal, informações)
        """
        try:
            Log.info(f"🤖 Configuração automática - Endpoint {endpoint}, {report_date.strftime('%Y-%m-%d')}")
            
            # Limpar diretório do dia se solicitado
            if auto_clean:
                cleaned, clean_msg = self.manager.clean_day_directory(endpoint, report_date, confirm=True)
                Log.info(f"🧹 {clean_msg}")
            
            # Criar estrutura de diretórios
            formats = [report_format]
            if enable_consolidated and endpoint == 32:  # Apenas para carteira diária
                formats.append("Consolidado")
            
            created_paths = self.manager.create_directory_structure(
                endpoint, report_date, formats, enable_consolidated
            )
            
            if not created_paths:
                raise Exception("Falha ao criar estrutura de diretórios")
            
            # Diretório principal
            main_dir = created_paths.get(report_format)
            
            # Criar índice
            self.manager.create_directory_index(endpoint, report_date)
            
            # Informações de retorno
            setup_info = {
                "created_paths": {k: str(v) for k, v in created_paths.items()},
                "main_directory": str(main_dir),
                "cleanup_performed": auto_clean,
                "consolidated_enabled": enable_consolidated,
                "ready_for_processing": True
            }
            
            Log.info(f"✅ Configuração automática concluída - {len(created_paths)} diretórios criados")
            
            return main_dir, setup_info
            
        except Exception as e:
            error_msg = f"Erro na configuração automática: {e}"
            Log.error(error_msg)
            return None, {"error": error_msg, "ready_for_processing": False}

# Instâncias globais
directory_manager = EnhancedDirectoryManager()
directory_automation = DirectoryAutomation(directory_manager)

def auto_setup_directories(
    endpoint: int,
    report_date: datetime,
    report_format: str = "PDF",
    enable_consolidated: bool = False,
    base_drive: str = "F:"
) -> Tuple[Path, Dict]:
    """
    Função utilitária para configuração automática de diretórios.
    
    Returns:
        Tuple[Path, Dict]: (diretório_principal, informações)
    """
    global directory_manager, directory_automation
    
    # Reconfigurar drive se necessário
    if base_drive != directory_manager.base_drive:
        directory_manager = EnhancedDirectoryManager(base_drive)
        directory_automation = DirectoryAutomation(directory_manager)
    
    return directory_automation.auto_setup_for_report(
        endpoint, report_date, report_format, enable_consolidated, auto_clean=True
    )

def get_output_directory(
    endpoint: int,
    report_date: datetime,
    format_type: str = "PDF",
    is_consolidated: bool = False
) -> Path:
    """Função utilitária para obter diretório de saída."""
    return directory_manager.build_directory_path(endpoint, report_date, format_type, is_consolidated)

def clean_directory_for_date(endpoint: int, report_date: datetime) -> bool:
    """Função utilitária para limpar diretório."""
    success, _ = directory_manager.clean_day_directory(endpoint, report_date, confirm=True)
    return success

def create_profitability_directory(
    endpoint: int,
    base_drive: str = "F:",
    report_date: datetime = None
) -> Path:
    """
    Cria diretório específico para relatórios de rentabilidade.
    
    Estrutura: F:\14. Rentabilidade Sintética\Daycoval\2025\08 Agosto\21.08\PDF\
    """
    global directory_manager
    
    if base_drive != directory_manager.base_drive:
        directory_manager = EnhancedDirectoryManager(base_drive)
    
    if not report_date:
        report_date = datetime.now()
    
    return directory_manager.build_directory_path(
        endpoint=endpoint,
        report_date=report_date,
        format_type="PDF"
    )

def auto_setup_profitability_directories(
    endpoint: int,
    report_date: datetime,
    report_format: str = "PDF",
    base_drive: str = "F:"
) -> Tuple[Path, Dict]:
    """
    Configuração automática para relatórios de rentabilidade.
    
    Args:
        endpoint: 1048 (sintética) ou 1799 (padrão)
        report_date: Data do relatório
        report_format: Formato do relatório
        base_drive: Drive base
        
    Returns:
        Tuple[Path, Dict]: (diretório_principal, informações)
    """
    global directory_manager, directory_automation
    
    if base_drive != directory_manager.base_drive:
        directory_manager = EnhancedDirectoryManager(base_drive)
        directory_automation = DirectoryAutomation(directory_manager)
    
    return directory_automation.auto_setup_for_report(
        endpoint=endpoint,
        report_date=report_date,
        report_format=report_format,
        enable_consolidated=False,  # Rentabilidade não usa consolidado
        auto_clean=True
    )