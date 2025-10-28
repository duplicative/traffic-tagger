# web and API misconfigurations
```
  - name: "GraphQL Introspection Enabled"
    enabled: true
    conditions:
      - target: "request.body"
        operator: "contains"
        value: "__schema"
      - target: "request.body"
        operator: "contains"
        value: "IntrospectionQuery"
    match_logic: "OR"
    description: "Flags GraphQL requests that perform introspection, a feature that can expose the entire API schema to an attacker if left enabled in production."
```

```
  - name: "CORS Misconfiguration"
    enabled: true
    conditions:
      - target: "response.headers.access-control-allow-origin"
        operator: "matches_regex"
        value: '(\*|null)'
    match_logic: "AND"
    description: "Identifies responses with an overly permissive Cross-Origin Resource Sharing (CORS) policy, which could allow malicious websites to steal data."
```

# info exposure
```
  - name: "CORS Misconfiguration"
    enabled: true
    conditions:
      - target: "response.headers.access-control-allow-origin"
        operator: "matches_regex"
        value: '(\*|null)'
    match_logic: "AND"
    description: "Identifies responses with an overly permissive Cross-Origin Resource Sharing (CORS) policy, which could allow malicious websites to steal data."
```

```
  - name: "Stack Trace in Response"
    enabled: true
    conditions:
      - target: "response.body"
        operator: "matches_regex"
        value: '(?i)(stack trace|at java\.lang|in [a-zA-Z\._]+ on line [0-9]+|Traceback \(most recent call last\))'
    match_logic: "AND"
    description: "Highlights responses containing a stack trace, which leaks internal application structure, file paths, and framework information."
```

# --- Category 3: Injection & Command Execution ---
```
  - name: "OS Command Injection Characters"
    enabled: true
    conditions:
      - target: "request.path"
        operator: "matches_regex"
        value: '(&|\||;|%0a|\$|\(|\`|\))'
      - target: "request.body"
        operator: "matches_regex"
        value: '(&|\||;|%0a|\$|\(|\`|\))'
    match_logic: "OR"
    description: "Looks for common shell metacharacters in the request path or body that are used to execute arbitrary OS commands."
```
```
  - name: "SQL Error in Response"
    enabled: true
    conditions:
      - target: "response.body"
        operator: "matches_regex"
        value: '(?i)(You have an error in your SQL syntax|ORA-009|unclosed quotation mark|NpgsqlException)'
    match_logic: "AND"
    description: "Flags responses that contain error messages characteristic of a backend SQL database, which is a strong indicator of an SQL injection vulnerability."
```
```
  - name: "NoSQL Injection Operators"
    enabled: true
    conditions:
      - target: "request.body"
        operator: "matches_regex"
        value: '(?i)("\$where"|"\$ne"|"\$gt"|"\$regex")'
    match_logic: "AND"
    description: "Detects the use of NoSQL (e.g., MongoDB) operators in the request body, which could be exploited for NoSQL injection attacks."
```
```
  - name: "XML Body (Potential XXE)"
    enabled: true
    conditions:
      - target: "request.headers.content-type"
        operator: "contains"
        value: "application/xml"
      - target: "request.body"
        operator: "starts_with"
        value: "<?xml"
    match_logic: "OR"
    description: "Identifies requests that send XML data. These endpoints should be tested for XML External Entity (XXE) injection vulnerabilities."
```
# --- Category 2: Server-Side Request & File Operations ---
```
  - name: "Local File Path Exposure"
    enabled: true
    conditions:
      - target: "response.body"
        operator: "matches_regex"
        value: '(?i)(C:\\\\Users|/home/[a-z]+|/var/www/|/etc/passwd)'
    match_logic: "AND"
    description: "Finds responses that contain common local file paths, indicating potential information disclosure or Local File Inclusion (LFI) vulnerabilities."
```
```
  - name: "URL-as-Parameter (SSRF/Redirect Gadget)"
    enabled: true
    conditions:
      - target: "request.path"
        operator: "matches_regex"
        value: '(?i)[?&](url|uri|link|proxy|redirect|callback|next|destination)=https?://'
      - target: "request.body"
        operator: "matches_regex"
        value: '(?i)["''](url|uri|link|proxy|redirect|callback|next|destination)["'']:\s*["'']https?://'
    match_logic: "OR"
    description: "Tags requests where a full URL is passed in a parameter. This is a classic gadget for Server-Side Request Forgery (SSRF) and Open Redirect vulnerabilities."
```
```
  - name: "Cloud Metadata Endpoint (SSRF)"
    enabled: true
    conditions:
      - target: "request.body"
        operator: "matches_regex"
        value: '(?i)(169\.254\.169\.254|metadata\.google\.internal)'
    match_logic: "AND"
    description: "Flags requests containing the IP address for cloud metadata services (AWS, GCP). This is a strong indicator of a potential high-impact SSRF vulnerability."
```
```
  - name: "Debug Mode Enabled"
    enabled: true
    conditions:
      - target: "request.headers.x-debug"
        operator: "equals"
        value: "true"
      - target: "response.body"
        operator: "matches_regex"
        value: '(?i)(DEBUG\s?=\s?True|in debug mode)'
    match_logic: "OR"
    description: "Identifies requests where a debug mode appears to be active, which often provides more verbose errors and may enable insecure functionality."
```

# authz authn
```

  - name: "Administrative Endpoint Access"
    enabled: true
    conditions:
      - target: "request.path"
        operator: "matches_regex"
        value: '(?i)^/(admin|manage|config|dashboard|control-panel)'
    match_logic: "AND"
    description: "Flags requests to endpoints that are typically used for administrative or management functions, which should have strict access controls."
```

```
  - name: "Custom Security Header"
    enabled: true
    conditions:
      - target: "request.headers.x-api-key"
        operator: "contains"
        value: ""
      - target: "request.headers.x-user-role"
        operator: "contains"
        value: ""
      - target: "request.headers.x-original-url"
        operator: "contains"
        value: ""
    match_logic: "OR"
    description: "Highlights requests that use non-standard headers like 'X-API-Key' or 'X-User-Role', which can sometimes be manipulated to bypass access controls."
```
