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
from app.utils.vector_math import rank_candidates_by_similarity


class MatchingEngineService:
    """Semantic Relevance Engine comparing blog post embeddings with catalog image embeddings."""

    def _generate_match_reasoning(
        self,
        post_title: str,
        post_tags: List[str],
        image_metadata: Optional[any],
        similarity_score: float
    ) -> str:
        """Generates human-readable explanation of why the image matched the blog post."""
        if not image_metadata:
            return f"Semantic vector similarity score: {similarity_score:.3f}."

        # Extract shared terms between post title/tags and image metadata tags/subject
        post_words = set(post_title.lower().split()).union({t.lower() for t in post_tags})
        img_words = set(image_metadata.tags or []).union(
            set(image_metadata.primary_subject.lower().split())
        )

        shared = post_words.intersection(img_words) - {"the", "a", "an", "in", "on", "and", "or", "of", "to", "for", "with"}

        if shared:
            shared_str = ", ".join(list(shared)[:5])
            reasoning = (
                f"Strong semantic match (similarity score: {similarity_score:.3f}). "
                f"Shared visual & topic concepts include: {shared_str}. "
                f"Image subject: '{image_metadata.primary_subject}'."
            )
        else:
            reasoning = (
                f"High contextual embedding alignment (similarity score: {similarity_score:.3f}). "
                f"Image visual description: '{image_metadata.caption}'."
            )
        return reasoning

    async def generate_matches_for_post(
        self,
        db: AsyncSession,
        post_id: UUID,
        top_k: int = 5
    ) -> List[Suggestion]:
        """
        Executes Top-K candidate retrieval and ranking for a blog post based on embedding vector similarity.
        """
        logger.info(f"Matching started for blog post_id={post_id}")

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
        logger.info(f"Ranking complete: Top {len(top_candidates)} candidate images ranked")

        # Clear existing suggestions for this post
        await suggestion_repo.delete_by_post_id(db, post_id)

        suggestions: List[Suggestion] = []

        for idx, (img_id, score) in enumerate(top_candidates, start=1):
            meta = await metadata_repo.get_by_image_id(db, img_id)
            reason = self._generate_match_reasoning(
                post_title=post.title,
                post_tags=post.tags or [],
                image_metadata=meta,
                similarity_score=score
            )

            suggestion_rec = await suggestion_repo.create(
                db,
                {
                    "post_id": post_id,
                    "image_id": img_id,
                    "raw_similarity_score": score,
                    "guard_confidence_score": 1.0,
                    "final_score": score,
                    "rank": idx,
                    "match_status": MatchStatus.MATCHED,
                    "match_reasoning": reason,
                    "is_reviewed": False
                }
            )
            suggestions.append(suggestion_rec)

        await db.commit()
        logger.info(f"Matching pipeline complete: {len(suggestions)} suggestions persisted for post_id={post_id}")
        return suggestions


matching_engine = MatchingEngineService()
