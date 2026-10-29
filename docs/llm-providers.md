# Optional LLM provider

Repository indexing, full-text search, and evidence retrieval work locally without a model provider. To enable natural-language answers, configure an OpenAI-compatible chat-completions endpoint:

```dotenv
OPENAI_API_KEY=your-provider-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
```

Restart the API after setting environment variables. Compatible providers may be used by setting the base URL and model to their documented values. Keep credentials in environment variables or a secret manager such as Doppler; never commit real keys to source control.

## Grounding and limitations

- Repository snippets are treated as untrusted data and never given tool access.
- At most eight retrieved snippets are sent, each truncated to 3,000 characters.
- Answers must cite source paths using `[[relative/path]]` markers.
- Responses with missing citations or paths not present in the retrieved evidence are rejected.
- Network/provider errors fall back to evidence-only retrieval.
- Citation validation is a guardrail, not a proof that every generated claim is correct. Review the cited source before acting on an answer.

The `/api/repos/{repo_id}/ask` endpoint returns `mode: "llm"` for a validated provider answer or `mode: "retrieval_only"` for fallback.
