"""
Static mapping of model display names → free providers.

Derived from free-coding-models npm package (sources.js).
To regenerate after updating the package, run:

    node --input-type=module <<'EOF'
    import { sources } from '/usr/local/lib/node_modules/free-coding-models/sources.js';
    const skip = new Set(['gemini', 'opencode-zen']);
    const names = {
      nvidia: 'NIM', groq: 'Groq', cerebras: 'Cerebras', googleai: 'Google AI',
      'github-models': 'GitHub', mistral: 'Mistral', cloudflare: 'Cloudflare',
      openrouter: 'OpenRouter', sambanova: 'SambaNova', ovhcloud: 'OVHcloud',
      codestral: 'Codestral', zai: 'ZAI', scaleway: 'Scaleway', qwen: 'DashScope',
    };
    const result = {};
    for (const [k, src] of Object.entries(sources)) {
      if (skip.has(k)) continue;
      const p = names[k] || src.name;
      for (const [, label] of src.models) {
        if (!result[label]) result[label] = [];
        if (!result[label].includes(p)) result[label].push(p);
      }
    }
    console.log(JSON.stringify(result, null, 2));
    EOF

Providers included (14 free API providers, CLI-only and Zen excluded):
  NIM (NVIDIA NIM), Groq, Cerebras, Google AI, GitHub, Mistral,
  Cloudflare, OpenRouter, SambaNova, OVHcloud, Codestral,
  ZAI, Scaleway, DashScope (Alibaba)
"""

# fmt: off
FCM_PROVIDERS: dict[str, list[str]] = {
    # ── NVIDIA NIM only ──────────────────────────────────────────────────────
    "MiniMax M2.7":               ["NIM"],
    "GLM 5.1":                    ["NIM"],
    "DeepSeek V4 Pro":            ["NIM"],
    "DeepSeek V4 Flash":          ["NIM"],
    "GLM 5":                      ["NIM"],
    "Step 3.5 Flash":             ["NIM"],
    "MiniMax M2":                 ["NIM"],
    "Qwen3 80B Thinking":         ["NIM"],
    "Mistral Medium 3.5":         ["NIM"],
    "Mistral Small 4":            ["NIM"],
    "Qwen3.5 122B":               ["NIM"],
    "Nemotron Ultra 253B":        ["NIM"],
    "Nemotron Super 49B":         ["NIM"],
    "Seed OSS 36B":               ["NIM"],
    "Stockmark 100B":             ["NIM"],
    "Mixtral 8x22B":              ["NIM"],
    "Ministral 14B":              ["NIM"],
    "Granite 34B Code":           ["NIM"],
    "Phi 4 Mini":                 ["NIM"],
    # ── Multi-provider ───────────────────────────────────────────────────────
    "Kimi K2.6":                  ["NIM", "Cloudflare"],
    "Qwen3 Coder 480B":           ["NIM", "OpenRouter"],
    "Qwen3 80B Instruct":         ["NIM", "OpenRouter"],
    "Qwen3.5 400B VLM":           ["NIM", "Scaleway"],
    "GPT OSS 120B":               ["NIM", "Groq", "Cerebras", "Cloudflare", "OpenRouter", "SambaNova", "OVHcloud", "Scaleway"],
    "Llama 4 Maverick":           ["NIM", "GitHub", "SambaNova"],
    "Mistral Large 675B":         ["NIM", "Scaleway"],
    "Nemotron 3 Super":           ["NIM", "Cloudflare", "OpenRouter"],
    "Nemotron 3 Omni":            ["NIM", "OpenRouter"],
    "Nemotron Nano 30B":          ["NIM", "OpenRouter"],
    "GPT OSS 20B":                ["NIM", "Groq", "Cloudflare", "OpenRouter", "OVHcloud"],
    "Gemma 4 31B":                ["NIM", "Cloudflare", "OpenRouter"],
    "Llama 3.3 70B":              ["NIM", "Groq", "GitHub", "Cloudflare", "OpenRouter", "SambaNova", "OVHcloud", "Scaleway"],
    "Llama 3.1 8B":               ["NIM", "Groq", "Cerebras", "GitHub", "Cloudflare", "OVHcloud"],
    # ── Groq ─────────────────────────────────────────────────────────────────
    "Llama 4 Scout":              ["Groq", "GitHub", "Cloudflare"],
    "Qwen3 32B":                  ["Groq", "OVHcloud", "DashScope"],
    "Groq Compound":              ["Groq"],
    "Groq Compound Mini":         ["Groq"],
    # ── Cerebras ─────────────────────────────────────────────────────────────
    "Qwen3 235B":                 ["Cerebras", "Scaleway", "DashScope"],
    "GLM 4.7":                    ["Cerebras"],
    # ── Google AI Studio ─────────────────────────────────────────────────────
    "Gemini 3.1 Pro Preview":     ["Google AI"],
    "Gemini 3 Flash Preview":     ["Google AI"],
    "Gemini 3.1 Flash Lite Preview": ["Google AI"],
    "Gemini 2.5 Pro":             ["Google AI"],
    "Gemini 2.5 Flash":           ["Google AI"],
    "Gemini 2.5 Flash Lite":      ["Google AI"],
    # ── GitHub Models ────────────────────────────────────────────────────────
    "GPT-4.1":                    ["GitHub"],
    "GPT-4.1 Mini":               ["GitHub"],
    "GPT-4.1 Nano":               ["GitHub"],
    "DeepSeek V3 0324":           ["GitHub"],
    "Llama 3.1 405B":             ["GitHub"],
    "Llama 3.2 90B Vision":       ["GitHub"],
    "Llama 3.2 11B Vision":       ["GitHub"],
    "Codestral 2501":             ["GitHub"],
    "Mistral Medium 2505":        ["GitHub"],
    "Mistral Small 2503":         ["GitHub", "OVHcloud"],
    "Ministral 3B":               ["GitHub"],
    # ── Mistral La Plateforme (free experiment plan) ─────────────────────────
    "Mistral Large":              ["Mistral"],
    "Mistral Medium":             ["Mistral"],
    "Mistral Small":              ["Mistral"],
    "Devstral Medium":            ["Mistral"],
    "Devstral Small":             ["Mistral"],
    "Magistral Medium":           ["Mistral"],
    "Magistral Small":            ["Mistral"],
    # ── Cloudflare ───────────────────────────────────────────────────────────
    "GLM-4.7-Flash":              ["Cloudflare", "ZAI"],
    "QwQ 32B":                    ["Cloudflare"],
    "Qwen3 30B MoE":              ["Cloudflare"],
    "Qwen2.5 Coder 32B":          ["Cloudflare", "DashScope"],
    "Gemma 4 26B MoE":            ["Cloudflare", "OpenRouter"],
    "Mistral Small 3.1":          ["Cloudflare"],
    "Granite 4.0 Micro":          ["Cloudflare"],
    # ── OpenRouter-only ──────────────────────────────────────────────────────
    "MiniMax M2.5":               ["OpenRouter", "SambaNova"],
    "GLM 4.5 Air":                ["OpenRouter"],
    "Tencent HY3 Preview":        ["OpenRouter"],
    "Poolside Laguna M.1":        ["OpenRouter"],
    "Poolside Laguna XS.2":       ["OpenRouter"],
    "Ling 2.6 1T":                ["OpenRouter"],
    "Nemotron Nano 12B VL":       ["OpenRouter"],
    "Owl Alpha":                  ["OpenRouter"],
    "Hermes 3 405B":              ["OpenRouter"],
    "Dolphin Mistral 24B":        ["OpenRouter"],
    "Llama 3.2 3B":               ["OpenRouter"],
    "Nemotron Nano 9B":           ["OpenRouter"],
    "Gemma 3n E2B":               ["OpenRouter"],
    "Gemma 3 27B":                ["OpenRouter", "Scaleway"],
    "Gemma 4 31B MoE":            ["OpenRouter"],
    "Gemma 3 12B":                ["OpenRouter"],
    "Gemma 3n E4B":               ["OpenRouter"],
    "Gemma 3 4B":                 ["OpenRouter"],
    "LFM 2.5 1.2B":               ["OpenRouter"],
    "LFM 2.5 Thinking":           ["OpenRouter"],
    # ── SambaNova ────────────────────────────────────────────────────────────
    "DeepSeek V3.1":              ["SambaNova"],
    "DeepSeek V3.2":              ["SambaNova"],
    # ── OVHcloud ─────────────────────────────────────────────────────────────
    "Qwen3 Coder 30B MoE":        ["OVHcloud"],
    "Mistral Small 3.2":          ["OVHcloud", "Scaleway"],
    "Mistral 7B Instruct":        ["OVHcloud"],
    "Mistral Nemo":               ["OVHcloud"],
    "Qwen3.5 9B":                 ["OVHcloud"],
    # ── Codestral (Mistral free coding endpoint) ─────────────────────────────
    "Codestral":                  ["Codestral"],
    # ── ZAI ──────────────────────────────────────────────────────────────────
    "GLM-4.5-Flash":              ["ZAI"],
    # ── Scaleway ─────────────────────────────────────────────────────────────
    "Devstral 2 123B":            ["Scaleway"],
    "Qwen3 Coder 30B":            ["Scaleway"],
    "Holo2 30B":                  ["Scaleway"],
    # ── Alibaba DashScope ─────────────────────────────────────────────────────
    "Qwen3 Max":                  ["DashScope"],
    "Qwen3.5 Plus":               ["DashScope"],
    "Qwen3 Coder Plus":           ["DashScope"],
    "Qwen3 Coder Next":           ["DashScope"],
    "Qwen3.5 Flash":              ["DashScope"],
    "Qwen3 Coder Flash":          ["DashScope"],
}
# fmt: on

# Extra providers not in FCM (survive fcm_updater.refresh() overwrites).
# fmt: off
EXTRA_PROVIDERS: dict[str, list[str]] = {
    # ── Pollinations.ai (no-auth free API) ───────────────────────────────────
    "Kimi K2.6":                  ["Pollinations"],
    "GLM 4.7":                    ["Pollinations"],
    "Gemini 3 Flash Preview":     ["Pollinations"],
    "Qwen2.5 Coder 32B":          ["Pollinations"],
    "DeepSeek V3 0324":           ["Pollinations"],
    "MiniMax M2.5":               ["Pollinations"],
    "GPT OSS 20B":                ["Pollinations"],

    # ── LLM7.io (no-auth free API) ────────────────────────────────────────────
    "Codestral 2501":             ["LLM7"],
    "Llama 4 Scout":              ["LLM7"],
    "Mistral Large":              ["LLM7"],
    "Mistral Medium":             ["LLM7"],
    "Mistral Small 2503":         ["LLM7"],
    "Mistral Small 3.1":          ["LLM7"],
    "GPT-4.1 Nano":               ["LLM7"],
    "Mixtral 8x22B":              ["LLM7"],
}
# fmt: on

# Display priority: most user-relevant providers first.
# Used when truncating long provider lists in the table.
PROVIDER_PRIORITY: list[str] = [
    "OpenRouter",
    "Google AI",
    "GitHub",
    "NIM",
    "Groq",
    "Cerebras",
    "SambaNova",
    "Cloudflare",
    "Mistral",
    "Codestral",
    "Pollinations",
    "LLM7",
    "Scaleway",
    "OVHcloud",
    "DashScope",
    "ZAI",
]
