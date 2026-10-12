# Model providers

LifeOps supports a local-first design. A provider is used only when an administrator explicitly configures it. Keep the default model set to the deterministic mock adapter until a real runtime is configured.

## Local adapters

- **Ollama**: local model server; the adapter can use its OpenAI-compatible API at `http://127.0.0.1:11434/v1`. Install Ollama separately and download a model. See [official compatibility documentation](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx).
- **LiteRT-LM**: optional Python runtime using a local `.litertlm` model file. Install the runtime separately and validate model compatibility. See [LiteRT-LM Python API](https://developers.google.cn/edge/litert-lm/python).
- **Other local servers**: LM Studio and vLLM can be connected when their OpenAI-compatible endpoint is explicitly configured.

## Hosted endpoints with potential free tiers

The generic OpenAI-compatible adapter can connect to providers exposing `POST /chat/completions`. Examples include Groq, Cerebras, OpenRouter, and Google's Gemini OpenAI-compatible endpoint. Hugging Face provides a model router with compatible interfaces for supported models.

1. Create an account with the provider and check its current model list, data policy, rate limits, and free-tier terms.
2. Set the provider key in the environment (for example, `GROQ_API_KEY` or `GEMINI_API_KEY`).
3. Copy `config/model-providers.example.toml` to a private configuration file and choose a model that your account can access.
4. Never commit real keys, put them in browser code, or pass them in URLs.

"Free online adapters" means adapters for services that may offer free quotas, not guaranteed unlimited free inference. Provider quotas, eligible models, and terms can change. Hosted inference sends prompt data to the selected provider; keep sensitive personal data on local models unless you explicitly accept that provider's privacy terms.

## Current limitations

The initial adapter supports non-streaming text chat only. It does not yet implement provider-specific tool calls, image/audio inputs, embeddings, automatic failover, or live model discovery across every provider. Health metadata confirms configuration shape, not successful network inference. Do not expose arbitrary endpoint URLs to untrusted users; configure trusted endpoints locally.
