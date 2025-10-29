"""Rule-based tagging engine for HTTP traffic analysis."""
import re
import yaml
from typing import Dict, List, Any, Tuple
from shared.http_parser import HTTPParser


class RuleEngine:
    """Evaluates HTTP traffic against user-defined rules."""

    def __init__(self, rules_file_path: str):
        """
        Initialize the rule engine with a YAML rules file.
        
        Args:
            rules_file_path: Path to the YAML rules file
        """
        with open(rules_file_path, 'r') as f:
            rules_data = yaml.safe_load(f)
        
        self.rules = rules_data.get('rules', [])

    def apply_rules(self, decoded_request: str, decoded_response: str) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Apply all enabled rules to the HTTP request/response pair.
        
        Args:
            decoded_request: Decoded HTTP request string
            decoded_response: Decoded HTTP response string
            
        Returns:
            Tuple of (list of tag names that matched, dict of rule name to matched values)
        """
        tags = []
        highlights = {}
        
        # Parse the HTTP request and response
        request = HTTPParser.parse_request(decoded_request)
        response = HTTPParser.parse_response(decoded_response)
        
        # Evaluate each enabled rule
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
            
            matched_values = self._evaluate_rule(rule, request, response)
            if matched_values:
                tags.append(rule['name'])
                highlights[rule['name']] = matched_values
        
        return tags, highlights

    def _evaluate_rule(self, rule: Dict[str, Any], request: Dict, response: Dict) -> List[str]:
        """
        Evaluate a single rule against the request/response.
        
        Args:
            rule: Rule dictionary
            request: Parsed request dictionary
            response: Parsed response dictionary
            
        Returns:
            List of matched string values if rule matches, empty list otherwise
        """
        conditions = rule.get('conditions', [])
        match_logic = rule.get('match_logic', 'AND').upper()
        
        if not conditions:
            return []
        
        # Collect all matched values from conditions
        all_matched_values = []
        condition_results = []
        
        for condition in conditions:
            matched_values = self._evaluate_condition(condition, request, response)
            condition_results.append(len(matched_values) > 0)
            all_matched_values.extend(matched_values)
        
        # Check if rule matches based on match logic
        rule_matches = False
        if match_logic == 'OR':
            rule_matches = any(condition_results)
        else:  # Default to AND
            rule_matches = all(condition_results)
        
        # Return matched values only if rule matches
        return all_matched_values if rule_matches else []

    def _evaluate_condition(self, condition: Dict[str, str], request: Dict, response: Dict) -> List[str]:
        """
        Evaluate a single condition.
        
        Args:
            condition: Condition dictionary with target, operator, and value
            request: Parsed request dictionary
            response: Parsed response dictionary
            
        Returns:
            List of matched string values if condition matches, empty list otherwise
        """
        target = condition.get('target', '')
        operator = condition.get('operator', '')
        value = condition.get('value', '')
        
        # Extract the target value from request/response
        target_value = self._extract_target_value(target, request, response)
        
        if target_value is None:
            return []
        
        # Convert to string for comparison
        target_value = str(target_value)
        
        # Apply the operator and get matched values
        return self._apply_operator(target_value, operator, value)

    def _extract_target_value(self, target: str, request: Dict, response: Dict) -> Any:
        """
        Extract the value from the target path.
        
        Args:
            target: Target path (e.g., 'request.path', 'response.headers.content-type')
            request: Parsed request dictionary
            response: Parsed response dictionary
            
        Returns:
            The extracted value or None if not found
        """
        parts = target.split('.')
        
        if len(parts) < 2:
            return None
        
        # Determine if we're looking at request or response
        if parts[0] == 'request':
            data = request
        elif parts[0] == 'response':
            data = response
        else:
            return None
        
        # Navigate through the parts
        current = data
        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None
        
        return current

    def _apply_operator(self, target_value: str, operator: str, value: str) -> List[str]:
        """
        Apply the specified operator to compare target_value and value.
        
        Args:
            target_value: The value extracted from the HTTP data
            operator: The comparison operator
            value: The value to compare against
            
        Returns:
            List of matched string values if comparison succeeds, empty list otherwise
        """
        if operator == 'contains':
            if value.lower() in target_value.lower():
                # Find the actual matched substring (case-insensitive match)
                pattern = re.compile(re.escape(value), re.IGNORECASE)
                matches = pattern.findall(target_value)
                return matches if matches else [value]
            return []
        
        elif operator == 'not_contains':
            # not_contains doesn't need highlighting as it's a negative condition
            if value.lower() not in target_value.lower():
                return [f"(not: {value})"]
            return []
        
        elif operator == 'equals':
            if target_value == value:
                return [target_value]
            return []
        
        elif operator == 'starts_with':
            if target_value.startswith(value):
                return [value]
            return []
        
        elif operator == 'ends_with':
            if target_value.endswith(value):
                return [value]
            return []
        
        elif operator == 'matches_regex':
            try:
                matches = re.findall(value, target_value)
                return matches if matches else []
            except re.error:
                return []
        
        return []
