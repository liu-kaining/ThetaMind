# Task, Multi-Agent & AI Call Flow - Verification Summary

**Last verified:** 2026-02-01 (Vertex URL rule: no-tools → publisher; with tools → project)

## 1. Task Creation & Processing

### Flow
```
POST /api/v1/tasks (or /api/v1/ai/report with async_mode=true)
  → create_task_async(db, user_id, task_type, metadata)
    → db.add(task), flush, refresh
    → db.commit()  ← CRITICAL: Must commit BEFORE scheduling so worker finds task
    → loop.create_task(safe_process_task())
  → process_task_async(task_id, task_type, metadata)
```

### Fixes Applied
- **Commit before schedule**: `await db.commit()` in `create_task_async` before `create_task(safe_process_task())` so the background worker can find the task (fixes "Task not found" / stuck PENDING).
- **Error handler**: When `safe_process_task` catches an exception, it updates task to FAILED if status is PENDING or PROCESSING.

## 2. Multi-Agent Report Flow (multi_agent_report)

### Pipeline
1. **Data Enrichment** → `_run_data_enrichment(strategy_summary)` injects:
   - fundamental_profile (FMP)
   - analyst_data, iv_context, upcoming_events, sentiment, historical_prices
   - `flag_modified(task, "task_metadata")` + commit for persistence
2. **Phase A** → `ai_service.generate_report_with_agents()`:
   - Coordinator runs: options_greeks_analyst, iv_environment_analyst, market_context_analyst (parallel)
   - risk_scenario_analyst (sequential)
   - options_synthesis_agent (sequential)
   - Each agent: `_call_ai(prompt)` → `generate_report({_agent_analysis_request, _agent_prompt, _agent_system_prompt})` → `_call_ai_api` → `_call_vertex_ai`
3. **Phase A+** → `generate_strategy_recommendations()` → `_call_gemini_with_search(use_search=False)`
4. **Phase B** → `generate_deep_research_report()`:
   - Planning → `_call_gemini_with_search(use_search=False)`
   - Research (4 questions) → `_call_gemini_with_search(use_search=True)` per question
   - Synthesis → `_call_gemini_with_search(use_search=False)`
5. Save report to AIReport, update task SUCCESS.

## 3. AI Call Paths (Vertex AI with AQ. key)

### Vertex AI (gemini-2.5-pro)

- **All calls** use **project/location URL** (`vertex_ai_project_url`). Publisher-only path returns 400.
- **Location**: For gemini-2.5-pro we use `location=us-central1` + v1beta1 for Search & JSON.
- **systemInstruction**: Sent in payload for gemini-2.5-pro (native support).

### GeminiProvider

| Call site | Method | URL | systemInstruction |
|-----------|--------|-----|-------------------|
| Report generation | _call_vertex_ai | project (us-central1) | In payload for 2.5-pro |
| Daily Picks | _call_vertex_ai | project (us-central1) | N/A |
| Strategy rec | _call_gemini_with_search | project (us-central1) | In payload if provided |
| Deep Research planning | _call_gemini_with_search(use_search=False) | project (us-central1) | In payload if provided |
| Deep Research research (4×) | _call_gemini_with_search(use_search=True) | project (us-central1) | In payload if provided |
| Deep Research final report | _call_gemini_with_search(use_search=False) | project (us-central1) | In payload if provided |

### systemInstruction
- gemini-2.5-pro and gemini-2.0-flash support `systemInstruction` in request body per Vertex AI docs.

### Image Generation (generate_strategy_chart)
- **Vertex AI HTTP** with `?key=` (same as text generation).
- Models tried: `gemini-3-pro-image-preview`, `gemini-2.5-flash-image`.
- Locations: `global`, `us-central1`.
- `generationConfig.responseModalities`: `["TEXT", "IMAGE"]`.

## 4. Environment Variables

```
GOOGLE_API_KEY=AQ....           # Vertex AI key
GOOGLE_CLOUD_PROJECT=<project>
GOOGLE_CLOUD_LOCATION=global    # or us-central1 for image models
AI_MODEL_DEFAULT=gemini-2.5-pro
```

## 5. Verification Checklist

- [x] Task commit before background scheduling
- [x] process_task_async finds task (no "Task not found")
- [x] Data enrichment + flag_modified + persist
- [x] Multi-agent agents call _call_ai → generate_report → _call_vertex_ai
- [x] systemInstruction in payload for gemini-2.5-pro
- [x] Deep Research uses _call_gemini_with_search (planning/research/synthesis)
- [x] Image gen uses Vertex AI HTTP with API key (no ADC)
- [x] Error handler updates FAILED for PENDING/PROCESSING

## 6. Restart Required

After code changes, restart backend to pick up updates:

```bash
docker compose restart backend
# or
docker compose up -d --build backend
```
