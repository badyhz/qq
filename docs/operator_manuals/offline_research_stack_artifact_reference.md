# Offline Research Stack Artifact Reference

## Pipeline Artifacts

### Workbench Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `workbench_results.json` | JSON | Raw backtest results per strategy/symbol/timeframe |
| `workbench_manifest.json` | JSON | Workbench manifest with run parameters |

### Quality Gate Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `quality_gate.json` | JSON | Quality validation results |
| `manifest.json` | JSON | Quality manifest with safety flags |
| `quality_report.md` | MD | Human-readable quality report |
| `quality_report.html` | HTML | Standalone HTML quality report |

### Artifact Browser Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `artifact_index.json` | JSON | Indexed artifact catalog |
| `artifact_browser/` | Directory | Browseable artifact collection |
| `browser_report.html` | HTML | Standalone browser report |

### Comparison Analytics Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `comparison_report.json` | JSON | Pairwise comparison results |
| `quality_series.json` | JSON | Quality metric time series |
| `scorecard.json` | JSON | Strategy scorecard |
| `comparison_report.md` | MD | Human-readable comparison report |

### Human Review Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `review_packet.json` | JSON | Complete review packet |
| `review_checklist.json` | JSON | 17-item review checklist |
| `review_checklist.md` | MD | Markdown checklist |
| `review_signoff_template.json` | JSON | Signoff template |
| `review_signoff_template.md` | MD | Markdown signoff template |
| `review_audit_trail.json` | JSON | Audit trail with hashes |
| `review_audit_trail.md` | MD | Markdown audit trail |
| `human_review_report.md` | MD | Full review report (14 sections) |
| `human_review_report.html` | HTML | Standalone HTML review report |
| `review_manifest.json` | JSON | Review manifest |

### Governance Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `governance_validation.json` | JSON | Governance validation results |
| `governance_validation.md` | MD | Governance report |
| `governance_manifest.json` | JSON | Governance manifest |

### Experiment Library Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `experiment_library_validation.json` | JSON | Library validation results |
| `experiment_library_manifest.json` | JSON | Library manifest |
| `experiment_full_manifest.json` | JSON | Full experiment manifest |

### Operator Bundle Output
| Artifact | Format | Description |
|----------|--------|-------------|
| `operator_bundle_index.json` | JSON | Bundle index |
| `operator_bundle_manifest.json` | JSON | Bundle manifest |
| `operator_bundle.md` | MD | Bundle markdown |
| `operator_bundle.html` | HTML | Standalone HTML bundle |
| `command_cheatsheet.md` | MD | Command cheatsheet |
| `safety_cheatsheet.md` | MD | Safety cheatsheet |
| `recovery_index.md` | MD | Recovery index |
| `experiment_catalog_summary.md` | MD | Experiment catalog summary |

## Fixture Artifacts

| Fixture | Path | Description |
|---------|------|-------------|
| Historical OHLCV | `tests/fixtures/historical_backtest_lab/` | BTC/ETH 5m/15m data |
| Research Quality | `tests/fixtures/research_quality/` | Quality gate fixtures |
| Human Review | `tests/fixtures/research_human_review/` | Review workflow fixtures |
| Experiment Library | `tests/fixtures/offline_research_experiment_library/` | Experiment catalog |

## Safety

All artifacts are advisory only. release_hold = HOLD. No artifact authorizes live/testnet/runtime/planner execution.
