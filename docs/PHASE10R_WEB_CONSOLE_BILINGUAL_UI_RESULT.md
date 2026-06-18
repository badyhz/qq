# Phase 10R: Web Console Bilingual UI

## Summary

Added bilingual (zh/en) support to local shadow web console. Default language is Chinese. Supports `?lang=zh` and `?lang=en` URL parameters. No cookies, no sessions, no config files.

## Files Modified

- `core/paper_trading/shadow_web_console.py` — added:
  - `SUPPORTED_LANGS` — `{"zh", "en"}`
  - `UI_TEXT` — translation dictionary with all UI strings in zh and en
  - `normalize_lang()` — normalizes lang code, falls back to "zh" for invalid values
  - `t()` — translation helper function
  - Updated all render functions to accept `lang` parameter:
    - `render_dashboard_html(..., lang="zh")`
    - `render_positions_table(..., lang="zh")`
    - `render_scorecard_table(..., lang="zh")`
    - `render_sample_gate_card(..., lang="zh")`
    - `render_recent_actions_table(..., lang="zh")`
    - `render_strategy_switchboard_table(..., lang="zh")`
    - `render_config_change_form(..., lang="zh")`
    - `render_config_change_result(..., lang="zh")`
  - Language switcher HTML with `?lang=zh` / `?lang=en` links
  - CSS for `.lang-switch` styling

- `scripts/run_shadow_web_console.py` — updated:
  - Added `normalize_lang` import
  - Reads `lang` from query parameters in `do_GET()`
  - Passes `lang` to `render_dashboard_html()`
  - Added `--lang` argument for smoke render

- `tests/unit/test_shadow_web_console.py` — updated:
  - Updated existing tests to check Chinese text (default language)
  - Added English variants for key tests
  - Added `TestNormalizeLang` (4 tests)
  - Added `TestBilingualUI` (11 tests)
  - Added `TestUILayout` (1 test)
  - Total: 140 tests

## Language Switch

- URL: `/?lang=zh`, `/?lang=en`
- Default: `zh`
- Invalid values: fallback to `zh`
- No cookies, no sessions, no localStorage
- Page right corner: `[中文] | [English]` links

## Translated Sections

| Key | zh | en |
|-----|----|----|
| title | 影子交易控制台 | Shadow Trading Console |
| section_status | 状态 | Status |
| section_actions | 操作 | Actions |
| section_reports | 报告 | Reports |
| section_positions | 纸面持仓 | Paper Positions |
| section_scorecard | 策略评分 | Strategy Scorecard |
| section_gate | 样本门禁 | Sample Gate |
| section_recent_actions | 最近操作 | Recent Actions |
| section_switchboard | 策略开关 | Strategy Switchboard |
| section_config_change | 策略配置变更草案 | Strategy Config Change Request |
| btn_lifecycle | 扫描新机会 + 更新持仓 | Scan New Opportunities + Update Positions |
| btn_update_only | 只更新已有持仓 | Update Existing Positions Only |
| btn_sample_gate | 刷新样本门禁 | Refresh Sample Gate |
| btn_print_status | 打印当前状态 | Print Current Status |
| safety_footer | 仅纸面 \| 仅影子 \| 仅本地 \| ... | Paper-only \| Shadow-only \| Local-only \| ... |

Status values (sample_status, testnet_gate_status, etc.) are NOT translated — they are system codes.

## Safety

- No config write
- No cookies/sessions/localStorage
- Local-only binding
- No testnet/live
- No order/account/secret
- Language only affects display text

## Commit Plan

```bash
git add core/paper_trading/shadow_web_console.py tests/unit/test_shadow_web_console.py
git commit -m "Add bilingual web console UI"

git add scripts/run_shadow_web_console.py
git commit -m "Support web console language parameter"

git add docs/PHASE10R_WEB_CONSOLE_BILINGUAL_UI_RESULT.md
git commit -m "Document bilingual web console UI"
```
