"""HTTP request and response parser module."""
import re
from typing import Dict, Optional


class HTTPParser:
    """Parses raw HTTP request and response strings."""

    @staticmethod
    def parse_request(raw_request: str) -> Dict[str, any]:
        """
        Parse a raw HTTP request string.
        
        Args:
            raw_request: Raw HTTP request string
            
        Returns:
            Dictionary containing method, path, http_version, headers, and body
        """
        lines = raw_request.split('\r\n')
        
        # Parse request line
        request_line_match = re.match(r'(\w+)\s+(.+?)\s+(HTTP/[\d.]+)', lines[0])
        if not request_line_match:
            return {
                'method': None,
                'path': None,
                'http_version': None,
                'headers': {},
                'body': ''
            }
        
        method, path, http_version = request_line_match.groups()
        
        # Parse headers
        headers = {}
        body_start_idx = 1
        for i, line in enumerate(lines[1:], start=1):
            if line == '':
                body_start_idx = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Parse body
        body = '\r\n'.join(lines[body_start_idx:]) if body_start_idx < len(lines) else ''
        
        return {
            'method': method,
            'path': path,
            'http_version': http_version,
            'headers': headers,
            'body': body
        }

    @staticmethod
    def parse_response(raw_response: str) -> Dict[str, any]:
        """
        Parse a raw HTTP response string.
        
        Args:
            raw_response: Raw HTTP response string
            
        Returns:
            Dictionary containing status_code, status_message, headers, and body
        """
        lines = raw_response.split('\r\n')
        
        # Parse status line
        status_line_match = re.match(r'HTTP/[\d.]+\s+(\d+)\s*(.*)', lines[0])
        if not status_line_match:
            return {
                'status_code': None,
                'status_message': None,
                'headers': {},
                'body': ''
            }
        
        status_code, status_message = status_line_match.groups()
        
        # Parse headers
        headers = {}
        body_start_idx = 1
        for i, line in enumerate(lines[1:], start=1):
            if line == '':
                body_start_idx = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Parse body
        body = '\r\n'.join(lines[body_start_idx:]) if body_start_idx < len(lines) else ''
        
        return {
            'status_code': int(status_code) if status_code else None,
            'status_message': status_message.strip(),
            'headers': headers,
            'body': body
        }
    
    @staticmethod
    def get_header(headers: Dict[str, str], key: str) -> Optional[str]:
        """
        Get header value with case-insensitive lookup.
        
        Args:
            headers: Dictionary of headers
            key: Header key to lookup
            
        Returns:
            Header value or None if not found
        """
        return headers.get(key.lower())
