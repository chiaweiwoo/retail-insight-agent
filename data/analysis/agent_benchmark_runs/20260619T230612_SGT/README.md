# RCA Agent Benchmark Run

- run timestamp (SGT): `20260619T230612_SGT`
- model: `deepseek-v4-flash`
- scenario count: `6`

## Scenario Outputs

| scenario_id | expected_signal | observed_signal | store_alias | dt | analysts | tool_call_count | report_md | report_html | trace | logs |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- |
| drop_high_h555_2024-05-16 | drop | drop | h555 | 2024-05-16 | 4 | 10 | [report.md](drop_high_h555_2024-05-16/report.md) | [report.html](drop_high_h555_2024-05-16/report.html) | [trace](drop_high_h555_2024-05-16/manager_trace.json) | [logs](drop_high_h555_2024-05-16/logs/event_log.md) |
| drop_medium_m041_2024-05-09 | drop | drop | m041 | 2024-05-09 | 4 | 10 | [report.md](drop_medium_m041_2024-05-09/report.md) | [report.html](drop_medium_m041_2024-05-09/report.html) | [trace](drop_medium_m041_2024-05-09/manager_trace.json) | [logs](drop_medium_m041_2024-05-09/logs/event_log.md) |
| drop_low_l165_2024-05-16 | drop | drop | l165 | 2024-05-16 | 4 | 17 | [report.md](drop_low_l165_2024-05-16/report.md) | [report.html](drop_low_l165_2024-05-16/report.html) | [trace](drop_low_l165_2024-05-16/manager_trace.json) | [logs](drop_low_l165_2024-05-16/logs/event_log.md) |
| lift_high_h235_2024-05-05 | lift | lift | h235 | 2024-05-05 | 4 | 10 | [report.md](lift_high_h235_2024-05-05/report.md) | [report.html](lift_high_h235_2024-05-05/report.html) | [trace](lift_high_h235_2024-05-05/manager_trace.json) | [logs](lift_high_h235_2024-05-05/logs/event_log.md) |
| lift_medium_m041_2024-05-12 | lift | lift | m041 | 2024-05-12 | 4 | 10 | [report.md](lift_medium_m041_2024-05-12/report.md) | [report.html](lift_medium_m041_2024-05-12/report.html) | [trace](lift_medium_m041_2024-05-12/manager_trace.json) | [logs](lift_medium_m041_2024-05-12/logs/event_log.md) |
| lift_low_l185_2024-04-13 | lift | lift | l185 | 2024-04-13 | 4 | 15 | [report.md](lift_low_l185_2024-04-13/report.md) | [report.html](lift_low_l185_2024-04-13/report.html) | [trace](lift_low_l185_2024-04-13/manager_trace.json) | [logs](lift_low_l185_2024-04-13/logs/event_log.md) |

## Quick Checks

- compare `expected_signal` vs `observed_signal` for trigger alignment
- review `tool_call_count` for prompt/tool efficiency drift
- inspect markdown tone and evidence strength in each report
