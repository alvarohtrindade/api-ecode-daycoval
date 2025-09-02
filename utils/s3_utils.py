#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitário S3 para operações de leitura e escrita no bucket.

Autor: Equipe Data Analytics - Catalise Investimentos
"""

import os
import json
import boto3
import pandas as pd
from pathlib import Path
from typing import Union, Dict, Any, List, Optional, BinaryIO
from io import BytesIO, StringIO
import zipfile
from botocore.exceptions import ClientError, NoCredentialsError
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class S3Manager:
    """Gerenciador de operações S3 com suporte a múltiplos formatos."""
    
    def __init__(self, bucket_name: str = None, region: str = 'sa-east-1'):
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        self.region = region
        self._client = None
        self._lock = threading.Lock()
        
    @property
    def client(self):
        """Cliente S3 thread-safe com lazy loading."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = boto3.client('s3', region_name=self.region)
        return self._client
    
    def build_path(self, custodiante: str, tipo_relatorio: str, data_ref: str, 
                ambiente: str = 'landing') -> str:
        """
        Constrói path S3 seguindo padrão: {custodiante}/{ambiente}/{tipo}/{ano}/{mes}/{dia}/
        
        Args:
            custodiante: btg, daycoval, etc
            tipo_relatorio: extrato, carteira, rentabilidade, resgate
            data_ref: YYYY-MM-DD
            ambiente: landing, processed, curated
        """
        ano, mes, dia = data_ref.split('-')
        path = f"{custodiante}/{ambiente}/{tipo_relatorio}/{ano}/{mes}/{dia}"
        print(f"Path S3 construído: {path}")
        return path
    
    def upload_file(self, local_path: Union[str, Path], s3_key: str, 
                    metadata: Dict[str, str] = None) -> bool:
        """Upload de arquivo único para S3."""
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
                
            self.client.upload_file(
                str(local_path), 
                self.bucket_name, 
                s3_key,
                ExtraArgs=extra_args
            )
            return True
        except Exception as e:
            raise Exception(f"Erro no upload de {local_path}: {str(e)}")
    
    def upload_fileobj(self, file_obj: BinaryIO, s3_key: str, 
                      metadata: Dict[str, str] = None) -> bool:
        """Upload de objeto file-like para S3."""
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
                
            self.client.upload_fileobj(
                file_obj, 
                self.bucket_name, 
                s3_key,
                ExtraArgs=extra_args
            )
            return True
        except Exception as e:
            raise Exception(f"Erro no upload do objeto: {str(e)}")
    
    def upload_json(self, data: Union[Dict, List], s3_key: str) -> bool:
        """Upload de dados JSON diretamente para S3."""
        try:
            json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_bytes,
                ContentType='application/json'
            )
            return True
        except Exception as e:
            raise Exception(f"Erro no upload JSON: {str(e)}")
        
    def _to_ndjson_bytes(self, data: Union[Dict, List]) -> bytes:
        """
        Converte um dict/list em NDJSON (uma linha JSON por registro).

        Regras:
        - Se for um dict com a chave "result" (lista), cada item da lista vira
          uma linha independente.
        - Se for uma lista, cada item vira linha.
        - Nos demais casos, serializa o objeto inteiro em uma única linha.
        """
        if isinstance(data, list):
            linhas = [json.dumps(obj, ensure_ascii=False) for obj in data]

        elif isinstance(data, dict):
            if "result" in data and isinstance(data["result"], list):
                linhas = [json.dumps(obj, ensure_ascii=False)
                          for obj in data["result"]]
            else:
                linhas = [json.dumps(data, ensure_ascii=False)]
        else:
            raise ValueError("Tipo de dado não suportado para NDJSON")

        return ("\n".join(linhas)).encode("utf-8")

    def upload_ndjson(self, data: Union[Dict, List], s3_key: str) -> bool:
        """
        Faz upload de dados em formato NDJSON para o S3.

        Args:
            data: dict ou list conforme _to_ndjson_bytes()
            s3_key: caminho completo no bucket (sufixo sugerido: .ndjson)
        """
        try:
            ndjson_bytes = self._to_ndjson_bytes(data)
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=ndjson_bytes,
                ContentType="application/x-ndjson"
            )
            return True
        except Exception as e:
            raise Exception(f"Erro no upload NDJSON: {str(e)}")
    
    def upload_dataframe(self, df: pd.DataFrame, s3_key: str, 
                        format: str = 'parquet') -> bool:
        """
        Upload de DataFrame pandas para S3.
        
        Args:
            df: DataFrame a ser salvo
            s3_key: Caminho no S3
            format: 'parquet', 'csv', 'xlsx'
        """
        try:
            buffer = BytesIO()
            
            if format == 'parquet':
                df.to_parquet(buffer, index=False, engine='pyarrow')
                content_type = 'application/octet-stream'
            elif format == 'csv':
                df.to_csv(buffer, index=False, encoding='utf-8')
                content_type = 'text/csv'
            elif format == 'xlsx':
                df.to_excel(buffer, index=False, engine='openpyxl')
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                raise ValueError(f"Formato não suportado: {format}")
            
            buffer.seek(0)
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType=content_type
            )
            return True
        except Exception as e:
            raise Exception(f"Erro no upload do DataFrame: {str(e)}")
    
    def upload_directory(self, local_dir: Union[str, Path], s3_prefix: str,
                        extensions: List[str] = None, max_workers: int = 5) -> Dict[str, bool]:
        """
        Upload de diretório completo para S3 com paralelização.
        
        Args:
            local_dir: Diretório local
            s3_prefix: Prefixo S3
            extensions: Lista de extensões para filtrar (ex: ['.json', '.csv'])
            max_workers: Número de threads paralelas
        
        Returns:
            Dict com status de cada arquivo
        """
        local_dir = Path(local_dir)
        results = {}
        
        files_to_upload = []
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                if extensions and file_path.suffix not in extensions:
                    continue
                    
                relative_path = file_path.relative_to(local_dir)
                s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')
                files_to_upload.append((file_path, s3_key))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.upload_file, file_path, s3_key): (file_path, s3_key)
                for file_path, s3_key in files_to_upload
            }
            
            for future in as_completed(future_to_file):
                file_path, s3_key = future_to_file[future]
                try:
                    future.result()
                    results[str(file_path)] = True
                except Exception as e:
                    results[str(file_path)] = False
        
        return results
    
    def download_file(self, s3_key: str, local_path: Union[str, Path]) -> bool:
        """Download de arquivo do S3."""
        try:
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            return True
        except Exception as e:
            raise Exception(f"Erro no download de {s3_key}: {str(e)}")
    
    def read_json(self, s3_key: str) -> Union[Dict, List]:
        """Lê arquivo JSON diretamente do S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            raise Exception(f"Erro ao ler JSON {s3_key}: {str(e)}")
    
    def read_dataframe(self, s3_key: str, format: str = None) -> pd.DataFrame:
        """
        Lê DataFrame diretamente do S3.
        
        Args:
            s3_key: Caminho no S3
            format: Formato do arquivo. Se None, detecta pela extensão
        """
        try:
            if format is None:
                format = Path(s3_key).suffix[1:]
            
            response = self.client.get_object(Bucket=self.bucket_name, Key=s3_key)
            body = response['Body'].read()
            
            if format == 'parquet':
                return pd.read_parquet(BytesIO(body))
            elif format == 'csv':
                return pd.read_csv(BytesIO(body))
            elif format in ['xlsx', 'xls']:
                return pd.read_excel(BytesIO(body))
            else:
                raise ValueError(f"Formato não suportado: {format}")
        except Exception as e:
            raise Exception(f"Erro ao ler DataFrame {s3_key}: {str(e)}")
    
    def list_objects(self, prefix: str, max_results: int = 1000) -> List[Dict[str, Any]]:
        """Lista objetos no S3 com prefixo específico."""
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={'MaxItems': max_results}
            )
            
            objects = []
            for page in pages:
                if 'Contents' in page:
                    objects.extend(page['Contents'])
            
            return objects
        except Exception as e:
            raise Exception(f"Erro ao listar objetos com prefixo {prefix}: {str(e)}")
    
    def exists(self, s3_key: str) -> bool:
        """Verifica se objeto existe no S3."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def delete_object(self, s3_key: str) -> bool:
        """Remove objeto do S3."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception as e:
            raise Exception(f"Erro ao deletar {s3_key}: {str(e)}")
    
    def extract_zip(self, s3_zip_key: str, s3_extract_prefix: str) -> List[str]:
        """
        Extrai ZIP do S3 e salva conteúdo extraído no S3.
        
        Returns:
            Lista de keys dos arquivos extraídos
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=s3_zip_key)
            zip_data = response['Body'].read()
            
            extracted_keys = []
            with zipfile.ZipFile(BytesIO(zip_data)) as zf:
                for file_info in zf.filelist:
                    if not file_info.is_dir():
                        file_data = zf.read(file_info.filename)
                        s3_key = f"{s3_extract_prefix}/{file_info.filename}"
                        
                        self.client.put_object(
                            Bucket=self.bucket_name,
                            Key=s3_key,
                            Body=file_data
                        )
                        extracted_keys.append(s3_key)
            
            return extracted_keys
        except Exception as e:
            raise Exception(f"Erro ao extrair ZIP {s3_zip_key}: {str(e)}")


def get_s3_manager(bucket_name: str = None) -> S3Manager:
    """Factory function para obter instância do S3Manager."""
    return S3Manager(bucket_name=bucket_name)