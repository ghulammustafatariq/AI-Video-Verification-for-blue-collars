"""
Domain Knowledge Retriever (lightweight RAG without ChromaDB)

Loads Pakistan trade standards from local JSON knowledge base.
Retrieves relevant standards, safety protocols, tools, and
common violations for a given trade category.

This is a local-first retrieval system — no external vector DB needed.
"""

import os
import json
from typing import List, Dict, Any, Optional

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")

CATEGORY_MAP = {
    "plumbing": "plumbing",
    "electrical": "electrical",
    "carpentry": "carpentry",
    "painting": "painting",
    "cleaning": "cleaning",
    "gardening": "gardening",
    "moving": "moving",
    "ac / hvac": "hvac",
    "hvac": "hvac",
    "ac repair": "hvac",
    "roofing": "roofing",
    "flooring": "flooring",
    "appliances": "appliances",
    "other": None,
}


def _load_knowledge(category: str) -> Optional[Dict]:
    """Load knowledge base for a category."""
    mapped = CATEGORY_MAP.get(category.lower().strip(), category.lower().strip())
    if mapped is None:
        return None

    path = os.path.join(KNOWLEDGE_DIR, mapped, "standards.json")
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def retrieve_relevant_context(category: str, violations: List[Dict] = None, top_k: int = 5) -> Dict[str, Any]:
    """
    Retrieve domain-specific context for augmenting analysis prompts.

    Args:
        category: Trade category (e.g., "Plumbing")
        violations: Optional list of detected violations to match against
        top_k: Max number of standards to return

    Returns:
        Dict with standards, safety, tools, and matched violations
    """
    kb = _load_knowledge(category)
    if not kb:
        return {
            "available": False,
            "message": f"No knowledge base for {category}. Using general assessment.",
            "standards": [],
            "safety": [],
            "tools": [],
            "matched_violations": [],
        }

    standards = kb.get("standards", [])
    safety = kb.get("safety", [])
    tools = kb.get("tools", [])
    common_violations = kb.get("common_violations", [])

    matched_violations = []
    if violations:
        for cv in common_violations:
            cv_text = cv.get("issue", "").lower()
            for v in violations:
                v_text = v.get("reason", "").lower()
                # Simple keyword overlap matching
                words_v = set(v_text.split())
                words_cv = set(cv_text.split())
                overlap = len(words_v & words_cv)
                if overlap >= 2 or any(w in cv_text for w in words_v if len(w) > 4):
                    matched_violations.append({
                        "detected": v.get("reason", ""),
                        "reference_issue": cv["issue"],
                        "severity": cv.get("severity", "UNKNOWN"),
                        "consequence": cv.get("consequence", ""),
                    })
                    break

    return {
        "available": True,
        "category": kb.get("trade", category),
        "standards": standards[:top_k],
        "safety": safety[:3],
        "tools": tools,
        "matched_violations": matched_violations[:5],
    }


def enrich_prompt_with_context(prompt: str, category: str) -> str:
    """
    Augment the analysis prompt with domain-specific context.

    Adds relevant standards, safety protocols, and tool references
    to improve Twelve Labs analysis accuracy.
    """
    context = retrieve_relevant_context(category)

    if not context["available"]:
        return prompt

    lines = [prompt]

    if context["standards"]:
        lines.append("\nRelevant {0} standards for reference:".format(context["category"]))
        for s in context["standards"][:3]:
            lines.append(f"  - {s['title']}: {s['rule']} (Ref: {s.get('reference', 'N/A')})")

    if context["safety"]:
        lines.append(f"\nRequired safety protocols for {context['category']}:")
        for s in context["safety"][:3]:
            lines.append(f"  - {s['protocol']}: {s['requirement']}")

    if context["tools"]:
        lines.append(f"\nExpected tools for {context['category']} work:")
        tool_names = [t["name"] for t in context["tools"][:5]]
        lines.append(f"  {', '.join(tool_names)}")

    return "\n".join(lines)
