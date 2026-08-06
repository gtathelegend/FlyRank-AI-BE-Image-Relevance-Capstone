from typing import List, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.suggestion import Suggestion, MatchStatus
from app.repositories.post_repo import post_repo
from app.repositories.image_repo import image_repo
from app.repositories.metadata_repo import metadata_repo
from app.repositories.embedding_repo import post_embedding_repo, image_embedding_repo
from app.repositories.suggestion_repo import suggestion_repo
from app.services.mismatch_guard import mismatch_guard
from app.utils.vector_math import rank_candidates_by_similarity


class MatchingEngineService:
    """Semantic Relevance Engine comparing blog post embeddings with catalog image embeddings, protected by Mismatch Guard."""

    async def generate_matches_for_post(
        self,
        db: AsyncSession,
        post_id: UUID,
        top_k: int = 5
    ) -> List[Suggestion]:
        """
        Executes Top-K candidate retrieval, Mismatch Guard verification, and persistence.
        Prefer 'No confident match' over weak or conflicting recommendations.
        """
        logger.info(f"Matching pipeline started for blog post_id={post_id}")

        post = await post_repo.get(db, post_id)
        if not post:
            raise ValueError(f"BlogPost with ID '{post_id}' not found.")

        post_emb = await post_embedding_repo.get_by_post_id(db, post_id)
        if not post_emb:
            raise ValueError(f"No vector embedding found for blog post '{post_id}'. Ensure post is indexed.")

        # Load all candidate image embeddings
        image_embs = await image_embedding_repo.get_multi(db, skip=0, limit=1000)
        if not image_embs:
            logger.warning(f"No catalog image embeddings found for matching against post_id={post_id}")
            return []

        logger.info(f"Candidates found: {len(image_embs)} catalog image vectors loaded for matching")

        # Rank candidates using cosine similarity on combined_vector
        candidates = [(emb.image_id, emb.embedding) for emb in image_embs]
        ranked_results = rank_candidates_by_similarity(post_emb.combined_vector, candidates)

        # Select Top-K candidates
        top_candidates = ranked_results[:top_k]
        logger.info(f"Ranking complete: Top {len(top_candidates)} candidate images ranked by vector similarity")

        # Clear existing suggestions for this post before re-evaluating
        await suggestion_repo.delete_by_post_id(db, post_id)

        suggestions: List[Suggestion] = []
        valid_match_count = 0

        for idx, (img_id, raw_score) in enumerate(top_candidates, start=1):
            meta = await metadata_repo.get_by_image_id(db, img_id)

            # Evaluate candidate against Mismatch Guard
            is_valid, guard_conf, guard_reason = await mismatch_guard.evaluate_candidate(
                db=db,
                post_title=post.title,
                post_content=post.content,
                raw_similarity=raw_score,
                image_metadata=meta
            )

            if is_valid:
                match_status = MatchStatus.MATCHED
                final_score = float(raw_score)
                valid_match_count += 1
            else:
                match_status = MatchStatus.REJECTED_BY_GUARD
                final_score = float(raw_score * 0.5)  # Penalized score for guard rejection

            suggestion_rec = await suggestion_repo.create(
                db,
                {
                    "post_id": post_id,
                    "image_id": img_id,
                    "raw_similarity_score": raw_score,
                    "guard_confidence_score": guard_conf,
                    "final_score": final_score,
                    "rank": idx,
                    "match_status": match_status,
                    "match_reasoning": guard_reason,
                    "is_reviewed": False
                }
            )
            suggestions.append(suggestion_rec)

        await db.commit()

        if valid_match_count == 0:
            logger.info(f"Mismatch Guard active: No confident match found for post_id={post_id}. Rejected {len(suggestions)} weak/conflicting candidates.")
        else:
            logger.info(f"Matching pipeline complete: {valid_match_count} accepted & {len(suggestions) - valid_match_count} guard-rejected suggestions stored for post_id={post_id}")

        return suggestions


matching_engine = MatchingEngineService()
