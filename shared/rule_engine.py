"""Rule-based tagging engine for HTTP traffic analysis."""
import re
import yaml
from typing import Dict, List, Any
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

    def apply_rules(self, decoded_request: str, decoded_response: str) -> List[str]:
        """
        Apply all enabled rules to the HTTP request/response pair.
        
        Args:
            decoded_request: Decoded HTTP request string
            decoded_response: Decoded HTTP response string
            
        Returns:
            List of tag names that matched
        """
        tags = []
        
        # Parse the HTTP request and response
        request = HTTPParser.parse_request(decoded_request)
        response = HTTPParser.parse_response(decoded_response)
        
        # Evaluate each enabled rule
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
            
            if self._evaluate_rule(rule, request, response):
                tags.append(rule['name'])
        
        return tags

    def _evaluate_rule(self, rule: Dict[str, Any], request: Dict, response: Dict) -> bool:
        """
        Evaluate a single rule against the request/response.
        
        Args:
            rule: Rule dictionary
            request: Parsed request dictionary
            response: Parsed response dictionary
            
        Returns:
            True if the rule matches, False otherwise
        """
        conditions = rule.get('conditions', [])
        match_logic = rule.get('match_logic', 'AND').upper()
        
        if not conditions:
            return False
        
        results = []
        for condition in conditions:
            result = self._evaluate_condition(condition, request, response)
            results.append(result)
        
        if match_logic == 'OR':
            return any(results)
        else:  # Default to AND
            return all(results)

    def _evaluate_condition(self, condition: Dict[str, str], request: Dict, response: Dict) -> bool:
        """
        Evaluate a single condition.
        
        Args:
            condition: Condition dictionary with target, operator, and value
            request: Parsed request dictionary
            response: Parsed response dictionary
            
        Returns:
            True if the condition matches, False otherwise
        """
        target = condition.get('target', '')
        operator = condition.get('operator', '')
        value = condition.get('value', '')
        
        # Extract the target value from request/response
        target_value = self._extract_target_value(target, request, response)
        
        if target_value is None:
            return False
        
        # Convert to string for comparison
        target_value = str(target_value)
        
        # Apply the operator
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

    def _apply_operator(self, target_value: str, operator: str, value: str) -> bool:
        """
        Apply the specified operator to compare target_value and value.
        
        Args:
            target_value: The value extracted from the HTTP data
            operator: The comparison operator
            value: The value to compare against
            
        Returns:
            True if the comparison succeeds, False otherwise
        """
        if operator == 'contains':
            return value.lower() in target_value.lower()
        
        elif operator == 'not_contains':
            return value.lower() not in target_value.lower()
        
        elif operator == 'equals':
            return target_value == value
        
        elif operator == 'starts_with':
            return target_value.startswith(value)
        
        elif operator == 'ends_with':
            return target_value.endswith(value)
        
        elif operator == 'matches_regex':
            try:
                return bool(re.search(value, target_value))
            except re.error:
                return False
        
        return False
