"""
Utilitários para manipulação de arquivos.
"""
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.models import ReportFormat


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres inválidos.
    
    Args:
        filename: Nome original do arquivo
        
    Returns:
        Nome sanitizado compatível com sistemas de arquivo
    """
    if not filename:
        return "ARQUIVO_SEM_NOME"
    
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


def generate_filename(
    portfolio_name: str,
    date: datetime,
    format: ReportFormat,
    report_type: str = "RELATORIO"
) -> str:
    """
    Gera nome de arquivo com padrão: [PREFIXO_]NOME_FUNDO_AAAAMMDD.extensao
    
    Args:
        portfolio_name: Nome do fundo (vem do CADFUN via PortfolioManager)
        date: Data do relatório
        format: Formato do arquivo
        report_type: Tipo do relatório para prefixo
        
    Returns:
        Nome do arquivo sanitizado e padronizado
    """
    if not portfolio_name:
        portfolio_name = "FUNDO_GENERICO"
    
    # Sanitizar nome do fundo (já vem do CADFUN)
    clean_name = sanitize_filename(portfolio_name)
    
    # Formatar data
    date_formatted = date.strftime('%Y%m%d')
    
    # Construir nome do arquivo
    if report_type and report_type != "RELATORIO":
        # Para relatórios com prefixo específico (ex: RENTABILIDADE_SINTETICA)
        filename = f"{report_type}_{clean_name}_{date_formatted}{format.extension}"
    else:
        # Para relatórios padrão (sem prefixo)
        filename = f"{clean_name}_{date_formatted}{format.extension}"
    
    return filename


def ensure_directory(path: Path) -> Path:
    """
    Garante que um diretório existe, criando se necessário.
    
    Args:
        path: Caminho do diretório
        
    Returns:
        Path do diretório criado
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size_mb(file_path: Path) -> float:
    """
    Retorna tamanho do arquivo em MB.
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        Tamanho em MB
    """
    if not file_path.exists():
        return 0.0
    
    size_bytes = file_path.stat().st_size
    return size_bytes / (1024 * 1024)


def clean_csv_content(content: str, delimiter: str = ';') -> str:
    """
    Limpa conteúdo CSV removendo espaços excessivos.
    
    Args:
        content: Conteúdo CSV
        delimiter: Delimitador usado
        
    Returns:
        Conteúdo CSV limpo
    """
    if not content:
        return content
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        if line.strip():  # Pular linhas vazias
            if delimiter in line:
                # Limpar cada campo
                fields = line.split(delimiter)
                cleaned_fields = [field.strip() for field in fields]
                cleaned_lines.append(delimiter.join(cleaned_fields))
            else:
                # Aplicar limpeza geral
                cleaned_line = re.sub(r'\s+', ' ', line.strip())
                cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)


def validate_file_path(file_path: Path) -> bool:
    """
    Valida se um caminho de arquivo é válido.
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        True se válido, False caso contrário
    """
    try:
        # Verificar se o diretório pai pode ser criado
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verificar se o nome do arquivo é válido
        if not file_path.name or len(file_path.name) > 255:
            return False
        
        # Verificar caracteres inválidos
        invalid_chars = '<>:"/\\|?*'
        if any(char in str(file_path) for char in invalid_chars):
            return False
        
        return True
        
    except (OSError, ValueError):
        return False


def backup_file(file_path: Path, backup_suffix: str = None) -> Optional[Path]:
    """
    Cria backup de um arquivo.
    
    Args:
        file_path: Arquivo original
        backup_suffix: Sufixo para o backup (default: timestamp)
        
    Returns:
        Caminho do backup criado ou None se falhou
    """
    if not file_path.exists():
        return None
    
    try:
        if backup_suffix is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_suffix = f"backup_{timestamp}"
        
        backup_path = file_path.with_suffix(f".{backup_suffix}{file_path.suffix}")
        
        # Copiar arquivo
        import shutil
        shutil.copy2(file_path, backup_path)
        
        return backup_path
        
    except Exception:
        return None


def get_temp_file(prefix: str = "daycoval", suffix: str = ".tmp") -> Path:
    """
    Cria arquivo temporário.
    
    Args:
        prefix: Prefixo do arquivo
        suffix: Sufixo/extensão do arquivo
        
    Returns:
        Caminho do arquivo temporário
    """
    import tempfile
    
    temp_dir = Path(tempfile.gettempdir()) / "daycoval"
    temp_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    temp_file = temp_dir / f"{prefix}_{timestamp}{suffix}"
    
    return temp_file


def cleanup_temp_files(max_age_hours: int = 24) -> int:
    """
    Remove arquivos temporários antigos.
    
    Args:
        max_age_hours: Idade máxima em horas
        
    Returns:
        Número de arquivos removidos
    """
    import tempfile
    import time
    
    temp_dir = Path(tempfile.gettempdir()) / "daycoval"
    
    if not temp_dir.exists():
        return 0
    
    cutoff_time = time.time() - (max_age_hours * 3600)
    removed_count = 0
    
    for file_path in temp_dir.iterdir():
        if file_path.is_file():
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    removed_count += 1
            except OSError:
                pass  # Ignorar erros de acesso
    
    return removed_count