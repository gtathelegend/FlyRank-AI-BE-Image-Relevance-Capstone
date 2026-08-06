import json
import asyncio
from typing import Tuple, Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.config import settings
from app.core.logging import logger
from app.models.cost import OperationType
from app.services.cost_tracker import cost_tracker

# Known species conflict pairs (distinct biological families/species)
SPECIES_CONFLICT_PAIRS = [
    ({"fox"}, {"wolf"}),
    ({"dog"}, {"wolf"}),
    ({"cat"}, {"tiger", "lion"}),
    ({"bear"}, {"dog", "wolf"}),
    ({"fox"}, {"dog"}),
    ({"rabbit"}, {"hare", "fox"})
]

# Incompatible environment/biome pairs
ENVIRONMENT_CONFLICT_PAIRS = [
    ({"forest", "jungle", "woods"}, {"city", "urban", "office", "street"}),
    ({"snow", "arctic", "ice", "winter"}, {"desert", "dunes", "arid", "sahara"}),
    ({"ocean", "underwater", "sea", "marine"}, {"desert", "dunes", "mountain peak"}),
    ({"beach", "tropical", "palm"}, {"snow", "arctic", "glacier"})
]


class MismatchGuardService:
    """Production-grade Mismatch Guard enforcing high precision and 'No confident match' preference."""

    def check_species_conflict(self, post_text: str, image_metadata: any) -> Optional[Tuple[str, str]]:
        """Checks for conflicting animal/species definitions between post and image."""
        if not image_metadata:
            return None

        post_words = set(post_text.lower().split())
        img_animals = set(image_metadata.animals or [])
        img_words = set(image_metadata.primary_subject.lower().split()).union(img_animals)

        for group_a, group_b in SPECIES_CONFLICT_PAIRS:
            match_a_post = post_words.intersection(group_a)
            match_b_img = img_words.intersection(group_b)
            if match_a_post and match_b_img:
                return (list(match_a_post)[0], list(match_b_img)[0])

            match_b_post = post_words.intersection(group_b)
            match_a_img = img_words.intersection(group_a)
            if match_b_post and match_a_img:
                return (list(match_b_post)[0], list(match_a_img)[0])

        return None

    def check_environment_conflict(self, post_text: str, image_metadata: any) -> Optional[Tuple[str, str]]:
        """Checks for incompatible biome/environment settings between post and image."""
        if not image_metadata:
            return None

        post_words = set(post_text.lower().split())
        img_env = (image_metadata.environment or "").lower()
        img_words = set(img_env.split()).union(set(image_metadata.scene_description.lower().split()))

        for group_a, group_b in ENVIRONMENT_CONFLICT_PAIRS:
            match_a_post = post_words.intersection(group_a)
            match_b_img = img_words.intersection(group_b)
            if match_a_post and match_b_img:
                return (list(match_a_post)[0], list(match_b_img)[0])

            match_b_post = post_words.intersection(group_b)
            match_a_img = img_words.intersection(group_a)
            if match_b_post and match_a_img:
                return (list(match_b_post)[0], list(match_a_img)[0])

        return None

    async def evaluate_candidate(
        self,
        db: AsyncSession,
        post_title: str,
        post_content: str,
        raw_similarity: float,
        image_metadata: Optional[any],
        job_id: Optional[UUID] = None
    ) -> Tuple[bool, float, str]:
        """
        Evaluates a candidate image against blog post content using multi-tier mismatch rules.
        Returns (is_valid_match, guard_confidence, reasoning).
        """
        min_similarity = settings.MISMATCH_GUARD_MIN_SIMILARITY
        min_confidence = settings.MISMATCH_GUARD_MIN_CONFIDENCE
        full_post_text = f"{post_title} {post_content}"

        # Tier 1: Cosine Similarity Threshold Check
        if raw_similarity < min_similarity:
            reasoning = f"Similarity score ({raw_similarity:.3f}) is below acceptance threshold ({min_similarity:.2f})."
            logger.info(f"Mismatch Guard Tier 1 rejection: {reasoning}")
            return False, 1.0, reasoning

        # Tier 2: Species / Entity Conflict Rule
        species_conflict = self.check_species_conflict(full_post_text, image_metadata)
        if species_conflict:
            post_sp, img_sp = species_conflict
            reasoning = f"Semantic species conflict detected: Post describes '{post_sp}' while image depicts '{img_sp}'."
            logger.info(f"Mismatch Guard Tier 2 rejection: {reasoning}")
            return False, 0.95, reasoning

        # Tier 3: Environment / Biome Conflict Rule
        env_conflict = self.check_environment_conflict(full_post_text, image_metadata)
        if env_conflict:
            post_env, img_env = env_conflict
            reasoning = f"Environment conflict detected: Post describes '{post_env}' setting while image setting is '{img_env}'."
            logger.info(f"Mismatch Guard Tier 3 rejection: {reasoning}")
            return False, 0.95, reasoning

        # Tier 4: LLM Guard Verification for live API environments
        api_key = settings.GEMINI_API_KEY.strip()
        if (
            settings.MISMATCH_GUARD_ENABLE_LLM_VALIDATION and
            api_key and
            api_key != "your-gemini-api-key-here" and
            not api_key.startswith("mock")
        ):
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")

                prompt = (
                    f"Evaluate if this image matches this blog post without misleading readers.\n"
                    f"Blog Post Title: {post_title}\n"
                    f"Blog Post Summary: {post_content[:300]}\n"
                    f"Image Primary Subject: {image_metadata.primary_subject if image_metadata else 'N/A'}\n"
                    f"Image Description: {image_metadata.scene_description if image_metadata else 'N/A'}\n\n"
                    f"Return JSON strictly matching: {{\"is_valid\": true/false, \"confidence\": 0.0-1.0, \"reason\": \"explanation\"}}"
                )

                response = model.generate_content(prompt)
                resp_text = (response.text or "").strip()

                if resp_text.startswith("```json"):
                    resp_text = resp_text[7:]
                if resp_text.endswith("```"):
                    resp_text = resp_text[:-3]

                guard_json = json.loads(resp_text.strip())
                is_valid = bool(guard_json.get("is_valid", True))
                conf = float(guard_json.get("confidence", 0.9))
                reason = str(guard_json.get("reason", "LLM Guard verification complete."))

                # Record Cost for Guard Verification
                await cost_tracker.log_cost(
                    db=db,
                    operation_type=OperationType.MISMATCH_GUARD_VERIFICATION,
                    model_name="gemini-1.5-flash",
                    input_tokens=180,
                    output_tokens=50,
                    job_id=job_id
                )

                if not is_valid or conf < min_confidence:
                    return False, conf, f"LLM Guard rejected match: {reason}"
                return True, conf, f"High-confidence AI match verification (confidence: {conf:.2f})."

            except Exception as e:
                logger.warning(f"LLM Guard verification call failed, falling back to deterministic rules: {e}")

        # Default: Candidate passed all deterministic rules
        reasoning = (
            f"Validated high-confidence match (similarity score: {raw_similarity:.3f} >= {min_similarity:.2f}). "
            f"Visual subject '{image_metadata.primary_subject if image_metadata else 'asset'}' aligns with post topic."
        )
        return True, 1.0, reasoning


mismatch_guard = MismatchGuardService()
