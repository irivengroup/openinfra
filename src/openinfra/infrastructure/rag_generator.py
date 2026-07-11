from __future__ import annotations

import re

from openinfra.application.ports import RagGeneratorPort
from openinfra.domain.rag import RagCitation, RagTextProcessor


class DeterministicRagGenerator(RagGeneratorPort):
    _SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")

    def generate(self, question: str, citations: tuple[RagCitation, ...]) -> str:
        if not citations:
            return (
                "Aucune source autorisée et suffisamment pertinente ne permet de répondre "
                "à cette question. Reformulez la demande ou faites indexer une source approuvée."
            )
        terms = set(RagTextProcessor.terms(question))
        statements: list[str] = []
        seen: set[str] = set()
        for index, citation in enumerate(citations, start=1):
            candidates = [
                item.strip() for item in self._SENTENCE.split(citation.excerpt) if item.strip()
            ]
            if not candidates:
                candidates = [citation.excerpt]
            selected = max(
                candidates,
                key=lambda item: (
                    len(terms.intersection(RagTextProcessor.terms(item))),
                    min(len(item), 400),
                ),
            )
            normalized = " ".join(selected.split())
            if not normalized:
                continue
            fingerprint = RagTextProcessor.normalize(normalized)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            statements.append(f"- {normalized} [{index}]")
            if len(statements) == 5:
                break
        if not statements:
            return (
                "Les sources autorisées ont été retrouvées, mais leur contenu ne permet pas "
                "de produire une synthèse fiable."
            )
        return "Synthèse fondée uniquement sur les sources autorisées :\n" + "\n".join(statements)
