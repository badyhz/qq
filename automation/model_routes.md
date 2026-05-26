# Claude / DeepSeek Model Routes

## Commands
- Pro route: `cc-deep-pro`
- Flash route: `cc-deep-flash`
- Flash full/bypass route: `cc-deep-flash-full`
- Flash full aliases: `cc-deep-flash-bypass`, `cc-deep-flash-unsafe`
- MiMo full route: `cc-mimo-full`
- Backward compatible Pro alias: `cc-deep`

## Actual model mapping
- Pro: `deepseek-v4-pro[1m]`
- Flash (non-thinking): `deepseek-v4-flash`
- Flash Full / Bypass (non-thinking): `deepseek-v4-flash`
- MiMo Full / Bypass: `mimo-v2.5`

## Usage guidance
- Use `cc-deep-flash` for batch coding, quick edits, repetitive tasks, low-risk refactors.
- Use `cc-deep-pro` for trading execution chain, submit/flatten, position logic, and risk-sensitive changes.

## DeepSeek Flash Full / Bypass Route
- Command: `cc-deep-flash-full`
- Model: `deepseek-v4-flash`
- Permissions: Claude Code bypass permissions via `--dangerously-skip-permissions`
- Suitable for:
  - trusted local repo only
  - `pytest`
  - `py_compile`
  - `git status`/`git diff`/`git add`/`git commit` when task explicitly authorizes
  - batch low-risk local development tasks
- Not suitable for:
  - unknown repo
  - `curl|bash`
  - `rm -rf`
  - `chmod`/`chown` on system directories
  - production key environments
  - real trading submit/order/flatten commands
  - unauthorized edits to core execution/order/submit files

## Xiaomi MiMo Full Route
- Command: `cc-mimo-full`
- Claude Code endpoint type: Anthropic-compatible API
- Anthropic base URL env: `MIMO_ANTHROPIC_BASE_URL` (default `https://token-plan-cn.xiaomimimo.com/anthropic`)
- OpenAI base URL env (model discovery/OpenAI clients): `MIMO_BASE_URL` (default `https://token-plan-cn.xiaomimimo.com/v1`)
- API key env: `MIMO_API_KEY`
- Model: `mimo-v2.5`
- Permissions: Claude Code bypass permissions via `--dangerously-skip-permissions`

## Recommended task header
`Use cc-deep-flash-full only inside /Users/winnie/Documents/trae_projects/qq. Do not touch live trading commands. Do not read large CSV/JSONL/logs fully. Output only FILES / TESTS / RESULT / NOTES.`

## Verification commands
```bash
zsh -ic 'type cc-deep-flash-full; type cc-deep-flash; type cc-deep-pro; type cc-mimo-full || true'
zsh -ic 'cc-deep-flash-full -p "Reply with exactly: FLASH_FULL_OK"'
zsh -ic 'cc-deep-flash -p "Reply with exactly: FLASH_OK"'
zsh -ic 'cc-deep-pro -p "Reply with exactly: PRO_OK"'
zsh -ic 'cc-mimo-full -p "Reply with exactly: MIMO_FULL_OK"'
```

## Rollback
```bash
# Restore shell config
cp ~/.zshrc.bak.<timestamp> ~/.zshrc

# Restore route files if needed
cp deploy-routes.sh.bak.<timestamp> deploy-routes.sh
cp install-routes.sh.bak.<timestamp> install-routes.sh
cp claude-use-deepseek-flash.sh.bak.<timestamp> claude-use-deepseek-flash.sh
cp claude-use-mimo-full.sh.bak.<timestamp> claude-use-mimo-full.sh
cp automation/model_routes.md.bak.<timestamp> automation/model_routes.md

# Reload shell
source ~/.zshrc
```
