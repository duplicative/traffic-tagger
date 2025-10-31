# Sidecar Browser Extension

Chrome Manifest V3 extension for capturing browser activity and sending to the Sidecar backend for AI-powered security analysis.

## Features

- **Network Interception**: Captures all HTTP requests/responses using Chrome Debugger API
- **DOM Snapshotting**: Monitors DOM changes with MutationObserver
- **JavaScript Execution Monitoring**: Hooks dangerous JS functions (innerHTML, eval, postMessage, etc.)
- **Storage Inspection**: Captures localStorage, sessionStorage, and cookies
- **WebSocket Communication**: Real-time streaming to backend
- **Simple Control UI**: Popup interface to start/stop monitoring

## Installation

### Development Mode

1. Make sure the Sidecar backend is running:
   ```bash
   cd ../backend
   source venv/bin/activate
   python src/main.py
   ```

2. Open Chrome and navigate to:
   ```
   chrome://extensions/
   ```

3. Enable "Developer mode" (toggle in top-right corner)

4. Click "Load unpacked"

5. Select the `extension` directory:
   ```
   /home/guid/projects/oppo3_Sidecar/extension
   ```

6. The Sidecar extension icon should appear in your toolbar

## Usage

### Basic Workflow

1. **Start Backend**: Ensure backend is running on port 8555

2. **Navigate to Target**: Open the website you want to analyze

3. **Start Monitoring**: Click the Sidecar extension icon and click "Start Monitoring"

4. **Browse Normally**: Interact with the web application as usual

5. **View Analysis**: Events are automatically sent to backend for AI analysis

6. **Check Console**: Open Attack Console via popup to see findings

### What Gets Captured

#### HTTP Transactions
- All requests and responses
- Headers, methods, status codes
- Request/response bodies
- Automatically tagged with security patterns

#### DOM Changes
- Initial page structure
- Dynamic DOM mutations (debounced to 500ms)
- Limited to 50 snapshots per page

#### JavaScript Execution
Functions being monitored:
- `innerHTML` / `outerHTML` setters
- `eval()` calls
- `document.write()` / `document.writeln()`
- `postMessage()` calls
- `addEventListener('message', ...)`
- `Function` constructor
- `setTimeout()` / `setInterval()` with string arguments
- `insertAdjacentHTML()`
- `location.href` setter

#### Storage State
- `localStorage` contents
- `sessionStorage` contents
- Accessible cookies (non-HttpOnly)
- Polled every 5 seconds

## Architecture

```
Web Page
    ↓
content-script.js ──→ DOM Snapshots
    |                 Storage State
    |
    ↓ injects
interceptor.js ──→ JS Function Calls
    |
    ↓ postMessage
content-script.js
    |
    ↓ chrome.runtime.sendMessage
background.js ──→ HTTP Transactions (via Debugger API)
    |
    ↓ WebSocket
Backend Server (localhost:8555)
```

## Files

- `manifest.json` - Extension configuration (MV3)
- `background.js` - Service worker, network interception, WebSocket
- `content-script.js` - DOM monitoring, storage inspection
- `interceptor.js` - JavaScript function hooking
- `popup.html` - Control interface UI
- `popup.js` - Popup logic
- `icons/` - Extension icons

## Troubleshooting

### Extension Not Loading
- Check Chrome version (must support Manifest V3)
- Look for errors in `chrome://extensions/`
- Ensure all files are present

### Backend Connection Failed
- Verify backend is running: `curl http://localhost:8555/`
- Check WebSocket connection in background service worker console
- Look for CORS errors

### No Events Captured
1. Check monitoring is started (blue dot in popup)
2. Open background service worker console: `chrome://extensions/` → "Service worker"
3. Verify debugger attached: should see console logs like `[Sidecar] Debugger attached`
4. Check for errors in content script console (regular DevTools)

### Debugger Detached
- Chrome automatically detaches debugger when DevTools is opened
- Close DevTools or restart monitoring
- This is a Chrome security feature

## Permissions Required

- `debugger` - For network interception via Chrome Debugger Protocol
- `webRequest` - For request metadata
- `scripting` - For content script injection
- `storage` - For extension state
- `activeTab` - For current tab access
- `tabs` - For tab management
- `<all_urls>` - Required for debugging any site

## Security Considerations

⚠️ **This extension is for security testing only**

- Only use on sites you have permission to test
- Extension captures sensitive data (cookies, tokens, etc.)
- All data stays local (only sent to localhost:8555)
- Do not use on production systems without authorization

## Development

### Console Logging

**Background Service Worker**:
```
chrome://extensions/ → Sidecar → "Service worker" link
```

**Content Scripts**:
```
Regular DevTools console on the page
```

**Popup**:
```
Right-click popup → "Inspect"
```

### Live Reload

Changes to files require:
- Background script changes: Click reload on `chrome://extensions/`
- Content scripts: Reload the target page
- Popup: Close and reopen popup

## Known Limitations

1. **Debugger Conflicts**: Cannot run while Chrome DevTools Network tab is open
2. **DOM Snapshot Limit**: Max 50 snapshots per page to avoid performance issues
3. **Binary Responses**: Large binary files may cause memory issues
4. **SPA Detection**: Heavy SPAs may generate many DOM snapshots
5. **HttpOnly Cookies**: Cannot access HttpOnly cookies (by design)

## Next Steps

See main project README for:
- Backend setup
- Attack Console UI
- OpenRouter API configuration
- Full system architecture

## License

See project root LICENSE file.
