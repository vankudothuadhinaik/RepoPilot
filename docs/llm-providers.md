# Optional LLM provider

RepoPilot's indexing and full-text search work locally without an LLM provider. To enable natural-language answers, configure an OpenAI-compatible chat-completions endpoint:

```dotenv
OPENAI_API_KEY=your-provider-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
```

Restart the API after setting environment variables. Compatible providers can be used by setting `OPENAI_BASE_URL` and `OPENAI_MODEL` to the provider's documented values. Keep keys in environment variables or a secret manager such as Doppler; never commit real keys to `.env`, source files, or repository history.

## Grounding behavior

- The prompt treats repository content as untrusted data and tells the model not to follow instructions found in code.
- Only the top eight retrieved snippets are sent, each truncated to 3,000 characters.
- Answers must cite source paths with `[[relative/path]]` markers.
- The provider response is rejected if it has no citations or cites a path that was not retrieved.
- Provider/network errors fall back to evidence-only retrieval rather than blocking search.
- This is a citation guard, not a proof that every model claim is correct. Review cited source before acting on an answer.

The API's `/ask` response reports `mode: "llm"` when a validated provider answer is returned and `mode: "retrieval_only"` when it falls back.
