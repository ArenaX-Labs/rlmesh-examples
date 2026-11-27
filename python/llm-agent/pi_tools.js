// Registers the env's tools in pi; each call is answered by the harness over RPC, never run here.
export default function (pi) {
  for (const { function: tool } of JSON.parse(process.env.PI_ENV_TOOLS || "[]")) {
    pi.registerTool({
      name: tool.name,
      label: tool.name,
      description: tool.description ?? "",
      parameters: tool.parameters ?? { type: "object", properties: {} },
      async execute(id, args, signal, _onUpdate, ctx) {
        const call = JSON.stringify({ id, name: tool.name, arguments: args });
        const result = await ctx.ui.input(call, undefined, { signal });
        if (result === undefined) throw new Error("The tool call was cancelled.");
        return { content: [{ type: "text", text: result }], details: {} };
      },
    });
  }

  // pi's own prompt names its cwd and docs, which are on the model pod, not where the tools run.
  const system = ["You are an agent. Your tools run in the task's environment.", process.env.PI_ENV_SYSTEM]
    .filter(Boolean)
    .join("\n\n");
  pi.on("before_agent_start", () => ({ systemPrompt: system }));

  const { PI_PROVIDER, PI_MODEL, OPENAI_BASE_URL } = process.env;
  // pi's built-in openai provider speaks the Responses API at api.openai.com; a base URL means
  // an OpenAI-compatible server (Nebius, vLLM, Ollama), which speaks Chat Completions.
  if (PI_PROVIDER === "openai" && PI_MODEL && OPENAI_BASE_URL) {
    pi.registerProvider("openai", {
      baseUrl: OPENAI_BASE_URL,
      apiKey: "OPENAI_API_KEY",
      api: "openai-completions",
      models: [
        {
          id: PI_MODEL,
          name: PI_MODEL,
          reasoning: false,
          input: ["text", "image"],
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
          // TODO: fixed limits for unknown models; read them from env vars once a model needs others.
          contextWindow: 128000,
          maxTokens: 8192,
        },
      ],
    });
  }
}
