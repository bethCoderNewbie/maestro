from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Literal, ClassVar, Optional
from datetime import datetime
from enum import Enum
import uuid

# --- NEW ENUMS FOR AGENTIC LOGIC ---
class NoteType(str, Enum):
    FLEETING = "fleeting"       # Raw copy-paste or quick thought
    LITERATURE = "literature"   # Synthesized summary of a source
    PERMANENT = "permanent"     # Atomic, self-contained idea (Zettelkasten)

class VerificationStatus(str, Enum):
    UNCHECKED = "unchecked"
    PASSED = "passed"
    REVISE = "revise"

# --- EXISTING METADATA (Unchanged) ---
class SourceMetadata(BaseModel):
    """Metadata about the source of a note."""
    title: Optional[str] = Field(None, description="Title of the source document")
    year: Optional[str] = Field(None, description="Publication year")
    original_filename: Optional[str] = Field(None, description="Original filename")
    snippet: Optional[str] = Field(None, description="Text snippet from source")
    authors: Optional[str] = Field(None, description="Authors of the source")
    url: Optional[str] = Field(None, description="URL if web source")
    
    # Additional fields found in existing data
    beginning_omitted: Optional[bool] = Field(None, description="Whether content was omitted from beginning")
    end_omitted: Optional[bool] = Field(None, description="Whether content was omitted from end")
    original_chunk_ids: Optional[List[str]] = Field(None, description="List of original chunk IDs")
    window_position: Optional[Dict[str, int]] = Field(None, description="Window position with start and end")
    overlapping_chunks: Optional[List[Dict[str, Any]]] = Field(None, description="Information about overlapping chunks")
    fetched_full_content: Optional[bool] = Field(None, description="Whether full content was fetched")
    keywords: Optional[str] = Field(None, description="Keywords from the source")
    abstract: Optional[str] = Field(None, description="Abstract from the source")
    publication_year: Optional[int] = Field(None, description="Publication year as integer")
    doc_id: Optional[str] = Field(None, description="Document ID")
    
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='allow')

# --- NEW STRUCTURED ANALYSIS COMPONENT ---
class NoteAnalysis(BaseModel):
    """
    Detailed breakdown of the note content for high-quality synthesis.
    This replaces the 'blob string' approach for complex notes.
    """
    core_argument: Optional[str] = Field(None, description="One sentence summary of the main point.")
    key_findings: List[str] = Field(default_factory=list, description="List of specific facts or discoveries.")
    methodology: Optional[str] = Field(None, description="How the information was derived (if scientific).")
    quotes: List[str] = Field(default_factory=list, description="Verbatim quotes with page/loc references.")
    critical_analysis: Optional[str] = Field(None, description="Agent's critique of the source's strength/weakness.")

# --- UPGRADED NOTE MODEL ---
class Note(BaseModel):
    """
    Represents a single piece of information gathered during research.
    Enhanced for Multi-Agent verification and synthesis.
    """
    note_id: str = Field(default_factory=lambda: f"note_{uuid.uuid4().hex[:8]}", description="Unique identifier for the note.")
    
    # 1. PRIMARY CONTENT (Backward Compatible)
    content: str = Field(..., description="The main textual content/summary of the note.")
    
    # 2. STRUCTURED CONTENT (New - For "Literature" notes)
    structured_analysis: Optional[NoteAnalysis] = Field(None, description="Structured breakdown for high-value notes.")
    
    # 3. SOURCE TRACKING
    source_type: Literal["document", "web", "internal"] = Field(..., description="The origin type.")
    source_id: str = Field(..., description="Identifier for the specific source.")
    source_metadata: SourceMetadata = Field(default_factory=SourceMetadata)
    
    # 4. CONTEXT & LINKING
    potential_sections: List[str] = Field(default_factory=list, description="List of relevant outline section IDs.")
    note_type: NoteType = Field(default=NoteType.FLEETING, description="The classification of the note.")
    tags: List[str] = Field(default_factory=list, description="Semantic tags (e.g., #Hallucination, #Ethics).")
    
    # 5. AGENT VERIFICATION STATE (New - For the Critic Agent)
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNCHECKED, description="Status from the Critic Agent.")
    verification_feedback: Optional[str] = Field(None, description="Feedback or reasoning provided by the Critic Agent.")
    
    # 6. TIMESTAMPS
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of creation.")
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of last update.")
    is_relevant: bool = Field(default=True, description="Flag indicating relevance.")

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid')
