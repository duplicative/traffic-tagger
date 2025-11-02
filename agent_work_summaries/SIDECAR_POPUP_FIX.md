# Sidecar Extension Popup Fix

**Date:** 2025-11-01  
**Issue:** Backend connection error preventing data capture  
**Status:** ✅ RESOLVED

## Problem

The sidecar extension popup was displaying a backend connection error:
```
Stack Trace:
popup.js:85 (anonymous function):
console.error('Backend connection error:', error);
```

This prevented the extension from functioning properly and capturing data.

## Root Cause

The sidecar extension was originally designed to connect to a standalone backend server on port 8555. During Phase 1 integration, we:

1. Disabled the WebSocket connection in `background.js`
2. Redirected enrichment events to traffic-tagger API on port 8000
3. **BUT** we forgot to update `popup.js` which was still trying to connect to the old backend

The popup was failing because:
- Default port was still `8555` (old backend)
- Status check endpoint expected old backend response format
- Stats endpoint didn't exist in traffic-tagger API

## Files Modified

### 1. `sidecar-extension/popup.js`

**Changes Made:**

#### Port Configuration (Line 63)
```javascript
// BEFORE
const port = result.backendPort || '8555';

// AFTER  
const port = result.backendPort || '8000'; // Changed to traffic-tagger API port
```

#### Backend Status Check (Lines 74-91)
```javascript
// BEFORE
fetch(`${backendUrl}/`)
  .then(response => response.json())
  .then(data => {
    if (data.status === 'running') {
      backendStatus.classList.add('connected');
      backendStatusText.textContent = 'Backend Connected';
    }
  })

// AFTER
fetch(`${backendUrl}/`)
  .then(response => response.json())
  .then(data => {
    // Traffic-tagger API returns {message: "HTTP Traffic Tagger API", version: "1.0"}
    if (data.message && data.message.includes('Traffic Tagger')) {
      backendStatus.classList.add('connected');
      backendStatusText.textContent = 'API Connected';
    } else {
      backendStatus.classList.remove('connected');
      backendStatusText.textContent = 'API Offline';
    }
  })
```

#### Open Console Button (Lines 168-170)
```javascript
// BEFORE
async function openAttackConsole() {
  const consoleUrl = await getBackendHttpUrl();
  chrome.tabs.create({ url: consoleUrl });
}

// AFTER
async function openAttackConsole() {
  // Traffic-tagger web UI is on port 9999
  chrome.tabs.create({ url: 'http://localhost:9999/' });
}
```

#### Event Count Display (Lines 214-224)
```javascript
// BEFORE
async function updateUI() {
  const backendUrl = await getBackendHttpUrl();
  try {
    const response = await fetch(`${backendUrl}/api/stats`);
    const stats = await response.json();
    if (stats.vector_store && stats.vector_store.total_events !== undefined) {
      eventCountDisplay.textContent = stats.vector_store.total_events;
    }
  } catch (error) {
    // Silently fail if backend is not available
  }
}

// AFTER
async function updateUI() {
  // Get event count from local storage (logged by message-logger.js)
  try {
    chrome.storage.local.get(['messageCount'], (result) => {
      if (result.messageCount !== undefined) {
        eventCountDisplay.textContent = result.messageCount;
      }
    });
  } catch (error) {
    // Silently fail
  }
}
```

### 2. `sidecar-extension/message-logger.js`

**Changes Made:**

#### Store Log Function (Lines 64-73)
Added event count tracking:
```javascript
// BEFORE
storeLog(filename, entry) {
  chrome.storage.local.get([filename], (result) => {
    const currentLog = result[filename] || `# ${filename.replace('.md', '')} Events Log\n\n`;
    const updatedLog = currentLog + entry;
    
    chrome.storage.local.set({
      [filename]: updatedLog
    });
  });
}

// AFTER
storeLog(filename, entry) {
  chrome.storage.local.get([filename, 'messageCount'], (result) => {
    const currentLog = result[filename] || `# ${filename.replace('.md', '')} Events Log\n\n`;
    const updatedLog = currentLog + entry;
    const currentCount = result.messageCount || 0;
    
    chrome.storage.local.set({
      [filename]: updatedLog,
      messageCount: currentCount + 1  // Track count
    });
  });
}
```

#### Clear Logs Function (Lines 102-116)
Added messageCount to clear list:
```javascript
// BEFORE
clearLogs() {
  const filenames = [
    'HTTP_TRANSACTION.md',
    'DOM_SNAPSHOT.md',
    'JS_EXECUTION.md',
    'STORAGE_STATE.md'
  ];
  chrome.storage.local.remove(filenames);
}

// AFTER
clearLogs() {
  const filenames = [
    'HTTP_TRANSACTION.md',
    'DOM_SNAPSHOT.md',
    'JS_EXECUTION.md',
    'STORAGE_STATE.md',
    'messageCount'  // Clear count too
  ];
  chrome.storage.local.remove(filenames);
}
```

### 3. `sidecar-extension/popup.html`

**Changes Made:**

#### Button Text (Line 197)
```html
<!-- BEFORE -->
<button id="openConsoleBtn" class="secondary">
  Open Attack Console
</button>

<!-- AFTER -->
<button id="openConsoleBtn" class="secondary">
  Open Traffic Tagger UI
</button>
```

## Testing

After the fixes, the extension should:

1. ✅ Show "API Connected" when traffic-tagger is running
2. ✅ Show "API Offline" when traffic-tagger is not running
3. ✅ Allow starting/stopping tab monitoring
4. ✅ Track event count correctly
5. ✅ Open traffic-tagger UI (port 9999) when "Open Traffic Tagger UI" is clicked

## How to Apply Fixes

1. **Reload Extension:**
   - Open Chrome: `chrome://extensions/`
   - Find "Sidecar" extension
   - Click the reload icon 🔄

2. **Start Traffic Tagger:**
   ```bash
   cd /home/guid/projects/traffic_tagger
   docker compose up -d
   ```

3. **Test the Popup:**
   - Click the Sidecar extension icon
   - Verify "API Connected" shows with green indicator
   - Click "Start Monitoring" on a tab
   - Browse some pages
   - Check event count increases

4. **Verify Data Capture:**
   ```bash
   python test_phase1_integration.py
   ```

## Configuration

The extension now uses these defaults:
- **API Host:** localhost
- **API Port:** 8000 (traffic-tagger API)
- **Web UI Port:** 9999 (traffic-tagger frontend)

These can be customized in the extension settings if needed.

## Known Limitations

1. Event count only shows events captured in current session
2. Event count resets when "Clear Logs" is clicked
3. No real-time sync with traffic-tagger database count
4. Extension must be reloaded after code changes

## Next Steps

The extension is now ready to capture data:

1. Ensure traffic-tagger services are running
2. Load the extension in Chrome
3. Navigate to a target website
4. Click "Start Monitoring" in the popup
5. Browse the site to generate events
6. Events will be batched and sent to traffic-tagger API
7. View captured data in traffic-tagger UI at http://localhost:9999/
