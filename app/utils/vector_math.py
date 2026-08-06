import numpy as np
from typing import List, Tuple, Union



def cosine_similarity(v1: Union[List[float], np.ndarray], v2: Union[List[float], np.ndarray]) -> float:
    """
    Computes cosine similarity between two 1D vector arrays.
    Returns normalized float score in range [0.0, 1.0].
    """
    a = np.asarray(v1, dtype=np.float32)
    b = np.asarray(v2, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    dot_product = float(np.dot(a, b))
    similarity = dot_product / (float(norm_a) * float(norm_b))

    # Clamp to [0.0, 1.0] range (cosine similarity can be [-1.0, 1.0], normalized to positive [0.0, 1.0])
    normalized = (similarity + 1.0) / 2.0 if similarity < 0 else similarity
    return float(np.clip(normalized, 0.0, 1.0))


def rank_candidates_by_similarity(
    query_vector: List[float],
    candidate_vectors: List[Tuple[any, List[float]]]
) -> List[Tuple[any, float]]:
    """
    Ranks candidates by cosine similarity against query_vector.
    candidate_vectors: List of (candidate_identifier, vector) tuples.
    Returns sorted list of (candidate_identifier, similarity_score) descending.
    """
    scored = []
    for candidate_id, vec in candidate_vectors:
        score = cosine_similarity(query_vector, vec)
        scored.append((candidate_id, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
