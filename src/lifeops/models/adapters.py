from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ModelUnavailableError(RuntimeError):
    """Raised when a configured model runtime cannot be reached."""


class BaseModelAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    def is_available(self) -> bool:
        """Return True if the underlying runtime can currently be used."""
        return True

    def info(self) -> Dict[str, Any]:
        """Describe this adapter for diagnostics endpoints."""
        return {"adapter": type(self).__name__, "available": self.is_available()}

class MockModelAdapter(BaseModelAdapter):
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return f"[Mock Output for: '{prompt}']"

class LiteRTLMAdapter(BaseModelAdapter):
    def __init__(self, binary_path: str = "litert-lm", model_path: Optional[str] = None):
        self.binary_path = binary_path
        self.model_path = model_path

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Fallback to deterministic mock if binary is not installed locally
        import subprocess
        try:
            cmd = [self.binary_path, "--prompt", prompt]
            if self.model_path:
                cmd.extend(["--model", self.model_path])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return f"[LiteRT Local Response for: '{prompt}']"

    def is_available(self) -> bool:
        import shutil
        return shutil.which(self.binary_path) is not None


class OllamaAdapter(BaseModelAdapter):
    """Adapter for a locally running Ollama server (https://ollama.com).

    Talks to the native /api/generate endpoint. No third-party HTTP client
    is required at runtime beyond stdlib urllib so the core install stays lean.
    """

    DEFAULT_BASE_URL = "http://127.0.0.1:11434"

    def __init__(self, model_name: str = "llama3.2", base_url: Optional[str] = None,
                 timeout_seconds: int = 60, generation_params: Optional[Dict[str, Any]] = None):
        self.model_name = model_name or "llama3.2"
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.generation_params = generation_params or {}

    # -- internals ---------------------------------------------------------
    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import json
        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama returned HTTP {exc.code} for {path}") from exc
        except Exception as exc:  # URLError, timeouts, connection refused...
            raise ModelUnavailableError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc

    # -- public API --------------------------------------------------------
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        payload: Dict[str, Any] = {"model": self.model_name, "prompt": prompt, "stream": False}
        if system_prompt:
            payload["system"] = system_prompt
        if self.generation_params:
            payload["options"] = {k: v for k, v in self.generation_params.items() if v is not None}
        data = self._post("/api/generate", payload)
        return data.get("response", "").strip()

    def list_models(self) -> list:
        import json
        import urllib.request

        try:
            with urllib.request.urlopen(self.base_url + "/api/tags", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def is_available(self) -> bool:
        import urllib.request

        try:
            with urllib.request.urlopen(self.base_url + "/", timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def info(self) -> Dict[str, Any]:
        return {"adapter": "OllamaAdapter", "base_url": self.base_url,
                "model": self.model_name, "available": self.is_available()}
