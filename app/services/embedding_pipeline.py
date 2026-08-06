import hashlib
import json
import time
import asyncio
import numpy as np
from typing import List, Tuple, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.config import settings
from app.core.logging import logger
from app.models.cost import OperationType
from app.services.cost_tracker import cost_tracker


class EmbeddingPipelineService:
    """Reusable service for generating semantic vector embeddings using Gemini Embeddings API."""

    def __init__(self):
        self.model_name = "text-embedding-004"
        self.dimension = 768

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generates deterministic, normalized 768-dimensional vector based on text hash for testing."""
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.randn(self.dimension).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    async def generate_embedding_with_retry(
        self,
        text: str,
        max_retries: int = 3
    ) -> Tuple[List[float], int]:
        """
        Generates 768-dim embedding vector using Gemini Embeddings API with retries.
        Returns (vector_list, estimated_input_tokens).
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty or whitespace text.")

        api_key = settings.GEMINI_API_KEY.strip()
        estimated_tokens = max(1, len(text.split()) * 2)

        # Fallback for mock/test environment
        if not api_key or api_key == "your-gemini-api-key-here" or api_key.startswith("mock"):
            logger.info(f"Generating mock embedding ({self.dimension}-dim) for text snippet (len={len(text)})")
            await asyncio.sleep(0.02)
            vector = self._generate_mock_embedding(text)
            return vector, estimated_tokens

        attempt = 0
        last_exception = None

        while attempt < max_retries:
            attempt += 1
            try:
                logger.info(f"Generating embedding attempt {attempt}/{max_retries} via {self.model_name}")
                import google.generativeai as genai
                genai.configure(api_key=api_key)

                response = genai.embed_content(
                    model=f"models/{self.model_name}",
                    content=text,
                    task_type="retrieval_document"
                )
                embedding_vector = response.get("embedding", [])
                if not embedding_vector or len(embedding_vector) != self.dimension:
                    raise ValueError(f"Received invalid embedding vector dimension: {len(embedding_vector)}")

                return embedding_vector, estimated_tokens

            except Exception as e:
                last_exception = e
                logger.warning(f"Embedding API attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"Embedding generation failed after {max_retries} attempts: {last_exception}")

    async def generate_and_store_image_embedding(
        self,
        db: AsyncSession,
        image_id: UUID,
        metadata_text: str,
        job_id: Optional[UUID] = None
    ) -> Tuple[List[float], Decimal]:
        """Generates embedding for an image's metadata prompt, logs cost, and stores record."""
        from app.repositories.embedding_repo import image_embedding_repo

        logger.info(f"Embedding started for image_id={image_id}")
        vector, input_tokens = await self.generate_embedding_with_retry(metadata_text)

        # Log Cost
        cost_log = await cost_tracker.log_cost(
            db=db,
            operation_type=OperationType.EMBEDDING_GEN,
            model_name=self.model_name,
            input_tokens=input_tokens,
            output_tokens=0,
            job_id=job_id
        )

        # Save/Update ImageEmbedding DB Record
        existing = await image_embedding_repo.get_by_image_id(db, image_id)
        if existing:
            existing.embedding = vector
            existing.dimension = len(vector)
            existing.status = "COMPLETED"
        else:
            await image_embedding_repo.create(
                db,
                {
                    "image_id": image_id,
                    "embedding": vector,
                    "model_name": self.model_name,
                    "dimension": len(vector),
                    "status": "COMPLETED"
                }
            )

        await db.commit()
        logger.info(f"Embedding stored for image_id={image_id} (dim={len(vector)})")
        return vector, cost_log.estimated_cost_usd

    async def generate_and_store_post_embedding(
        self,
        db: AsyncSession,
        post_id: UUID,
        title: str,
        content: str,
        summary: Optional[str] = None,
        job_id: Optional[UUID] = None
    ) -> Tuple[List[float], Decimal]:
        """Generates title, content, and combined embeddings for a blog post, logs cost, and stores record."""
        from app.repositories.embedding_repo import post_embedding_repo

        logger.info(f"Embedding started for blog post_id={post_id}")

        title_text = f"Title: {title}"
        content_text = f"Content: {content[:1500]}"
        combined_text = f"Title: {title}. Summary: {summary or title}. Content: {content[:2000]}"

        t_vec, t_tokens = await self.generate_embedding_with_retry(title_text)
        c_vec, c_tokens = await self.generate_embedding_with_retry(content_text)
        comb_vec, comb_tokens = await self.generate_embedding_with_retry(combined_text)

        total_tokens = t_tokens + c_tokens + comb_tokens

        # Log Cost
        cost_log = await cost_tracker.log_cost(
            db=db,
            operation_type=OperationType.EMBEDDING_GEN,
            model_name=self.model_name,
            input_tokens=total_tokens,
            output_tokens=0,
            job_id=job_id
        )

        # Save/Update PostEmbedding DB Record
        existing = await post_embedding_repo.get_by_post_id(db, post_id)
        if existing:
            existing.title_vector = t_vec
            existing.content_vector = c_vec
            existing.combined_vector = comb_vec
            existing.dimension = len(comb_vec)
        else:
            await post_embedding_repo.create(
                db,
                {
                    "post_id": post_id,
                    "title_vector": t_vec,
                    "content_vector": c_vec,
                    "combined_vector": comb_vec,
                    "model_name": self.model_name,
                    "dimension": len(comb_vec)
                }
            )

        await db.commit()
        logger.info(f"Embedding stored for post_id={post_id} (dim={len(comb_vec)})")
        return comb_vec, cost_log.estimated_cost_usd


embedding_pipeline = EmbeddingPipelineService()
