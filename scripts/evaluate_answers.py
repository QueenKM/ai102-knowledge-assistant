"""Run a small, reproducible smoke evaluation against the sample corpus."""
import json

from app.config import DEFAULT_TOP_K
from app.runtime import AssistantRuntime


def main() -> None:
    runtime = AssistantRuntime()
    cases = [
        ("What should I do when the BrewMaster Mini shows E12?", "E12"),
        ("How long is the warranty period?", "warranty"),
        ("Quasars nucleosynthesis?", None),
    ]
    results = []
    for question, evidence in cases:
        response, mode = runtime.ask_with_mode(question, DEFAULT_TOP_K)
        citations = [citation.to_dict() for citation in response.citations]
        evidence_match = (
            any(evidence.lower() in citation.snippet.lower() for citation in response.citations)
            if evidence is not None
            else None
        )
        results.append({
            "question": question,
            "mode": mode,
            "answer": response.answer,
            "citations": citations,
            "expected_evidence_term": evidence,
            "citation_term_match": evidence_match,
            "expected_abstention": evidence is None,
            "returned_without_citations": not citations,
        })
    print(json.dumps({"requested_mode": runtime.requested_mode, "results": results}, indent=2))


if __name__ == "__main__":
    main()
