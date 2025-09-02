"""
Cliente HTTP para comunicação com a API Daycoval.
"""
import asyncio
import time
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config.settings import APISettings
from .exceptions import APIError, RateLimitError, AuthenticationError, TimeoutError


class RateLimiter:
    """Implementa rate limiting com janela deslizante."""
    
    def __init__(self, max_calls: int, period_seconds: int):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.calls = []
    
    def _cleanup_old_calls(self) -> None:
        """Remove chamadas antigas da janela."""
        current_time = time.time()
        cutoff_time = current_time - self.period_seconds
        self.calls = [call_time for call_time in self.calls if call_time > cutoff_time]
    
    def can_make_call(self) -> bool:
        """Verifica se pode fazer uma chamada agora."""
        self._cleanup_old_calls()
        return len(self.calls) < self.max_calls
    
    def wait_time(self) -> float:
        """Retorna tempo de espera necessário em segundos."""
        self._cleanup_old_calls()
        
        if len(self.calls) < self.max_calls:
            return 0.0
        
        # Tempo até a chamada mais antiga sair da janela
        oldest_call = min(self.calls)
        return (oldest_call + self.period_seconds) - time.time()
    
    def record_call(self) -> None:
        """Registra uma chamada."""
        self.calls.append(time.time())
    
    async def wait_if_needed(self) -> None:
        """Aguarda se necessário para respeitar rate limit."""
        wait_time = self.wait_time()
        if wait_time > 0:
            await asyncio.sleep(wait_time)


class APIClient:
    """Cliente HTTP para a API Daycoval."""
    
    def __init__(self, settings: APISettings):
        self.settings = settings
        self.rate_limiter = RateLimiter(
            settings.rate_limit_calls, 
            settings.rate_limit_period
        )
        self._session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP com retry automático."""
        session = requests.Session()
        
        # Configurar estratégia de retry
        retry_strategy = Retry(
            total=self.settings.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=self.settings.backoff_factor,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers padrão para requisições."""
        return {
            "apikey": self.settings.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _handle_response(self, response: requests.Response) -> requests.Response:
        """Trata resposta da API e levanta exceções apropriadas."""
        if response.status_code == 401:
            raise AuthenticationError("Credenciais inválidas")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit excedido")
        elif response.status_code >= 400:
            raise APIError(
                f"Erro na API: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text
            )
        
        return response
    
    async def post(self, endpoint: str, json_data: Dict[str, Any]) -> requests.Response:
        """Faz requisição POST com rate limiting."""
        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.settings.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            # Usar run_in_executor para não bloquear event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._session.post(
                    url, 
                    json=json_data, 
                    headers=headers, 
                    timeout=self.settings.timeout
                )
            )
            
            self.rate_limiter.record_call()
            return self._handle_response(response)
            
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Timeout após {self.settings.timeout}s: {e}")
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Timeout após {self.settings.timeout}s: {e}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Erro de comunicação: {e}")
    
    def post_sync(self, endpoint: str, json_data: Dict[str, Any]) -> requests.Response:
        """Versão síncrona do post para compatibilidade."""
        # Implementação simplificada sem rate limiting assíncrono
        if not self.rate_limiter.can_make_call():
            wait_time = self.rate_limiter.wait_time()
            if wait_time > 0:
                time.sleep(wait_time)
        
        url = f"{self.settings.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = self._session.post(
                url, 
                json=json_data, 
                headers=headers, 
                timeout=self.settings.timeout
            )
            
            self.rate_limiter.record_call()
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            raise APIError(f"Erro de comunicação: {e}")
    
    def close(self) -> None:
        """Fecha a sessão HTTP."""
        if self._session:
            self._session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()