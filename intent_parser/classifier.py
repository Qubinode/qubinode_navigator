"""
Deterministic keyword/regex intent classifier.

No AI models used. Classification is based on keyword matching and
regex patterns for each IntentCategory.
"""

import re
from typing import List, Tuple

from .models import IntentCategory, ParsedIntent


# Each category maps to (keywords, regex_patterns, priority_boost)
# keywords: list of keyword sets - matching ANY set scores +1
# regex_patterns: compiled regex patterns - each match scores +2
# priority_boost: static priority boost for disambiguation (only applied if base score > 0)

_CATEGORY_RULES: dict = {}


def _kw(*words: str) -> re.Pattern:
    """Build a regex that matches if ALL words appear (in any order)."""
    parts = [rf"(?=.*\b{re.escape(w)}\b)" for w in words]
    return re.compile("".join(parts), re.IGNORECASE)


def _any_kw(*words: str) -> re.Pattern:
    """Build a regex that matches if ANY word appears."""
    escaped = [re.escape(w) for w in words]
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)


def _build_rules() -> dict:
    """Build classification rules for each intent category."""
    rules = {}

    # --- VM operations ---
    rules[IntentCategory.VM_LIST] = {
        "keywords": [
            _kw("list", "vm"),
            _kw("show", "vm"),
            _kw("list", "virtual"),
            _kw("show", "virtual"),
            _kw("all", "vm"),
        ],
        "patterns": [
            re.compile(r"\blist\s+(?:all\s+)?(?:vms?|virtual\s+machines?)\b", re.I),
            re.compile(r"\bshow\s+(?:all\s+)?(?:vms?|virtual\s+machines?)\b", re.I),
            re.compile(r"\bwhat\s+vms?\b", re.I),
        ],
        "boost": 0,
    }

    rules[IntentCategory.VM_INFO] = {
        "keywords": [
            _kw("info", "vm"),
            _kw("details", "vm"),
            _kw("describe", "vm"),
            _kw("status", "vm"),
        ],
        "patterns": [
            re.compile(r"\b(?:info|details?|describe|status)\s+(?:about\s+|for\s+|of\s+)?(?:vm|virtual\s+machine)\s+\w+", re.I),
            re.compile(r"\bvm\s+(?:info|details?|status)\b", re.I),
            re.compile(r"\btell\s+me\s+about\s+(?:vm|virtual\s+machine)\s+\w+", re.I),
        ],
        "boost": 1,
    }

    rules[IntentCategory.VM_CREATE] = {
        "keywords": [
            _kw("create", "vm"),
            _kw("make", "vm"),
            _kw("deploy", "vm"),
            _kw("spin", "up"),
            _kw("provision", "vm"),
            _kw("launch", "vm"),
            _kw("new", "vm"),
            _kw("create", "virtual"),
        ],
        "patterns": [
            re.compile(r"\b(?:create|make|launch)\s+(?:a\s+)?(?:new\s+)?(?:vm|virtual\s+machine)\b", re.I),
            re.compile(r"\bspin\s+up\s+(?:a\s+)?(?:(?:new|the)\s+)?(?:vm|virtual\s+machine|server)\b", re.I),
            re.compile(r"\bdeploy\s+(?:a\s+)?(?:new\s+)?(?:vm|virtual\s+machine)\b", re.I),
            re.compile(r"\bprovision\s+(?:a\s+)?(?:vm|virtual\s+machine)\b", re.I),
        ],
        "boost": 0,
    }

    rules[IntentCategory.VM_DELETE] = {
        "keywords": [
            _kw("delete", "vm"),
            _kw("remove", "vm"),
            _kw("destroy", "vm"),
            _kw("terminate", "vm"),
        ],
        "patterns": [
            re.compile(r"\b(?:delete|remove|destroy|terminate)\s+(?:the\s+)?(?:vm|virtual\s+machine)\s+\w+", re.I),
            re.compile(r"\b(?:delete|remove|destroy|terminate)\s+\w+\s+vm\b", re.I),
        ],
        "boost": 0,
    }

    rules[IntentCategory.VM_PREFLIGHT] = {
        "keywords": [
            _kw("preflight"),
            _kw("pre-flight"),
            _kw("check", "before", "create"),
            _kw("validate", "vm"),
            _kw("can", "create", "vm"),
        ],
        "patterns": [
            re.compile(r"\bpre-?flight\b", re.I),
            re.compile(r"\bcheck\s+(?:before|if)\s+(?:i\s+can\s+)?creat", re.I),
            re.compile(r"\bcan\s+i\s+create\s+(?:a\s+)?vm", re.I),
        ],
        "boost": 1,
    }

    # --- DAG operations ---
    rules[IntentCategory.DAG_LIST] = {
        "keywords": [
            _kw("list", "dag"),
            _kw("show", "dag"),
            _kw("list", "workflow"),
            _kw("show", "workflow"),
            _kw("available", "dag"),
            _kw("available", "workflow"),
            _kw("all", "dag"),
        ],
        "patterns": [
            re.compile(r"\blist\s+(?:all\s+)?(?:dags?|workflows?)\b", re.I),
            re.compile(r"\bshow\s+(?:\w+\s+)?(?:dags?|workflows?)\b", re.I),
            re.compile(r"\bwhat\s+(?:dags?|workflows?)\b", re.I),
        ],
        "boost": 0,
    }

    rules[IntentCategory.DAG_INFO] = {
        "keywords": [
            _kw("info", "dag"),
            _kw("details", "dag"),
            _kw("describe", "dag"),
        ],
        "patterns": [
            re.compile(r"\b(?:info|details?|describe)\s+(?:about\s+|for\s+|of\s+)?(?:dag|workflow)\s+\w+", re.I),
            re.compile(r"\bdag\s+(?:info|details?)\b", re.I),
        ],
        "boost": 1,
    }

    rules[IntentCategory.DAG_TRIGGER] = {
        "keywords": [
            _kw("trigger", "dag"),
            _kw("run", "dag"),
            _kw("execute", "dag"),
            _kw("start", "dag"),
            _kw("trigger", "workflow"),
            _kw("run", "workflow"),
        ],
        "patterns": [
            re.compile(r"\b(?:trigger|run|execute|start)\s+(?:the\s+)?(?:dag|workflow)\s+\w+", re.I),
            re.compile(r"\b(?:trigger|run|execute|start)\s+(?:the\s+)?\w+\s+(?:dag|workflow)\b", re.I),
        ],
        "boost": 0,
    }

    # --- RAG operations ---
    rules[IntentCategory.RAG_QUERY] = {
        "keywords": [
            _kw("search", "rag"),
            _kw("query", "rag"),
            _kw("search", "knowledge"),
            _kw("search", "document"),
            _kw("find", "document"),
        ],
        "patterns": [
            re.compile(r"\b(?:search|query)\s+(?:the\s+)?(?:rag|knowledge\s+base|docs?|documentation)\b", re.I),
            re.compile(r"\bfind\s+(?:docs?|documentation|information)\s+(?:about|on|for)\b", re.I),
            re.compile(r"\bhow\s+(?:do|to|can)\s+(?:i|we)\b", re.I),
            re.compile(r"\blookup\s+\w+", re.I),
        ],
        "boost": 0,
    }

    rules[IntentCategory.RAG_INGEST] = {
        "keywords": [
            _kw("ingest"),
            _kw("index", "document"),
            _kw("add", "document"),
            _kw("import", "document"),
        ],
        "patterns": [
            re.compile(r"\b(?:ingest|index)\s+(?:the\s+)?(?:docs?|documents?|content)\b", re.I),
            re.compile(r"\badd\s+(?:\w+\s+)?(?:to\s+)?(?:rag|knowledge\s+base)\b", re.I),
            re.compile(r"\badd\s+(?:the\s+)?(?:docs?|documents?)\b", re.I),
        ],
        "boost": 1,
    }

    rules[IntentCategory.RAG_STATS] = {
        "keywords": [
            _kw("rag", "stats"),
            _kw("rag", "statistics"),
            _kw("knowledge", "base", "stats"),
            _kw("document", "count"),
        ],
        "patterns": [
            re.compile(r"\brag\s+(?:stats|statistics|status)\b", re.I),
            re.compile(r"\bhow\s+many\s+documents?\b", re.I),
            re.compile(r"\bknowledge\s+base\s+(?:stats?|statistics?|info|status)\b", re.I),
        ],
        "boost": 1,
    }

    # --- System operations ---
    rules[IntentCategory.SYSTEM_STATUS] = {
        "keywords": [
            _kw("system", "status"),
            _kw("airflow", "status"),
            _kw("health"),
            _kw("is", "running"),
            _kw("service", "status"),
        ],
        "patterns": [
            re.compile(r"\b(?:system|airflow|service)\s+(?:status|health)\b", re.I),
            re.compile(r"\bis\s+(?:the\s+)?(?:system|airflow|everything)\s+(?:running|up|ok|healthy)\b", re.I),
            re.compile(r"\bcheck\s+(?:system\s+)?(?:health|status)\b", re.I),
            re.compile(r"\b(?:health|status)\s+check\b", re.I),
        ],
        "boost": 0,
    }

    rules[IntentCategory.SYSTEM_INFO] = {
        "keywords": [
            _kw("system", "info"),
            _kw("system", "information"),
            _kw("architecture"),
            _kw("capabilities"),
        ],
        "patterns": [
            re.compile(r"\b(?:system|qubinode)\s+(?:info|information|overview)\b", re.I),
            re.compile(r"\btell\s+me\s+about\s+(?:the\s+)?(?:system|qubinode|architecture)\b", re.I),
        ],
        "boost": 0,
    }

    # --- Troubleshooting ---
    rules[IntentCategory.TROUBLESHOOT_DIAGNOSE] = {
        "keywords": [
            _kw("diagnose"),
            _kw("troubleshoot"),
            _kw("debug"),
            _kw("fix"),
            _kw("broken"),
            _kw("not", "working"),
            _kw("failing"),
        ],
        "patterns": [
            re.compile(r"\b(?:diagnose|troubleshoot|debug|fix)\s+", re.I),
            re.compile(r"\b(?:is|not)\s+(?:working|responding|running)\b", re.I),
            re.compile(r"\bwhy\s+(?:is|did|does)\s+.+?\s+(?:fail|error|crash|hang)", re.I),
            re.compile(r"\bsomething\s+(?:is\s+)?(?:wrong|broken)\b", re.I),
            re.compile(r"\b(?:error|failure|problem|issue)\s+(?:in|with|during)\b", re.I),
        ],
        "boost": 0,
    }

    rules[IntentCategory.TROUBLESHOOT_HISTORY] = {
        "keywords": [
            _kw("troubleshooting", "history"),
            _kw("past", "solutions"),
            _kw("previous", "fixes"),
            _kw("similar", "errors"),
        ],
        "patterns": [
            re.compile(r"\b(?:troubleshooting|past|previous)\s+(?:history|solutions?|fixes?|attempts?)\b", re.I),
            re.compile(r"\bhas\s+this\s+(?:been\s+)?(?:solved|fixed)\s+before\b", re.I),
            re.compile(r"\bsimilar\s+(?:errors?|issues?|problems?)\b", re.I),
        ],
        "boost": 2,
    }

    rules[IntentCategory.TROUBLESHOOT_LOG] = {
        "keywords": [
            _kw("log", "troubleshooting"),
            _kw("record", "solution"),
            _kw("save", "solution"),
            _kw("log", "attempt"),
        ],
        "patterns": [
            re.compile(r"\blog\s+(?:the\s+)?(?:troubleshooting|solution|attempt|fix)\b", re.I),
            re.compile(r"\brecord\s+(?:the\s+)?(?:solution|fix|attempt)\b", re.I),
            re.compile(r"\bsave\s+(?:the\s+)?(?:solution|fix)\b", re.I),
        ],
        "boost": 2,
    }

    # --- Lineage ---
    rules[IntentCategory.LINEAGE_DAG] = {
        "keywords": [
            _kw("lineage"),
            _kw("dependencies", "dag"),
            _kw("upstream"),
            _kw("downstream"),
        ],
        "patterns": [
            re.compile(r"\b(?:dag\s+)?lineage\b", re.I),
            re.compile(r"\b(?:upstream|downstream)\s+(?:of|for|deps?|dependencies)\b", re.I),
            re.compile(r"\bwhat\s+(?:depends|relies)\s+on\b", re.I),
        ],
        "boost": 1,
    }

    rules[IntentCategory.LINEAGE_BLAST_RADIUS] = {
        "keywords": [
            _kw("blast", "radius"),
            _kw("impact", "failure"),
            _kw("impact", "analysis"),
            _kw("what", "affected"),
        ],
        "patterns": [
            re.compile(r"\bblast\s+radius\b", re.I),
            re.compile(r"\b(?:failure|impact)\s+(?:analysis|assessment)\b", re.I),
            re.compile(r"\bwhat\s+(?:would\s+be\s+|is\s+)?affected\s+if\b", re.I),
        ],
        "boost": 2,
    }

    # --- Help ---
    rules[IntentCategory.HELP] = {
        "keywords": [
            _kw("usage"),
            _kw("how", "use"),
        ],
        "patterns": [
            re.compile(r"^help$", re.I),
            re.compile(r"\bhow\s+(?:do\s+i\s+)?use\s+(?:this|qubinode)\b", re.I),
            re.compile(r"\bwhat\s+(?:can\s+)?(?:you|this)\s+do\b", re.I),
        ],
        "boost": 0,
    }

    return rules


def _get_rules() -> dict:
    """Lazy-initialize rules."""
    global _CATEGORY_RULES
    if not _CATEGORY_RULES:
        _CATEGORY_RULES = _build_rules()
    return _CATEGORY_RULES


def classify(text: str) -> ParsedIntent:
    """
    Classify natural language text into an IntentCategory.

    Returns a ParsedIntent with the best-matching category and confidence.
    """
    if not text or not text.strip():
        return ParsedIntent(
            category=IntentCategory.UNKNOWN,
            confidence=0.0,
            raw_input=text or "",
        )

    text_clean = text.strip()
    rules = _get_rules()

    scores: List[Tuple[IntentCategory, float]] = []

    for category, rule in rules.items():
        base_score = 0.0

        # Check keyword patterns
        for kw_pattern in rule["keywords"]:
            if kw_pattern.search(text_clean):
                base_score += 1.0

        # Check regex patterns (weighted higher)
        for pattern in rule["patterns"]:
            if pattern.search(text_clean):
                base_score += 2.0

        # Only apply boost if there was a real match (keyword or pattern)
        if base_score > 0:
            score = base_score + rule["boost"] * 0.5
            scores.append((category, score))

    if not scores:
        return ParsedIntent(
            category=IntentCategory.UNKNOWN,
            confidence=0.0,
            raw_input=text_clean,
        )

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    best_category, best_score = scores[0]

    # Require minimum score to avoid matching on noise
    if best_score < 1.5:
        return ParsedIntent(
            category=IntentCategory.UNKNOWN,
            confidence=round(best_score / 10.0, 2),
            raw_input=text_clean,
        )

    # Normalize confidence: map score to 0-1 range
    max_possible = 10.0
    confidence = min(best_score / max_possible, 1.0)

    # Boost confidence if clear winner (big gap to second)
    if len(scores) >= 2:
        gap = best_score - scores[1][1]
        if gap >= 2.0:
            confidence = min(confidence + 0.1, 1.0)

    return ParsedIntent(
        category=best_category,
        confidence=round(confidence, 2),
        raw_input=text_clean,
    )
