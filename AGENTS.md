# TFTSimulatorMCP

Read SPEC.md before implementation and GLOSSARY.md for domain terms. This repository owns the MCP server, documentation and tests. Use ordinary Python and the existing concrete adapter; do not add a generic dispatcher or provider framework.

The installed simulator is an external dependency. Do not vendor or modify Simulator code, rules or defaults. Rules come from its installed definitions without a fixed set label, set selector or copied catalog. Pin the tested upstream Git revision and verify installed source identity.

Code belongs in src/tft_mcp/, tests in tests/, shared prompts and packaging in the root, and detailed documentation in docs/. Preserve the tft_mcp import and tft-mcp launcher. SPEC.md owns module responsibilities and protocol behavior.

Use checkout source for developer checks. Verify installed acceptance from outside both checkouts without PYTHONPATH. Record actual MCP and simulator revisions separately, failures and unexecuted evidence in docs/verification.md. Preserve operator configuration, credentials and retained logs.

Before delegated writers edit, verify the actual repository, isolated worktree, branch, base and local changes. Integrate sequentially after focused tests and review. Publication and changes to other repositories remain parent-owned work within owner authorization.
