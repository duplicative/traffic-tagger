from typing import List, Dict, Any, Set
from urllib.parse import unquote_plus, unquote

from .user_input_extractor import extract_inputs


def _candidate_variants(value: str) -> Set[str]:
    """
    Produce normalized variants of a value to improve matching recall while
    still being precise to user-provided inputs.
    """
    variants: Set[str] = set()
    if not isinstance(value, str):
        return variants

    raw = value
    variants.add(raw)
    # URL decoding variants
    try:
        variants.add(unquote_plus(raw))
    except Exception:
        pass
    try:
        variants.add(unquote(raw))
    except Exception:
        pass
    # Space/plus normalization
    variants.add(raw.replace('+', ' '))

    # Lowercased variants for case-insensitive search
    variants |= {v.lower() for v in list(variants)}
    return {v for v in variants if v}


def _is_trivial(value: str) -> bool:
    """
    Filter out trivial inputs to reduce false positives.
    Heuristics: very short, purely numeric short tokens, common constants.
    """
    if value is None:
        return True
    s = value.strip()
    if s == '':
        return True
    if len(s) <= 2:
        # Allow 2+ only when it contains mixed chars
        if s.isdigit():
            return True
        # common one/two-char tokens are ignored
        if s.lower() in {'ok', 'on', 'no', 'id', 'to', 'in', 'at'}:
            return True
    if s.lower() in {'true', 'false', 'null', 'undefined', 'nan'}:
        return True
    return False


def _iter_event_strings(data: Any):
    """Yield string values from arbitrary nested event data structures."""
    if isinstance(data, str):
        yield data
    elif isinstance(data, dict):
        for v in data.values():
            yield from _iter_event_strings(v)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_event_strings(item)
    else:
        # Optionally include simple scalars by converting to string only if they are not trivial after conversion
        if isinstance(data, (int, float)):
            s = str(data)
            if not _is_trivial(s):
                yield s


def analyze_reflections(http_record: Dict[str, Any], sidecar_events: List[Dict[str, Any]]) -> List[str]:
    """
    Analyze whether user-controlled inputs from the HTTP request appear in any child
    sidecar events (DOM snapshots, JS executions, storage states) or in the HTTP response body.

    Only reflections of extracted user inputs are considered; we avoid scanning
    arbitrary patterns to minimize false positives.

    Args:
        http_record: The parent HTTP record (MongoDB document as dict), must contain 'decoded_request'.
        sidecar_events: List of associated sidecar event documents. Each should contain 'data' with nested structures.

    Returns:
        List of unique user input strings that were reflected.
    """
    decoded_request = http_record.get('decoded_request') or ''
    if not decoded_request:
        return []

    # Extract user inputs from the request
    inputs = extract_inputs(decoded_request)

    # Filter and prepare candidate match variants
    filtered_inputs: List[str] = [s for s in inputs if not _is_trivial(s)]
    # Map each original input to its variant set
    input_variants: Dict[str, Set[str]] = {orig: _candidate_variants(orig) for orig in filtered_inputs}

    reflected: Set[str] = set()

    # A) Check HTTP response body as a reflection surface
    decoded_response = (http_record.get('decoded_response') or '')
    r_low = decoded_response.lower()
    if r_low:
        for orig, variants in input_variants.items():
            if orig in reflected:
                continue
            for v in variants:
                if v and v in r_low:
                    reflected.add(orig)
                    break

    # B) Check sidecar events
    for event in sidecar_events or []:
        data = event.get('data')
        if data is None:
            # Some events might nest payload differently; try common fallbacks
            data = event.get('eventData') or event
        # Iterate over all string-like content inside event data
        for text in _iter_event_strings(data):
            if not isinstance(text, str):
                continue
            t_low = text.lower()
            for orig, variants in input_variants.items():
                # Skip if already found
                if orig in reflected:
                    continue
                for v in variants:
                    if v and v in t_low:
                        reflected.add(orig)
                        break

    return list(reflected)
