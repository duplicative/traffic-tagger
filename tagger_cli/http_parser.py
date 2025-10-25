import re
from typing import Dict, Tuple

def parse_headers(header_lines: List[str]) -> Dict[str, str]:
    headers = {}
    for line in header_lines:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key.lower()] = value
    return headers

def parse_http_request(text: str) -> Dict:
    lines = text.split('\r\n')
    if not lines:
        return {}
    first_line = lines[0]
    parts = first_line.split()
    if len(parts) < 3:
        return {}
    method, path, http_version = parts[0], parts[1], parts[2]

    header_lines = []
    body_start = 0
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '':
            body_start = i + 1
            break
        header_lines.append(line)

    headers = parse_headers(header_lines)
    body = '\r\n'.join(lines[body_start:]) if body_start else ''

    return {
        'method': method,
        'path': path,
        'http_version': http_version,
        'headers': headers,
        'body': body
    }

def parse_http_response(text: str) -> Dict:
    lines = text.split('\r\n')
    if not lines:
        return {}
    first_line = lines[0]
    parts = first_line.split()
    if len(parts) < 3:
        return {}
    http_version, status_code, status_message = parts[0], int(parts[1]), ' '.join(parts[2:])

    header_lines = []
    body_start = 0
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '':
            body_start = i + 1
            break
        header_lines.append(line)

    headers = parse_headers(header_lines)
    body = '\r\n'.join(lines[body_start:]) if body_start else ''

    return {
        'status_code': status_code,
        'status_message': status_message,
        'http_version': http_version,
        'headers': headers,
        'body': body
    }
