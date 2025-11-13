from urllib.parse import parse_qs, unquote
import json

def extract_inputs(decoded_request: str) -> list[str]:
    """
    Parses a raw HTTP request string to extract potential user-controlled inputs
    from the query string, common body formats, and cookies.

    Args:
        decoded_request: The full, decoded HTTP request as a string.

    Returns:
        A list of unique strings identified as potential user inputs.
    """
    inputs = set()
    
    try:
        headers_part, body_part = decoded_request.split('\\r\\n\\r\\n', 1)
    except ValueError:
        headers_part = decoded_request
        body_part = ""

    request_lines = headers_part.split('\\r\\n')
    if not request_lines:
        return []

    # 1. Extract from URL Query String
    request_line_parts = request_lines[0].split(' ')
    if len(request_line_parts) > 1:
        path = request_line_parts[1]
        if '?' in path:
            query_string = path.split('?', 1)[1]
            query_params = parse_qs(query_string)
            for value_list in query_params.values():
                for value in value_list:
                    inputs.add(value)

    # 2. Extract from Headers (specifically Cookies)
    headers = {}
    for line in request_lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key.lower()] = value
            # 3. Cookie Values
            if key.lower() == 'cookie':
                cookies = value.split('; ')
                for cookie in cookies:
                    if '=' in cookie:
                        cookie_value = cookie.split('=', 1)[1]
                        inputs.add(unquote(cookie_value))

    # 4. Extract from Request Body
    content_type = headers.get('content-type', '')
    if body_part:
        # application/x-www-form-urlencoded
        if 'application/x-www-form-urlencoded' in content_type:
            form_data = parse_qs(body_part)
            for value_list in form_data.values():
                for value in value_list:
                    inputs.add(value)
        
        # application/json
        elif 'application/json' in content_type:
            try:
                json_data = json.loads(body_part)
                
                def find_strings_in_json(data):
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, str):
                                inputs.add(v)
                            else:
                                find_strings_in_json(v)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                inputs.add(item)
                            else:
                                find_strings_in_json(item)

                find_strings_in_json(json_data)
            except json.JSONDecodeError:
                # Body is not valid JSON, but we can still treat it as a raw string
                inputs.add(body_part)
        
        # multipart/form-data (basic implementation)
        elif 'multipart/form-data' in content_type:
            try:
                boundary = content_type.split('boundary=')[1]
                parts = body_part.split(f'--{boundary}')
                for part in parts:
                    if 'Content-Disposition' in part:
                        # This is a simplified parser. It finds the content after the headers of a part.
                        try:
                            _, content = part.split('\\r\\n\\r\\n', 1)
                            # Trim the trailing newline characters and dashes
                            cleaned_content = content.rsplit('\\r\\n', 1)[0]
                            if cleaned_content:
                                inputs.add(cleaned_content)
                        except ValueError:
                            continue
            except (IndexError, ValueError):
                # Could not parse multipart body, add the whole body as input
                inputs.add(body_part)

        # Treat as plain text if no specific content type matches
        else:
            inputs.add(body_part)

    return list(inputs)
