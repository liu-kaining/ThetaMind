# Task, Multi-Agent & AI Call Flow - Verification Summary

**Last verified:** 2026-01-31

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

### GeminiProvider

| Call site | Method | Vertex AI | systemInstruction |
|-----------|--------|-----------|-------------------|
| Agents _call_ai | generate_report | _call_vertex_ai | Prepend to prompt (gemini-3-pro doesn't support it) |
| Strategy rec | _call_gemini_with_search(use_search=False) | Vertex HTTP | N/A |
| Deep Research | _call_gemini_with_search | Vertex HTTP | Prepend if needed |
| Daily Picks | _call_vertex_ai | Vertex HTTP | N/A |

### systemInstruction Fix
- Per Vertex AI docs, `systemInstruction` only applies to `gemini-2.0-flash*`.
- For `gemini-3-pro-preview`: prepend system prompt to user prompt to avoid 400 "invalid argument".

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
AI_MODEL_DEFAULT=gemini-3.0-pro-preview
```

## 5. Verification Checklist

- [x] Task commit before background scheduling
- [x] process_task_async finds task (no "Task not found")
- [x] Data enrichment + flag_modified + persist
- [x] Multi-agent agents call _call_ai → generate_report → _call_vertex_ai
- [x] systemInstruction prepended for gemini-3-pro (no 400)
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
