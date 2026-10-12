from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseModelAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

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
