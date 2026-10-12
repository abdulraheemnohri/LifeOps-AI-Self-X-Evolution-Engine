# Model provider configuration

LifeOps uses one OpenAI-compatible adapter for compatible local servers and explicitly configured hosted endpoints. Provider presets are configuration helpers, not a guarantee that a model exists, a server is reachable, or an account has free quota.

## Configure through the Web UI

Open **Settings** after logging in. Choose a known provider, enter the model identifier used by that provider, optionally supply a local loopback endpoint override, choose a bounded timeout, and save. Saving does not initiate a network request. Connection status remains **Not tested** until a separate, explicit health/test action is implemented.

Endpoint overrides in this settings form are intentionally limited to HTTP loopback addresses (`localhost`, `127.0.0.1`, or `::1`) with an explicit port. This prevents the form from becoming an arbitrary outbound URL/SSRF path. To use a hosted preset, select its preset; do not enter hosted endpoints into the local override field.

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

Credentials must be supplied through process environment or a protected secret manager. Never put API keys in browser forms, HTML, URLs, committed configuration, or logs. Do not assume hosted services are free; verify current terms and quotas.

## Python usage

```python
from lifeops.models.provider_catalog import create_provider_adapter

adapter = create_provider_adapter("ollama", model="your-installed-model")
text = adapter.generate("Summarize the purpose of LifeOps.")
print(text)
```

`is_available()` reports adapter configuration, not endpoint health. A successful `generate()` call is the actual inference check. The initial adapter is synchronous and non-streaming, with no automatic failover. Hosted requests transmit prompt content outside the machine, so use local inference for private content unless you explicitly authorize remote processing.
