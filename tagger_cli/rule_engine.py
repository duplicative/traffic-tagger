import re
import yaml
from typing import Dict, List, Any

def load_rules(rules_file: str) -> List[Dict]:
    with open(rules_file, 'r') as f:
        data = yaml.safe_load(f)
    return data.get('rules', [])

def get_nested_value(obj: Dict, path: str) -> Any:
    keys = path.split('.')
    current = obj
    for key in keys:
        if isinstance(current, dict):
            # Case-insensitive for headers
            if 'headers' in keys[:keys.index(key)]:
                key = key.lower()
                current = {k.lower(): v for k, v in current.items()}.get(key)
            else:
                current = current.get(key)
        else:
            return None
    return current

def evaluate_condition(record: Dict, condition: Dict) -> bool:
    target_value = get_nested_value(record, condition['target'])
    if target_value is None:
        return False
    value = condition['value']
    operator = condition['operator']

    if operator == 'contains':
        return value.lower() in str(target_value).lower()
    elif operator == 'not_contains':
        return value.lower() not in str(target_value).lower()
    elif operator == 'equals':
        return str(target_value) == value
    elif operator == 'starts_with':
        return str(target_value).startswith(value)
    elif operator == 'ends_with':
        return str(target_value).endswith(value)
    elif operator == 'matches_regex':
        return bool(re.search(value, str(target_value)))
    else:
        return False

def apply_rules(rules: List[Dict], record: Dict) -> List[str]:
    tags = []
    for rule in rules:
        if not rule.get('enabled', True):
            continue
        conditions = rule['conditions']
        match_logic = rule.get('match_logic', 'AND').upper()
        results = [evaluate_condition(record, cond) for cond in conditions]
        if match_logic == 'AND':
            if all(results):
                tags.append(rule['name'])
        elif match_logic == 'OR':
            if any(results):
                tags.append(rule['name'])
    return tags
