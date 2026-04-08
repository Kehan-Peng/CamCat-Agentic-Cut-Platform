import hashlib
import math
import re
from abc import ABC, abstractmethod


TOKEN_PATTERN = re.compile(r"[\w]+|[\u4e00-\u9fff]{2,}")


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = 64) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in tokenize_text(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left, right))


def tokenize_text(text: str) -> list[str]:
    normalized = text.lower().replace("/", " ").replace(",", " ")
    tokens = TOKEN_PATTERN.findall(normalized)
    return [token for token in tokens if token]
