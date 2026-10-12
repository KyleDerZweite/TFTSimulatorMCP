# Qwen and historical comp research

Investigated on 2026-10-12. This note distinguishes upstream recommendations, locally tested behavior and proposals. Actual target results belong in [verification.md](verification.md).

## Model and host

[Qwen's official Qwen3.5-4B model card](https://huggingface.co/Qwen/Qwen3.5-4B) recommends Qwen-Agent, with `Assistant`, `model_type="qwenvl_oai"` and `generate_cfg.use_raw_api=True`. Its vLLM examples use Qwen3 reasoning parsing and Qwen3-Coder tool parsing. Qwen3's prompt switches `/think` and `/nothink` are not supported controls for Qwen3.5. These recommendations do not require replacing a standard MCP server.

[Qwen-Agent's MCP guide](https://qwenlm.github.io/Qwen-Agent/en/guide/core_moduls/mcp/) accepts an `mcpServers` block in `function_list`. Its [function-call agent](https://github.com/QwenLM/Qwen-Agent/blob/main/qwen_agent/agents/fncall_agent.py) owns the model/tool/result loop. The model inference service does not execute MCP tools itself. Python stdio tools need the MCP extra, without GUI, RAG, code-interpreter or Node dependencies.

The [MCP wrapper](https://github.com/QwenLM/Qwen-Agent/blob/main/qwen_agent/tools/mcp_manager.py) prefixes tool names with the server key, for example `tft-get_decision`. It forwards root `type`, `properties` and `required` to the model and can discard other root schema fields. TFT's server must still enforce the complete schema. Keep tool properties self-contained; root `$defs` referenced by a property could be stripped by this host. An engine adapter's presence is not end-to-end acceptance evidence.

[Ollama's official model listing](https://ollama.com/library/qwen3.5:4b) supports tools and thinking. The tag is mutable. Record the resolved digest and quantization, not only `qwen3.5:4b`. Download size excludes runtime context and cache memory.

[Ollama's OpenAI-compatible endpoint](https://docs.ollama.com/api/openai-compatibility) supports tool calls and `reasoning_effort="none"` for disabling thinking on a boolean thinking model. The [native thinking API](https://docs.ollama.com/capabilities/thinking) uses `think=false`. Do not assume that vLLM's `chat_template_kwargs` controls Ollama. Verify forwarding through the actual host. The OpenAI endpoint does not accept per-request context size; Ollama documents a derived Modelfile with `PARAMETER num_ctx` for that purpose. The investigated local test host used an explicitly configured 32K alias and preserved the base model. That optional host was withdrawn when the owner chose Codex. Qwen's card suggests temperature 0.7 and top_p 0.8 for general non-thinking use; that is a starting configuration, not a TFT optimum.

[Ollama's context guidance](https://docs.ollama.com/context-length) recommends at least 64,000 tokens for agent workloads. Qwen's card recommends at least 128K to preserve complex thinking capability. A per-round non-thinking conversation with a smaller context is a constrained experiment. Inspect actual allocation with `ollama ps`; the model's 262,144-token capacity does not mean that context is allocated locally. No global Ollama settings or existing model templates need to change for this project.

## Server choices

Reduce repeated category reads and empty slot records. Return visible state after a turn so the host can continue the conversation with actual observations. Keep legal individual action tools, strict validation, atomic failure recovery and a simulator-owned rules catalog. A local model still needs explicit tool schemas and a host that preserves tool responses. Neither copying a model prompt template into the MCP server nor reimplementing Qwen's parser improves that separation.

For a future Qwen host, use its official agent loop and fresh per-round conversations against the same MCP process to bound history. Preserve an explicit game/action budget and reject omitted tools in the compact profile. Retain full/default tools for other clients. Measure byte volume, invalid calls, successful decisions and latency separately. A byte reduction is not a measured improvement in strategic play.

## Original Set 4 MetaTFT data

MetaTFT's author described original Set 4 clustering in a [2020-09-18 first-party post](https://www.reddit.com/r/CompetitiveTFT/comments/iv88yl/metatft_top_comps_of_set_4_so_far/). The post discusses Gold+ matches, multiple variants within each group and missing Chosen information in the TFT API. It establishes that historical analysis existed, without supplying a reproducible comp export with complete winrates, sample counts and patch identifiers.

The inspected [current comps page](https://www.metatft.com/comps) did not expose a documented original Set 4 CSV/JSON archive. Direct requests received HTTP 403. A Wayback CDX request received HTTP 503, so archived payload availability remains unverified. These observations do not establish that no historical data exists.

A [Sett page with `set=TFTSet4_Act2`](https://www.metatft.com/units/Sett?set=TFTSet4_Act2) showed current patch/time-window metadata and placeholders. `Act2` identifies a different rules period; this page does not prove access to original Set 4 statistics. [MetaTFT's app guide](https://ghost.metatft.com/how-to-use-the-metatft-app/) also distinguishes round win rate and final placement. These metrics cannot be substituted for one another.

[MetaTFT's terms](https://www.metatft.com/tos) state ownership of platform data/content. No reusable downloadable-data license was identified in the inspected sources. A local or redistributed dataset needs a documented permitted source. This note records source availability and terms; it does not supply a legal conclusion.

Even an original Set 4 export would need validation against the installed simulator's champion, trait and item definitions and revision. Historical live TFT winrates do not establish simulator performance against `Default_Agent(False)`. Do not copy a current or revival catalog, invent winrates, or ask a model to turn unsupported guesses into a database.

A future small offline catalog could accept curated builds with source, patch, rule compatibility, phase and explicitly available metrics. One bounded `find_comps` query with phase and optional unit/trait filters would avoid three nearly identical tools. That remains a proposal until usable data and its contract are accepted.
