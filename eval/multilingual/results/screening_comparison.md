# Quick screening: model comparison

Identical frozen case set (`SCREEN_5`) x 3 languages = 15 queries per model, scored against the same 3x English baseline.

**This is a filter, not a measurement.** Five cases per language cannot support a confident percentage -- one case moves any rate by 20 points. It is here to decide which model earns a full 60-query run.

## Comparison

| Model | FR | AR | HI | Avg Latency | Routing | Entity Preservation | Translation Quality | Errors |
|---|---|---|---|---|---|---|---|---|
| `gemma4:31b` | 4/4 (97.0s) | 4/4 (100.6s) | 4/4 (102.4s) | 101.5s added / 101.9s total | 100.0% (12/12) | 100.0% (12/12) | 4.54/5 | 0 |
| `qwen3:14b` | 3/4 (25.4s) | 4/4 (26.3s) | 4/4 (42.0s) | 29.8s added / 32.7s total | 91.7% (11/12) | 100.0% (12/12) | 4.62/5 | 0 |
| `qwen2.5:14b` | 3/4 (14.6s) | 3/4 (15.8s) | 2/4 (33.7s) | 25.7s added / 25.8s total | 91.7% (11/12) | 75.0% (9/12) | 4.65/5 | 0 |
| `qwen2.5:7b` | 2/4 (13.0s) | 2/4 (13.0s) | 3/4 (16.4s) | 16.6s added / 19.0s total | 75.0% (9/12) | 83.3% (10/12) | 4.51/5 | 0 |

Language cells show *clean passes* (routing **and** entity preservation, no errors) out of cases scored, with median added latency in brackets. Latency still reflects every case run.

### Excluded from scoring

- **`cp03`** - The English pipeline mis-parses 'compare this month vs last month DBR01': it takes the word 'this' as a report name and offers IRS / Phising / FMRD10_Hedg_Comm_Price_Freight_Risk_Ove as candidates, ignoring DBR01. Reproduces identically across all 3 baseline runs, so it is a deterministic pipeline bug rather than noise. A model that renders the query as 'compare DBR01 for this month with last month' AVOIDS the bug and resolves DBR01 correctly -- scoring that as a routing miss would penalise the better translation.

## Latency detail (p50 / p95)

| Model | Inbound | Outbound | Total added | Pipeline | End-to-end |
|---|---|---|---|---|---|
| `gemma4:31b` | 39.0s / 52.7s | 57.8s / 69.6s | **101.5s / 114.7s** | 0.3s / 3.3s | 101.9s / 114.7s |
| `qwen3:14b` | 8.8s / 15.9s | 22.6s / 45.0s | **29.8s / 61.0s** | 0.3s / 43.2s | 32.7s / 68.6s |
| `qwen2.5:14b` | 10.1s / 15.1s | 15.6s / 99.8s | **25.7s / 110.8s** | 0.2s / 72.0s | 25.8s / 182.8s |
| `qwen2.5:7b` | 5.9s / 9.2s | 11.8s / 22.2s | **16.6s / 28.8s** | 0.5s / 72.0s | 19.0s / 90.4s |

## Translation quality by axis (LLM-as-judge, 1-5)

| Model | inbound_adequacy | inbound_fluency | inbound_terminology | outbound_adequacy | outbound_fluency | outbound_terminology |
|---|---|---|---|---|---|---|
| `gemma4:31b` | 4.75 | 4.5 | 5.0 | 4.25 | 4.0 | 4.75 |
| `qwen3:14b` | 4.75 | 4.5 | 5.0 | 4.75 | 4.08 | 4.67 |
| `qwen2.5:14b` | 4.75 | 4.5 | 5.0 | 4.92 | 4.08 | 4.67 |
| `qwen2.5:7b` | 4.67 | 4.58 | 5.0 | 4.33 | 4.17 | 4.33 |

_Judged by a third model, different family from both candidates, so neither is marking its own homework. Advisory only._

## Judge blind spots

Cases the objective checks failed but the LLM judge rated 4+ for adequacy. Where these exist, the Translation Quality column is not trustworthy and the objective columns must carry the decision.

| Model | Case | Lang | Judge adequacy | Objective violations | Actual output |
|---|---|---|---|---|---|
| `qwen2.5:14b` | `st01` | fr | 5/5 | 3 | `J'ai trouvé 3 rapports correspondants. Lequel recherchez-vou` |
| `qwen2.5:14b` | `st01` | ar | 5/5 | 4 | `وجدت ثلاثة تقارير متطابقة. أيها الذي تبحث عنه؟  1. RAQ(ربع س` |
| `qwen2.5:14b` | `st01` | hi | 4/5 | 7 | `मैंने 3 उपाय म` |
| `qwen2.5:14b` | `cp03` | hi | 5/5 | 10 | `3` |
| `qwen2.5:7b` | `st01` | fr | 5/5 | 1 | `1. RAQ(Quarterly) 2. RAQ(Monthly) 3. RAQ(Annually)` |
| `qwen2.5:7b` | `st01` | ar | 5/5 | 1 | `1. RAQ(Quarterly) 2. RAQ(Monthly) 3. RAQ(Annually)` |
| `qwen2.5:7b` | `cp03` | hi | 5/5 | 10 | `3` |

## Per-case detail

### `gemma4:31b`

| Case | Lang | Routing | Entities | Added | Notes |
|---|---|---|---|---|---|
| `st01` | fr | ok | ok | 107.1s | - |
| `cp03` | fr | **MISS** | ok | 89.8s | compare_reports -> compare_reports |
| `dq09` | fr | ok | ok | 97.0s | - |
| `dq13` | fr | ok | ok | 114.7s | - |
| `cv01` | fr | ok | ok | 89.9s | - |
| `st01` | ar | ok | ok | 106.7s | - |
| `cp03` | ar | **MISS** | ok | 92.9s | compare_reports -> compare_reports |
| `dq09` | ar | ok | ok | 100.6s | - |
| `dq13` | ar | ok | ok | 109.8s | - |
| `cv01` | ar | ok | ok | 90.2s | - |
| `st01` | hi | ok | ok | 102.4s | - |
| `cp03` | hi | ok | ok | 122.9s | - |
| `dq09` | hi | ok | ok | 94.4s | - |
| `dq13` | hi | ok | ok | 108.0s | - |
| `cv01` | hi | ok | ok | 87.8s | - |

### `qwen3:14b`

| Case | Lang | Routing | Entities | Added | Notes |
|---|---|---|---|---|---|
| `st01` | fr | ok | ok | 33.0s | - |
| `cp03` | fr | **MISS** | ok | 15.6s | compare_reports -> compare_reports |
| `dq09` | fr | ok | ok | 17.7s | - |
| `dq13` | fr | ok | ok | 28.6s | - |
| `cv01` | fr | **MISS** | ok | 25.4s | conversational -> unknown |
| `st01` | ar | ok | ok | 47.0s | - |
| `cp03` | ar | **MISS** | ok | 15.7s | compare_reports -> compare_reports |
| `dq09` | ar | ok | ok | 30.9s | - |
| `dq13` | ar | ok | ok | 26.3s | - |
| `cv01` | ar | ok | ok | 16.8s | - |
| `st01` | hi | ok | ok | 61.0s | - |
| `cp03` | hi | ok | ok | 42.0s | - |
| `dq09` | hi | ok | ok | 28.7s | - |
| `dq13` | hi | ok | ok | 53.1s | - |
| `cv01` | hi | ok | ok | 35.6s | - |

### `qwen2.5:14b`

| Case | Lang | Routing | Entities | Added | Notes |
|---|---|---|---|---|---|
| `st01` | fr | ok | **FAIL** | 32.3s | entity `RAQ(Annually)` lost; entity `RAQ(Monthly)` lost; entity `RAQ(Quarterly)` lost |
| `cp03` | fr | **MISS** | ok | 14.6s | compare_reports -> compare_reports |
| `dq09` | fr | ok | ok | 14.6s | - |
| `dq13` | fr | ok | ok | 24.2s | - |
| `cv01` | fr | ok | ok | 14.4s | - |
| `st01` | ar | ok | **FAIL** | 43.7s | number `3` lost; entity `RAQ(Annually)` lost; entity `RAQ(Monthly)` lost |
| `cp03` | ar | **MISS** | ok | 14.1s | compare_reports -> compare_reports |
| `dq09` | ar | ok | ok | 15.8s | - |
| `dq13` | ar | ok | ok | 23.6s | - |
| `cv01` | ar | ok | ok | 14.1s | - |
| `st01` | hi | ok | **FAIL** | 33.7s | number `1` lost; number `2` lost; number `3` lost |
| `cp03` | hi | ok | **FAIL** | 12.1s | number `1` lost; number `10` lost; number `2` lost |
| `dq09` | hi | ok | ok | 27.2s | - |
| `dq13` | hi | **MISS** | ok | 110.8s | reports_filed_in_range -> db_submission_list |
| `cv01` | hi | ok | ok | 43.3s | - |

### `qwen2.5:7b`

| Case | Lang | Routing | Entities | Added | Notes |
|---|---|---|---|---|---|
| `st01` | fr | ok | **FAIL** | 13.0s | number `3` lost |
| `cp03` | fr | **MISS** | ok | 8.7s | compare_reports -> compare_reports |
| `dq09` | fr | ok | ok | 11.8s | - |
| `dq13` | fr | **MISS** | ok | 19.0s | reports_filed_in_range -> db_submission_list |
| `cv01` | fr | ok | ok | 23.9s | - |
| `st01` | ar | ok | **FAIL** | 19.6s | number `3` lost |
| `cp03` | ar | **MISS** | ok | 11.4s | compare_reports -> compare_reports |
| `dq09` | ar | **MISS** | ok | 16.8s | return_field -> generate_instance; invented number `03`; invented number `06` |
| `dq13` | ar | ok | ok | 13.0s | - |
| `cv01` | ar | ok | ok | 9.5s | invented number `03`; invented number `2025` |
| `st01` | hi | ok | ok | 28.8s | - |
| `cp03` | hi | ok | **FAIL** | 6.5s | number `1` lost; number `10` lost; number `2` lost |
| `dq09` | hi | ok | ok | 15.6s | - |
| `dq13` | hi | **MISS** | ok | 28.3s | reports_filed_in_range -> db_submission_list |
| `cv01` | hi | ok | ok | 16.4s | - |
