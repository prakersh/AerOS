import json
from difflib import SequenceMatcher

from sqlmodel import Session, select

from aeros.models.sku import SKU, Category

# Below this similarity score a fuzzy candidate is considered unrelated.
_FUZZY_CUTOFF = 0.6
# A fuzzy winner is "definite" only if it is strong on its own and clearly
# ahead of the runner-up; otherwise the match is ambiguous and we hand the
# candidates back for the LLM / user to choose between.
_CONFIDENT = 0.85
_LEAD_MARGIN = 0.15


def list_categories(session: Session) -> list[Category]:
    return list(session.exec(select(Category).order_by(Category.sort_order)).all())  # type: ignore[arg-type]


def list_skus(session: Session, org_id: int, category_id: int | None = None) -> list[SKU]:
    stmt = select(SKU).where(SKU.org_id == org_id)
    if category_id:
        stmt = stmt.where(SKU.category_id == category_id)
    return list(session.exec(stmt.order_by(SKU.name)).all())


def get_sku(session: Session, sku_id: int) -> SKU | None:
    return session.get(SKU, sku_id)


def _aliases(sku: SKU) -> list[str]:
    try:
        raw = json.loads(sku.aliases_json or "[]")
    except (ValueError, TypeError):
        return []
    return [str(a) for a in raw] if isinstance(raw, list) else []


def _haystacks(sku: SKU) -> list[str]:
    """All lowercased strings a query may legitimately match against."""
    return [sku.name.lower(), sku.code.lower(), *(a.lower() for a in _aliases(sku))]


def _score(query: str, sku: SKU) -> float:
    """0..1 relevance of a SKU to the query across name, code, and aliases.

    Combines whole-string and per-word signals so that a short or misspelled
    query ("milk", "Ashirvad") still scores well against a long full name
    ("Full Cream Milk", "Aashirvaad Atta 5kg").
    """
    q = query.lower().strip()
    if not q:
        return 0.0
    best = 0.0
    for hay in _haystacks(sku):
        if not hay:
            continue
        if q == hay:
            return 1.0
        if q in hay:
            best = max(best, 0.95)
        elif hay in q:
            best = max(best, 0.85)
        best = max(best, SequenceMatcher(None, q, hay).ratio())
        for word in hay.split():
            if q == word:
                best = max(best, 0.92)
            elif q in word:
                best = max(best, 0.85)
            best = max(best, 0.9 * SequenceMatcher(None, q, word).ratio())
    return best


def _ranked(session: Session, org_id: int, query: str) -> list[tuple[SKU, float]]:
    """Org SKUs scored against the query, best first, unrelated ones dropped."""
    query = (query or "").strip()
    skus = list(session.exec(select(SKU).where(SKU.org_id == org_id)).all())
    if not query:
        ranked = [(s, 0.0) for s in sorted(skus, key=lambda s: s.name)]
        return ranked[:20]
    scored = [(s, _score(query, s)) for s in skus]
    hits = [(s, sc) for s, sc in scored if sc >= _FUZZY_CUTOFF]
    hits.sort(key=lambda pair: (-pair[1], len(pair[0].name), pair[0].name))
    return hits[:20]


def search_skus(session: Session, org_id: int, query: str) -> list[SKU]:
    """Rank an org's SKUs by relevance to a free-text query.

    Matches against name, code, and aliases, tolerating misspellings
    ("Ashirvad" -> "Aashirvaad Atta") and exact code lookups ("PF001").
    """
    return [s for s, _ in _ranked(session, org_id, query)]


def resolve_sku(session: Session, org_id: int, ref: object) -> SKU | None:
    """Resolve any reference a user might give to a single SKU.

    Accepts an integer primary key, a numeric/code string ("19", "PF001"),
    or a name/alias ("Aashirvaad", even misspelled). Returns the single best
    match scoped to the org, or None if nothing is close enough. Use
    [resolve_sku_ref][] when ambiguity should be surfaced rather than guessed.
    """
    match, candidates = resolve_sku_ref(session, org_id, ref)
    if match:
        return match
    return candidates[0] if candidates else None


def resolve_sku_ref(session: Session, org_id: int, ref: object) -> tuple[SKU | None, list[SKU]]:
    """Resolve a reference, distinguishing a confident match from ambiguity.

    Returns ``(match, candidates)``:
    - ``match`` is set only when the reference is unambiguous: an integer id,
      an exact code, or a fuzzy winner that clearly leads the field. The
      ``candidates`` list is empty in that case.
    - When several SKUs are plausible (e.g. "milk" -> Toned / Full Cream),
      ``match`` is None and ``candidates`` holds the ranked options so the
      caller can ask the user which one they meant.
    - When nothing is close, both are empty / None.
    """
    if ref is None:
        return None, []

    # Integer primary key (or its string form) — always unambiguous.
    if isinstance(ref, int) or (isinstance(ref, str) and ref.strip().isdigit()):
        sku = session.get(SKU, int(ref))
        if sku and sku.org_id == org_id:
            return sku, []

    text = str(ref).strip()
    if not text:
        return None, []

    # Exact code match (case-insensitive), the most common explicit reference.
    code_hit = session.exec(
        select(SKU).where(SKU.org_id == org_id, SKU.code == text.upper())
    ).first()
    if code_hit:
        return code_hit, []

    ranked = _ranked(session, org_id, text)
    if not ranked:
        return None, []

    top_sku, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    confident = top_score >= _CONFIDENT and (top_score - second_score) >= _LEAD_MARGIN
    if len(ranked) == 1 or top_score >= 1.0 or confident:
        return top_sku, []

    return None, [s for s, _ in ranked]
