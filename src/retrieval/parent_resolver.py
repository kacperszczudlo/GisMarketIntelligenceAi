import logging
from typing import Any, Dict, List
from uuid import UUID
from src.database.connection import db_manager

logger = logging.getLogger(__name__)


class ParentNodeResolver:
    """Resolves child chunk results to their corresponding full ParentNode chapters in PostgreSQL."""

    def resolve(self, child_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetches full parent nodes for the provided child candidates, preserving rank ordering and deduplicating."""
        if not child_candidates:
            return []

        # Maintain first-seen order of parent_ids to preserve top relevance ranking
        ordered_parent_ids: List[str] = []
        parent_max_scores: Dict[str, float] = {}

        for c in child_candidates:
            p_id = str(c.get("parent_id"))
            if not p_id or p_id == "None":
                continue
            score = float(c.get("cross_encoder_score", c.get("rrf_score", c.get("score", 0.0))))

            if p_id not in ordered_parent_ids:
                ordered_parent_ids.append(p_id)
                parent_max_scores[p_id] = score
            else:
                parent_max_scores[p_id] = max(parent_max_scores[p_id], score)

        if not ordered_parent_ids:
            return []

        with db_manager.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, attachment_id, section_title, token_count, content
                FROM parent_nodes
                WHERE id = ANY(%s::uuid[]);
                """,
                (ordered_parent_ids,),
            )
            rows = cur.fetchall()

        parent_dict: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            p_id_str = str(r[0])
            parent_dict[p_id_str] = {
                "id": p_id_str,
                "attachment_id": str(r[1]),
                "section_title": r[2],
                "token_count": r[3],
                "content": r[4],
                "score": parent_max_scores.get(p_id_str, 0.0),
            }

        # Return resolved parents in the order of top ranked relevance
        results: List[Dict[str, Any]] = []
        for p_id in ordered_parent_ids:
            if p_id in parent_dict:
                results.append(parent_dict[p_id])

        return results
