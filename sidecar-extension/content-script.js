/**
 * Sidecar Content Script
 * Handles DOM snapshotting with MutationObserver and storage inspection.
 * Implements PRD sections 3.1.3 and 3.1.5.
 */

console.log('[Sidecar Content] Script loaded on:', window.location.href);

// Debounce utility
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * DOM Snapshot Capture
 * Implements PRD section 3.1.3
 */
class DOMSnapshotHandler {
  constructor() {
    this.observer = null;
    this.snapshotCount = 0;
    this.maxSnapshots = 50; // Limit snapshots per page to avoid spam
    this.disconnected = false;
  }

  initialize() {
    // Initial snapshot on page load
    this.captureSnapshot('initial');

    // Set up MutationObserver for dynamic changes
    this.setupMutationObserver();
  }

  captureSnapshot(reason = 'mutation') {
    if (this.disconnected) {
      return;
    }
    if (this.snapshotCount >= this.maxSnapshots) {
      console.log('[Sidecar Content] Max snapshots reached, skipping');
      return;
    }

    try {
      const html = document.documentElement.outerHTML;
      
      // Only send if HTML is substantial (avoid empty pages)
      if (html.length > 100) {
        chrome.runtime.sendMessage({
          type: 'DOM_SNAPSHOT',
          url: window.location.href,
          html: html,
          mutations: [reason],
          timestamp: new Date().toISOString()
        }, (response) => {
          if (chrome.runtime.lastError) {
            console.error('[Sidecar Content] Error sending DOM snapshot:', chrome.runtime.lastError);
          } else {
            this.snapshotCount++;
            console.log(`[Sidecar Content] DOM snapshot sent (${reason}) - count: ${this.snapshotCount}`);
          }
        });
      }
    } catch (error) {
      console.error('[Sidecar Content] Error capturing DOM snapshot:', error);
    }
  }

  setupMutationObserver() {
    // Debounced snapshot capture to avoid excessive updates
    const debouncedCapture = debounce(() => {
      this.captureSnapshot('mutation');
    }, 500); // Wait 500ms after last mutation

    this.observer = new MutationObserver((mutations) => {
      // Filter out minor mutations (like style changes on scroll)
      const significantMutations = mutations.filter(mutation => {
        if (mutation.type === 'childList') {
          return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
        }
        return mutation.type === 'attributes' && 
               !['style', 'class'].includes(mutation.attributeName);
      });

      if (significantMutations.length > 0) {
        debouncedCapture();
      }
    });

    // Observe entire document
    this.observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeOldValue: false,
      characterData: false
    });

    console.log('[Sidecar Content] MutationObserver initialized');
  }

  disconnect() {
    this.disconnected = true;
    if (this.observer) {
      this.observer.disconnect();
    }
  }
}

/**
 * Storage State Inspection
 * Implements PRD section 3.1.5
 */
class StorageInspector {
  constructor() {
    this.pollInterval = null;
    this.lastStorageState = null;
  }

  initialize() {
    // Initial storage capture
    this.captureStorage();

    // Poll for storage changes every 5 seconds
    this.pollInterval = setInterval(() => {
      this.captureStorage();
    }, 5000);
  }

  captureStorage() {
    try {
      const currentState = {
        localStorage: this.getLocalStorage(),
        sessionStorage: this.getSessionStorage(),
        cookies: this.getCookies()
      };

      // Only send if state has changed
      const stateString = JSON.stringify(currentState);
      if (stateString !== this.lastStorageState) {
        this.lastStorageState = stateString;

        chrome.runtime.sendMessage({
          type: 'STORAGE_STATE',
          url: window.location.href,
          localStorage: currentState.localStorage,
          sessionStorage: currentState.sessionStorage,
          cookies: currentState.cookies,
          timestamp: new Date().toISOString()
        }, (response) => {
          if (chrome.runtime.lastError) {
            console.error('[Sidecar Content] Error sending storage state:', chrome.runtime.lastError);
          } else {
            console.log('[Sidecar Content] Storage state sent');
          }
        });
      }
    } catch (error) {
      console.error('[Sidecar Content] Error capturing storage:', error);
    }
  }

  getLocalStorage() {
    const storage = {};
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        storage[key] = localStorage.getItem(key);
      }
    } catch (e) {
      console.warn('[Sidecar Content] Cannot access localStorage:', e);
    }
    return storage;
  }

  getSessionStorage() {
    const storage = {};
    try {
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        storage[key] = sessionStorage.getItem(key);
      }
    } catch (e) {
      console.warn('[Sidecar Content] Cannot access sessionStorage:', e);
    }
    return storage;
  }

  getCookies() {
    try {
      // Parse document.cookie (only accessible cookies, not HttpOnly)
      const cookieString = document.cookie;
      if (!cookieString) return [];

      return cookieString.split(';').map(cookie => {
        const [name, ...valueParts] = cookie.trim().split('=');
        return {
          name: name.trim(),
          value: valueParts.join('=').trim()
        };
      });
    } catch (e) {
      console.warn('[Sidecar Content] Cannot access cookies:', e);
      return [];
    }
  }

  disconnect() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }
}

/**
 * Inject Interceptor Script
 * The interceptor.js runs in the page's main world to hook JavaScript functions.
 * Implements PRD section 3.1.4
 */
function injectInterceptor() {
  try {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('interceptor.js');
    script.onload = function() {
      console.log('[Sidecar Content] Interceptor script injected');
      this.remove();
    };
    (document.head || document.documentElement).appendChild(script);
  } catch (error) {
    console.error('[Sidecar Content] Error injecting interceptor:', error);
  }
}

/**
 * Listen for messages from interceptor script
 */
window.addEventListener('message', (event) => {
  // Only accept messages from same origin
  if (event.source !== window) return;

  // Check for Sidecar messages from interceptor
  if (event.data && event.data.type === 'SIDECAR_JS_EXECUTION') {
    console.log('[Sidecar Content] Received message from interceptor:', event.data);
    const detail = event.data.detail;
    
    console.log('[Sidecar Content] Forwarding message to background script...');
    chrome.runtime.sendMessage({
      type: 'JS_EXECUTION',
      url: window.location.href,
      functionName: detail.functionName,
      inputValue: detail.inputValue,
      stackTrace: detail.stackTrace,
      timestamp: new Date().toISOString()
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[Sidecar Content] Error sending JS execution:', chrome.runtime.lastError);
      } else {
        console.log('[Sidecar Content] Message sent to background script successfully.');
      }
    });
  }
});

/**
 * Initialize all handlers
 */
let domHandler = null;
let storageInspector = null;

function initialize() {
  console.log('[Sidecar Content] Initializing...');

  // Inject interceptor for JS function hooking
  injectInterceptor();

  // Initialize DOM snapshot handler
  domHandler = new DOMSnapshotHandler();
  domHandler.initialize();

  // Initialize storage inspector
  storageInspector = new StorageInspector();
  storageInspector.initialize();

  console.log('[Sidecar Content] Initialization complete');
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  // DOM already loaded
  initialize();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (domHandler) domHandler.disconnect();
  if (storageInspector) storageInspector.disconnect();
});
