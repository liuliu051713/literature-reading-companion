# Model-provider adapters

The core pipeline requests JSON-shaped paper maps and source-linked annotations.
Provider adapters are responsible only for obtaining that structured output.

- openai: uses the OpenAI Responses API with a strict JSON schema.
- gemini: uses the Gemini Interactions API with a JSON schema response format.
- mock: remains offline and produces clearly marked placeholders for tests.

Adding a provider should not change the source model, annotation schema,
quality checks, or renderer contract. Implement the ModelProvider interface,
return the shared data structures, and add an offline test or fixture.

Do not implement a provider by scraping a consumer chat interface. Keep all
provider credentials local and explicit.
