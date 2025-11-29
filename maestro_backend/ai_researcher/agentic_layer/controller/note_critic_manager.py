import logging
import queue
from typing import Optional, Callable, Dict, Any, List
from ai_researcher.agentic_layer.async_context_manager import ExecutionLogEntry
from ai_researcher.agentic_layer.schemas.notes import Note, VerificationStatus
from ai_researcher.agentic_layer.controller.utils.status_checks import acheck_mission_status, check_mission_status_async

logger = logging.getLogger(__name__)

class NoteCriticManager:
    """
    Manages the critique and verification of research notes.
    """
    def __init__(self, controller):
        self.controller = controller

    @acheck_mission_status
    async def critique_all_notes(
        self,
        mission_id: str,
        log_queue: Optional[queue.Queue] = None,
        update_callback: Optional[Callable[[queue.Queue, ExecutionLogEntry], None]] = None
    ):
        """
        Runs the NoteCriticAgent on all unchecked notes for the mission.
        """
        mission_context = self.controller.context_manager.get_mission_context(mission_id)
        if not mission_context:
             logger.error(f"Mission {mission_id} not found")
             return

        active_goals = self.controller.context_manager.get_active_goals(mission_id)
        active_thoughts = self.controller.context_manager.get_recent_thoughts(mission_id)
        scratchpad = self.controller.context_manager.get_scratchpad(mission_id)

        notes_to_critique = [
            n for n in mission_context.notes 
            if n.verification_status == VerificationStatus.UNCHECKED
        ]
        
        logger.info(f"Starting critique for {len(notes_to_critique)} notes in mission {mission_id}")

        processed_count = 0
        for note in notes_to_critique:
             # Check status per note
             if not await check_mission_status_async(self.controller, mission_id):
                 logger.info(f"Mission {mission_id} stopped during critique.")
                 break

             # Infer section goal (fallback to user request if no specific assignment)
             section_goal = mission_context.user_request
             # Optional: Look up potential sections in plan to get better goal
             
             critique_output, _, scratchpad_update = await self.controller.notes_critic_agent.run(
                 note=note,
                 section_goal=section_goal,
                 active_goals=active_goals,
                 active_thoughts=active_thoughts,
                 agent_scratchpad=scratchpad,
                 mission_id=mission_id,
                 log_queue=log_queue,
                 update_callback=update_callback
             )
             
             if critique_output:
                 await self.controller.context_manager.update_note_verification(
                     mission_id=mission_id,
                     note_id=note.note_id,
                     status=critique_output.verification_status,
                     feedback=critique_output.overall_assessment,
                     critique_result=critique_output
                 )
                 
                 if scratchpad_update:
                      await self.controller.context_manager.update_scratchpad(mission_id, scratchpad_update)
                      scratchpad = scratchpad_update # Update local ref
                 
                 processed_count += 1

        await self.controller.context_manager.log_execution_step(
            mission_id, "NoteCriticManager", "Batch Critique",
            output_summary=f"Critiqued {processed_count} notes.",
            status="success",
            log_queue=log_queue, update_callback=update_callback
        )
