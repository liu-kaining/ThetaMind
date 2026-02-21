import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import AsyncSessionLocal
from app.db.models import Task, AIReport, User
from app.services.ai_service import ai_service
from app.api.endpoints.ai import check_ai_quota, increment_ai_usage
from app.core.config import settings

logger = logging.getLogger(__name__)

# Constants and Mappings
_AGENT_NAME_TO_PHASE_A_SUB_STAGE = {
    "Greeks": "greeks",
    "IV": "iv",
    "Market": "market",
    "Risk": "risk",
    "Synthesis": "synthesis",
}

def _add_execution_event(
    history: list[dict[str, Any]] | None, level: str, message: str, ts: datetime | None = None
) -> list[dict[str, Any]]:
    """Helper to append an event to the task execution history."""
    if history is None:
        history = []
    event = {
        "timestamp": (ts or datetime.now(timezone.utc)).isoformat(),
        "level": level,
        "message": message,
    }
    history.append(event)
    return history

def _update_stage(
    task: Task,
    stage_id: str,
    status: str,
    message: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    set_sub_stages_status: str | None = None,
) -> None:
    """Update a specific stage in task_metadata.stages."""
    if not task.task_metadata:
        task.task_metadata = {}
    stages = task.task_metadata.setdefault("stages", [])
    for stage in stages:
        if stage.get("id") == stage_id:
            stage["status"] = status
            if message:
                stage["message"] = message
            if started_at:
                stage["started_at"] = started_at.isoformat()
            if ended_at:
                stage["ended_at"] = ended_at.isoformat()
            if set_sub_stages_status and "sub_stages" in stage:
                for sub in stage["sub_stages"]:
                    sub["status"] = set_sub_stages_status
            return
    logger.warning(f"Stage {stage_id} not found in task_metadata.stages")


class DeepResearchOrchestrator:
    """
    Orchestrates the multi-agent deep research workflow.
    """

    def __init__(self, task_id: UUID, session: AsyncSession):
        self.task_id = task_id
        self.session = session
        self.loop = asyncio.get_running_loop()
        
    async def _emit_progress(self, progress: int, message: str) -> None:
        if self.loop is None:
            return
            
        async def update_progress_async() -> None:
            try:
                # We use a separate session for progress updates to avoid interfering
                # with the main orchestrator transaction state
                async with AsyncSessionLocal() as progress_session:
                    progress_result = await progress_session.execute(
                        select(Task).where(Task.id == self.task_id)
                    )
                    progress_task = progress_result.scalar_one_or_none()
                    if progress_task:
                        progress_task.execution_history = _add_execution_event(
                            progress_task.execution_history,
                            "progress",
                            f"[{progress}%] {message}",
                        )
                        if progress_task.task_metadata is None:
                            progress_task.task_metadata = {}
                        progress_task.task_metadata["progress"] = progress
                        progress_task.task_metadata["current_stage"] = message
                        progress_task.updated_at = datetime.now(timezone.utc)
                        await progress_session.commit()
            except Exception as e:
                logger.warning(f"Failed to update progress for task {self.task_id}: {e}")
                
        self.loop.create_task(update_progress_async())

    async def _update_phase_a_sub_stage(self, sub_stage_id: str, status: str) -> None:
        async def run_update():
            try:
                async with AsyncSessionLocal() as s:
                    res = await s.execute(select(Task).where(Task.id == self.task_id))
                    t = res.scalar_one_or_none()
                    if not t or not t.task_metadata: return
                    stages = t.task_metadata.get("stages", [])
                    modified = False
                    for stage in stages:
                        if stage.get("id") == "phase_a" and "sub_stages" in stage:
                            for sub in stage["sub_stages"]:
                                if sub.get("id") == sub_stage_id:
                                    sub["status"] = status
                                    modified = True
                    if modified:
                        t.updated_at = datetime.now(timezone.utc)
                        await s.commit()
            except Exception as e:
                logger.warning(f"Phase A sub-stage update error: {e}")
        self.loop.create_task(run_update())

    async def _update_phase_b_sub_stage(self, sub_stage_id: str, status: str) -> None:
        async def run_update():
            try:
                async with AsyncSessionLocal() as s:
                    res = await s.execute(select(Task).where(Task.id == self.task_id))
                    t = res.scalar_one_or_none()
                    if not t or not t.task_metadata: return
                    stages = t.task_metadata.get("stages", [])
                    modified = False
                    for stage in stages:
                        if stage.get("id") == "phase_b" and "sub_stages" in stage:
                            for sub in stage["sub_stages"]:
                                if sub.get("id") == sub_stage_id:
                                    sub["status"] = status
                                    modified = True
                    if modified:
                        t.updated_at = datetime.now(timezone.utc)
                        await s.commit()
            except Exception as e:
                logger.warning(f"Phase B sub-stage update error: {e}")
        self.loop.create_task(run_update())
        
    def _phase_a_progress_callback(self, progress: int, message: str) -> None:
        scaled = 5 + int(progress * 0.4)
        self.loop.create_task(self._emit_progress(scaled, f"Phase A: {message}"))
        
        if message.startswith("Agent "):
            rest = message[6:].strip()
            agent_name = None
            status = None
            if ": " in rest:
                part0, rest = rest.split(": ", 1)
                agent_name = part0.strip()
                rest_lower = rest.lower()
            else:
                parts = rest.rsplit(maxsplit=1)
                if len(parts) == 2:
                    agent_name, suffix = parts
                    rest_lower = suffix.lower()
                else:
                    rest_lower = rest.lower()
            if not agent_name:
                agent_name = rest.split()[0] if rest.split() else None
                
            if rest_lower:
                if "started" in rest_lower or "initializing" in rest_lower or "executing" in rest_lower:
                    status = "running"
                elif "succeeded" in rest_lower or "completed" in rest_lower:
                    status = "success"
                elif "failed" in rest_lower:
                    status = "failed"
                    
            if status and agent_name:
                sub_id = _AGENT_NAME_TO_PHASE_A_SUB_STAGE.get(agent_name)
                if sub_id:
                    self.loop.create_task(self._update_phase_a_sub_stage(sub_id, status))

    def _phase_b_progress_callback(self, progress: int, message: str) -> None:
        scaled = 50 + int(progress * 0.5)
        self.loop.create_task(self._emit_progress(scaled, f"Phase B: {message}"))
        
        m = message.lower()
        if "planning research" in m or ("planning" in m and "questions" in m):
            self.loop.create_task(self._update_phase_b_sub_stage("planning", "running"))
        elif "generated" in m and "research questions" in m:
            self.loop.create_task(self._update_phase_b_sub_stage("planning", "success"))
            self.loop.create_task(self._update_phase_b_sub_stage("research", "running"))
        elif "researching" in m and "parallel" in m:
            self.loop.create_task(self._update_phase_b_sub_stage("research", "running"))
        elif "research phase completed" in m or "synthesizing final" in m:
            self.loop.create_task(self._update_phase_b_sub_stage("research", "success"))
            self.loop.create_task(self._update_phase_b_sub_stage("synthesis", "running"))
        elif "deep research report completed" in m or "report completed" in m:
            self.loop.create_task(self._update_phase_b_sub_stage("synthesis", "success"))

    async def execute_workflow(self, task: Task, strategy_summary: dict[str, Any], option_chain: dict[str, Any], use_multi_agent: bool, preferred_model_id: str | None = None) -> None:
        """
        Executes the full multi-agent deep research workflow.
        """
        await self._emit_progress(5, "Phase A: Multi-agent analysis...")
        now_a = datetime.now(timezone.utc)
        _update_stage(task, "phase_a", "running", started_at=now_a)
        task.updated_at = now_a
        task.execution_history = _add_execution_event(
            task.execution_history,
            "info",
            "Starting Phase A: Multi-agent report generation...",
        )
        await self.session.commit()
        
        # Phase A
        PHASE_A_TIMEOUT = 480
        try:
            phase_a_result = await asyncio.wait_for(
                ai_service.generate_report_with_agents(
                    strategy_summary=strategy_summary,
                    use_multi_agent=use_multi_agent,
                    option_chain=option_chain,
                    progress_callback=self._phase_a_progress_callback,
                    preferred_model_id=preferred_model_id,
                ),
                timeout=PHASE_A_TIMEOUT,
            )
        except asyncio.TimeoutError:
            now_a_end = datetime.now(timezone.utc)
            _update_stage(task, "phase_a", "failed", ended_at=now_a_end, message="Phase A timed out (8 min)")
            task.updated_at = now_a_end
            await self.session.commit()
            raise ValueError("Multi-agent analysis timed out (8 min)") from None
            
        if isinstance(phase_a_result, dict):
            agent_summaries = phase_a_result.get("agent_summaries") or {}
            internal_preliminary_report = phase_a_result.get("internal_preliminary_report") or phase_a_result.get("report_text") or ""
        else:
            agent_summaries = {}
            internal_preliminary_report = ""
            
        if task.task_metadata is None:
            task.task_metadata = {}
        task.task_metadata["agent_summaries"] = agent_summaries
        now_a_end = datetime.now(timezone.utc)
        await self.session.refresh(task) 
        _update_stage(task, "phase_a", "success", ended_at=now_a_end, set_sub_stages_status="success")
        task.updated_at = now_a_end
        await self.session.commit()
        
        # Phase A+
        await self._emit_progress(45, "Phase A+: Strategy recommendation...")
        now_a_plus = datetime.now(timezone.utc)
        _update_stage(task, "phase_a_plus", "running", started_at=now_a_plus)
        task.updated_at = now_a_plus
        await self.session.commit()
        
        fundamental_profile = strategy_summary.get("fundamental_profile") or {}
        recommended_strategies: list[dict[str, Any]] = []
        if option_chain and agent_summaries:
            try:
                recommended_strategies = await ai_service.generate_strategy_recommendations(
                    option_chain=option_chain,
                    strategy_summary=strategy_summary,
                    fundamental_profile=fundamental_profile,
                    agent_summaries=agent_summaries,
                )
            except Exception as e:
                logger.warning(f"Phase A+ strategy recommendation failed: {e}", exc_info=True)
                
        task.task_metadata["recommended_strategies"] = recommended_strategies
        now_a_plus_end = datetime.now(timezone.utc)
        _update_stage(task, "phase_a_plus", "success", ended_at=now_a_plus_end)
        task.updated_at = now_a_plus_end
        await self.session.commit()
        
        # Phase B
        await self._emit_progress(50, "Phase B: Deep Research (planning, research, synthesis)...")
        now_b = datetime.now(timezone.utc)
        _update_stage(task, "phase_b", "running", started_at=now_b)
        task.updated_at = now_b
        await self.session.commit()
        
        PHASE_B_TIMEOUT = 1800 
        try:
            phase_b_result = await asyncio.wait_for(
                ai_service.generate_deep_research_report(
                    strategy_summary=strategy_summary,
                    option_chain=option_chain,
                    progress_callback=self._phase_b_progress_callback,
                    agent_summaries=agent_summaries,
                    recommended_strategies=recommended_strategies,
                    internal_preliminary_report=internal_preliminary_report,
                    preferred_model_id=preferred_model_id,
                ),
                timeout=PHASE_B_TIMEOUT,
            )
        except asyncio.TimeoutError:
            now_b_end = datetime.now(timezone.utc)
            _update_stage(
                task, "phase_b", "failed",
                ended_at=now_b_end,
                message="Phase B timed out (30 min)",
                set_sub_stages_status="failed",
            )
            task.updated_at = now_b_end
            await self.session.commit()
            raise ValueError("Deep Research timed out (30 min)") from None
            
        if isinstance(phase_b_result, dict):
            report_content = phase_b_result.get("report") or ""
            task.task_metadata["research_questions"] = phase_b_result.get("research_questions") or []
            full_prompt = phase_b_result.get("full_prompt")
            if full_prompt:
                task.prompt_used = full_prompt
        else:
            report_content = phase_b_result or ""
            full_prompt = None
            
        # Append input summary to report content (same as original logic)
        from app.api.endpoints.tasks import _build_input_summary
        input_summary, data_anomaly = _build_input_summary(strategy_summary, option_chain)
        if data_anomaly:
            input_summary += "\n**Confidence Adjustment:** Reduced due to missing Greeks.\n"
        report_content = f"{input_summary}\n{report_content}"
        
        now_b_end = datetime.now(timezone.utc)
        await self.session.refresh(task) 
        _update_stage(task, "phase_b", "success", ended_at=now_b_end, set_sub_stages_status="success")
        task.updated_at = now_b_end
        task.task_metadata["progress"] = 100
        task.task_metadata["current_stage"] = "Analysis complete"
        await self.session.commit()
        
        symbol = strategy_summary.get("symbol") or "the underlying"
        strategy_name = strategy_summary.get("strategy_name", "Multi-Agent Deep Research")
        
        # Save Report
        new_report = AIReport(
            user_id=task.user_id,
            report_content=report_content,
            model_used=task.model_used,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(new_report)
        await self.session.flush()
        await self.session.refresh(new_report)
        
        task.result_ref = str(new_report.id)
        task.status = "SUCCESS"
        task.completed_at = datetime.now(timezone.utc)
        task.updated_at = task.completed_at
        task.execution_history = _add_execution_event(
            task.execution_history, "success", f"Multi-agent deep research report successfully generated. Report ID: {new_report.id}",
            task.completed_at
        )
        
        # Deduct quota
        if task.user_id:
            user_result = await self.session.execute(select(User).where(User.id == task.user_id))
            user = user_result.scalar_one_or_none()
            if user:
                required_quota = 5 if use_multi_agent else 1
                await increment_ai_usage(user, self.session, cost=required_quota)
                task.execution_history = _add_execution_event(
                    task.execution_history, "info", f"Deducted {required_quota} AI units from user quota."
                )
                
        await self.session.commit()
        logger.info(f"Task {self.task_id} completed successfully (multi-agent)")
