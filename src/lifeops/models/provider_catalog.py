"""Documented provider presets; credentials are referenced by environment variable."""
PROVIDER_PRESETS = {
    "ollama": {"base_url": "http://127.0.0.1:11434/v1", "api_key_env": ""},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "cerebras": {"base_url": "https://api.cerebras.ai/v1", "api_key_env": "CEREBRAS_API_KEY"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key_env": "GEMINI_API_KEY"},
    "huggingface": {"base_url": "https://router.huggingface.co/v1", "api_key_env": "HF_TOKEN"},
}
