import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ParentNode(BaseModel):
    """Parent chunk representing a full section or chapter."""
    id: UUID = Field(default_factory=uuid4)
    attachment_id: Optional[UUID] = None
    section_title: str
    token_count: int
    content: str


class ChildNode(BaseModel):
    """Child chunk representing a focused passage linked to a ParentNode."""
    id: UUID = Field(default_factory=uuid4)
    parent_id: UUID
    chunk_index: int
    content: str
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)


class ParentChildSplitter:
    """Hierarchically splits Markdown documents into Parent and Child nodes."""

    def __init__(
        self,
        parent_size: int = 1500,
        child_size: int = 200,
        child_overlap: int = 20,
    ) -> None:
        self.parent_size = parent_size
        self.child_size = child_size
        self.child_overlap = child_overlap

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximates token count using whitespace and punctuation splitting."""
        return max(1, len(re.findall(r"\w+|[^\w\s]", text, re.UNICODE)))

    def _split_into_sections(self, markdown_text: str) -> List[Tuple[str, str]]:
        """Splits markdown by header tags (# , ## , ### )."""
        lines = markdown_text.splitlines()
        sections: List[Tuple[str, List[str]]] = []
        current_title = "Wstęp"
        current_lines: List[str] = []

        header_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            match = header_pattern.match(line.strip())
            if match:
                if current_lines:
                    sections.append((current_title, current_lines))
                current_title = match.group(2).strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_title, current_lines))

        # Join lines for each section
        result: List[Tuple[str, str]] = []
        for title, l_list in sections:
            content = "\n".join(l_list).strip()
            if content:
                result.append((title, content))

        if not result and markdown_text.strip():
            result.append(("Dokument główny", markdown_text.strip()))

        return result

    def _split_text_into_child_chunks(self, text: str) -> List[str]:
        """Splits section content into overlapping child chunks."""
        words = text.split()
        if not words:
            return []

        chunks: List[str] = []
        step = max(1, self.child_size - self.child_overlap)
        for i in range(0, len(words), step):
            chunk_words = words[i : i + self.child_size]
            chunk_str = " ".join(chunk_words).strip()
            if chunk_str:
                chunks.append(chunk_str)

        return chunks

    def split(
        self,
        markdown_text: str,
        attachment_id: Optional[UUID] = None,
    ) -> Tuple[List[ParentNode], List[ChildNode]]:
        """Splits markdown document into linked ParentNode and ChildNode collections."""
        raw_sections = self._split_into_sections(markdown_text)
        parents: List[ParentNode] = []
        children: List[ChildNode] = []

        for title, content in raw_sections:
            tokens = self._estimate_tokens(content)
            parent = ParentNode(
                attachment_id=attachment_id,
                section_title=title,
                token_count=tokens,
                content=content,
            )
            parents.append(parent)

            child_texts = self._split_text_into_child_chunks(content)
            for idx, c_text in enumerate(child_texts):
                child = ChildNode(
                    parent_id=parent.id,
                    chunk_index=idx,
                    content=c_text,
                    metadata_payload={
                        "section_title": title,
                        "token_count": self._estimate_tokens(c_text),
                    },
                )
                children.append(child)

        return parents, children
