# Model provider configuration

LifeOps uses one OpenAI-compatible adapter for compatible local servers and explicitly configured hosted endpoints. Provider presets are configuration helpers, not a guarantee that a model exists, a server is reachable, or an account has free quota.

## Local endpoints

| Preset | Default endpoint | Notes |
|---|---|---|
| `ollama` | `http://127.0.0.1:11434/v1` | Start Ollama and pull a model separately. |
| `lm_studio` | `http://127.0.0.1:1234/v1` | Enable the local server in LM Studio. |
| `vllm` | `http://127.0.0.1:8000/v1` | Start a compatible vLLM OpenAI server. |

## Hosted endpoints

| Preset | Environment variable | Notes |
|---|---|---|
| `groq` | `GROQ_API_KEY` | Provider account and applicable quota required. |
| `cerebras` | `CEREBRAS_API_KEY` | Provider account and applicable quota required. |
| `openrouter` | `OPENROUTER_API_KEY` | Model availability and pricing vary by model. |
| `gemini` | `GEMINI_API_KEY` | Use a model supported by the provider's compatible API. |
| `huggingface` | `HF_TOKEN` | Endpoint/model compatibility and quota vary. |

Set credentials in the process environment or a protected secret manager. Never place API keys in browser code, URLs, committed configuration, or screenshots. Do not assume hosted services are free; verify each provider's current terms and quota.

## Python usage

```python
from lifeops.models.provider_catalog import create_provider_adapter

adapter = create_provider_adapter("ollama", model="your-installed-model")
text = adapter.generate("Summarize the purpose of LifeOps.")
print(text)
```

`is_available()` reports that adapter configuration is present; it does not probe the endpoint. A successful `generate()` call is the actual inference check. The initial adapter is synchronous, non-streaming, and does not implement automatic failover. Configure one provider explicitly and handle `ProviderError` in the calling service.

Hosted provider requests send prompt content outside the machine. Keep the default local-first policy and do not route private content to hosted providers without user configuration and authorization.
