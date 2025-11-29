import logging
import re
from typing import Optional, List, Dict, Any, Tuple

from pydantic import ValidationError

# Import the JSON utilities
from ai_researcher.agentic_layer.utils.json_utils import (
    parse_llm_json_response,
    prepare_for_pydantic_validation
)

# Use absolute imports starting from the top-level package 'ai_researcher'
from ai_researcher.agentic_layer.agents.base_agent import BaseAgent
from ai_researcher.agentic_layer.model_dispatcher import ModelDispatcher
from ai_researcher import config
from ai_researcher.agentic_layer.schemas.notes import Note, NotesCritiqueOutput, VerificationStatus
from ai_researcher.agentic_layer.schemas.goal import GoalEntry
from ai_researcher.agentic_layer.schemas.thought import ThoughtEntry

logger = logging.getLogger(__name__)

class NotesCriticAgent(BaseAgent):
    """
    Agent responsible for critiquing notes, verifying accuracy against sources,
    detecting hallucinations, and checking alignment with mission goals.
    """
    def __init__(
        self,
        model_dispatcher: ModelDispatcher,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        controller: Optional[Any] = None
    ):
        agent_name = "NotesCriticAgent"
        # Determine model based on 'notes_critic' role in config, or fallback to 'mid'
        model_type = config.AGENT_ROLE_MODEL_TYPE.get("notes_critic", "mid") 
        
        if model_type == "fast":
            provider = config.FAST_LLM_PROVIDER
            effective_model_name = config.PROVIDER_CONFIG[provider]["fast_model"]
        elif model_type == "mid":
            provider = config.MID_LLM_PROVIDER
            effective_model_name = config.PROVIDER_CONFIG[provider]["mid_model"]
        elif model_type == "intelligent":
            provider = config.INTELLIGENT_LLM_PROVIDER
            effective_model_name = config.PROVIDER_CONFIG[provider]["intelligent_model"]
        else:
            logger.warning(f"Unknown model type '{model_type}', falling back to mid.")
            provider = config.MID_LLM_PROVIDER
            effective_model_name = config.PROVIDER_CONFIG[provider]["mid_model"]

        effective_model_name = model_name or effective_model_name

        super().__init__(
            agent_name=agent_name,
            model_dispatcher=model_dispatcher,
            tool_registry=None, # No tools needed for direct critique (context is provided)
            system_prompt=system_prompt or self._default_system_prompt(),
            model_name=effective_model_name
        )
        self.controller = controller
        self.mission_id = None

    def _default_system_prompt(self) -> str:
        """Generates the default system prompt for the Notes Critic Agent."""
        return """You are a meticulous Research Auditor. Your task is to verify the quality, accuracy, and alignment of a research note against its source material and the mission's goals. You do not generate new content; you rigorously critique existing content.

Your primary responsibilities are:
1. **Hallucination Detection:** Verify if the note's claims are supported by the provided 'Source Context'. Flag any information that is not present in the source.
2. **Source Alignment:** Ensure the note accurately reflects the source's meaning without distortion or omission of critical context.
3. **Goal Alignment:** Check if the note is relevant to the 'Section Goal' and 'Active Mission Goals'.
4. **Quality Check:** Evaluate if the note is clear, concise, and properly structured.

Based on your audit, provide:
1. An 'overall_assessment' of the note.
2. A 'source_alignment' report (aligned: bool, coverage %, unsupported claims).
3. A list of 'hallucinations_detected' (if any).
4. 'suggested_refinements' to improve accuracy or clarity.
5. A 'verification_status' (passed, revise, unchecked).
6. A 'scratchpad_update' and 'generated_thought'.

Output ONLY a JSON object conforming to the NotesCritiqueOutput schema.
"""

    async def run(
        self,
        note: Note,
        section_goal: str,
        active_goals: Optional[List[GoalEntry]] = None,
        active_thoughts: Optional[List[ThoughtEntry]] = None,
        agent_scratchpad: Optional[str] = None,
        mission_id: Optional[str] = None,
        log_queue: Optional[Any] = None,
        update_callback: Optional[Any] = None
    ) -> Tuple[Optional[NotesCritiqueOutput], Optional[Dict[str, Any]], Optional[str]]:
        """
        Critiques a note against its source and goals.
        """
        self.mission_id = mission_id
        
        logger.info(f"{self.agent_name}: Critiquing note {note.note_id} (source: {note.source_id})...")
        scratchpad_update = None

        # Prepare context
        scratchpad_context = f"\nCurrent Agent Scratchpad:\n---\n{agent_scratchpad}\n---\n" if agent_scratchpad else ""
        
        goals_str = "\n".join([f"- {g.text}" for g in active_goals]) if active_goals else "None"
        active_goals_context = f"\nActive Mission Goals:\n---\n{goals_str}\n---\n"
        
        thoughts_context = ""
        if active_thoughts:
            thoughts_str = "\n".join([f"- {t.content}" for t in active_thoughts])
            thoughts_context = f"\nRecent Thoughts:\n---\n{thoughts_str}\n---\n"

        # Source context from note metadata
        source_context = "Source Snippet/Content:\n---\n"
        if note.source_metadata.snippet:
             source_context += f"{note.source_metadata.snippet}\n"
        else:
             source_context += "(No source snippet available)\n"
        source_context += f"Source ID: {note.source_id}\nTitle: {note.source_metadata.title}\n---\n"

        prompt = f"""Please critique the following research note.

Note to Verify:
---
ID: {note.note_id}
Content: {note.content}
Structured Analysis: {note.structured_analysis if note.structured_analysis else 'None'}
---

{source_context}

Section Goal:
{section_goal}

{active_goals_context}
{scratchpad_context}
{thoughts_context}

Task: Verify the note's accuracy against the source snippet, check for hallucinations, and assess relevance to the section goal. Output ONLY a JSON object conforming to the NotesCritiqueOutput schema.
"""

        messages = [{"role": "user", "content": prompt}]
        model_call_details = None
        
        try:
            response, model_call_details = await self._call_llm(
                user_prompt=prompt,
                agent_mode="notes_critic",
                response_format={"type": "json_object"},
                log_queue=log_queue,
                update_callback=update_callback
            )

            if response and response.choices and response.choices[0].message.content:
                json_str = response.choices[0].message.content
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)

                try:
                    parsed_json = parse_llm_json_response(json_str)
                    # Ensure note_id matches
                    parsed_json['note_id'] = note.note_id 
                    
                    prepared_data = prepare_for_pydantic_validation(parsed_json, NotesCritiqueOutput)
                    response_model = NotesCritiqueOutput(**prepared_data)
                    scratchpad_update = response_model.scratchpad_update
                    
                    logger.info(f"{self.agent_name}: Critique complete. Status: {response_model.verification_status}")
                    return response_model, model_call_details, scratchpad_update
                except Exception as e:
                    logger.error(f"{self.agent_name}: Failed to parse response: {e}", exc_info=True)
                    return None, model_call_details, scratchpad_update
            else:
                logger.error(f"{self.agent_name}: LLM call failed.")
                return None, model_call_details, scratchpad_update

        except Exception as e:
            logger.error(f"{self.agent_name}: Error during critique: {e}", exc_info=True)
            return None, model_call_details, scratchpad_update
