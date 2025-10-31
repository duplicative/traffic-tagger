/**
 * Sidecar Background Service Worker
 * Manages network interception, debugger attachment, and WebSocket communication with backend.
 * Implements PRD section 3.1.
 */

// Import message logger
importScripts('message-logger.js');

// Configuration
const RECONNECT_DELAY = 5000; // 5 seconds

// State management
let websocket = null;
let monitoredTabs = new Set();
let pendingRequests = new Map(); // requestId -> request data
let eventQueue = []; // Queue for events when WebSocket is disconnected
const MAX_QUEUE_SIZE = 100;

/**
 * WebSocket Connection Management
 */
class BackendConnection {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.isConnecting = false;
    this.backendUrl = '';
  }

  async getBackendUrl() {
    return new Promise((resolve) => {
      chrome.storage.sync.get(['backendIp', 'backendPort'], (result) => {
        const ip = result.backendIp || 'localhost';
        const port = result.backendPort || '8555';
        resolve(`ws://${ip}:${port}/ws/events`);
      });
    });
  }

  async connect() {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;
    this.backendUrl = await this.getBackendUrl();
    console.log('[Sidecar] Connecting to backend...', this.backendUrl);

    try {
      this.ws = new WebSocket(this.backendUrl);

      this.ws.onopen = () => {
        console.log('[Sidecar] Connected to backend');
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.flushQueue();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (e) {
          console.error('[Sidecar] Error parsing message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[Sidecar] WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('[Sidecar] Disconnected from backend');
        this.isConnecting = false;
        this.ws = null;
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error('[Sidecar] Connection error:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[Sidecar] Reconnecting in ${RECONNECT_DELAY}ms (attempt ${this.reconnectAttempts})...`);
      setTimeout(() => this.connect(), RECONNECT_DELAY);
    } else {
      console.error('[Sidecar] Max reconnection attempts reached. Please restart the extension.');
    }
  }

  sendEvent(event) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(event));
      } catch (e) {
        console.error('[Sidecar] Error sending event:', e);
        this.queueEvent(event);
      }
    } else {
      this.queueEvent(event);
    }
  }

  queueEvent(event) {
    if (eventQueue.length < MAX_QUEUE_SIZE) {
      eventQueue.push(event);
    } else {
      console.warn('[Sidecar] Event queue full, dropping oldest event');
      eventQueue.shift();
      eventQueue.push(event);
    }
  }

  flushQueue() {
    console.log(`[Sidecar] Flushing ${eventQueue.length} queued events`);
    while (eventQueue.length > 0) {
      const event = eventQueue.shift();
      this.sendEvent(event);
    }
  }

  handleMessage(message) {
    if (message.type === 'ack') {
      console.log('[Sidecar] Event acknowledged:', message.eventId);
    } else if (message.type === 'error') {
      console.error('[Sidecar] Backend error:', message.message);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

const backendConnection = new BackendConnection();

/**
 * Network Interception using Chrome Debugger API
 * Implements PRD section 3.1.2
 */
async function startMonitoring(tabId) {
  if (monitoredTabs.has(tabId)) {
    console.log('[Sidecar] Tab already being monitored:', tabId);
    return;
  }

  try {
    // Attach debugger
    await chrome.debugger.attach({ tabId }, '1.3');
    console.log('[Sidecar] Debugger attached to tab:', tabId);

    // Enable Network domain
    await chrome.debugger.sendCommand({ tabId }, 'Network.enable');
    console.log('[Sidecar] Network domain enabled for tab:', tabId);

    monitoredTabs.add(tabId);
  } catch (error) {
    console.error('[Sidecar] Error starting monitoring:', error);
  }
}

async function stopMonitoring(tabId) {
  if (!monitoredTabs.has(tabId)) {
    return;
  }

  try {
    await chrome.debugger.detach({ tabId });
    console.log('[Sidecar] Debugger detached from tab:', tabId);
    monitoredTabs.delete(tabId);
    
    // Clean up pending requests for this tab
    for (const [requestId, data] of pendingRequests.entries()) {
      if (data.tabId === tabId) {
        pendingRequests.delete(requestId);
      }
    }
  } catch (error) {
    console.error('[Sidecar] Error stopping monitoring:', error);
  }
}

/**
 * Chrome Debugger Event Handlers
 */
chrome.debugger.onEvent.addListener((source, method, params) => {
  const tabId = source.tabId;

  if (!monitoredTabs.has(tabId)) {
    return;
  }

  // Handle Network.requestWillBeSent
  if (method === 'Network.requestWillBeSent') {
    const { requestId, request, timestamp } = params;
    
    pendingRequests.set(requestId, {
      tabId,
      request: {
        method: request.method,
        url: request.url,
        headers: Object.entries(request.headers || {}).map(([name, value]) => ({ name, value })),
        body: request.postData || null
      },
      timestamp: new Date(timestamp * 1000).toISOString()
    });
  }

  // Handle Network.responseReceived
  if (method === 'Network.responseReceived') {
    const { requestId, response } = params;
    const requestData = pendingRequests.get(requestId);

    if (requestData) {
      requestData.response = {
        statusCode: response.status,
        statusText: response.statusText,
        headers: Object.entries(response.headers || {}).map(([name, value]) => ({ name, value })),
        body: null // Will be fetched in loadingFinished
      };
    }
  }

  // Handle Network.loadingFinished
  if (method === 'Network.loadingFinished') {
    const { requestId } = params;
    const requestData = pendingRequests.get(requestId);

    if (requestData && requestData.response) {
      // Fetch response body
      chrome.debugger.sendCommand({ tabId }, 'Network.getResponseBody', { requestId }, (result) => {
        if (chrome.runtime.lastError) {
          console.warn('[Sidecar] Could not get response body:', chrome.runtime.lastError.message);
        } else if (result) {
          requestData.response.body = result.base64Encoded 
            ? atob(result.body)
            : result.body;
        }

        // Send complete HTTP transaction event
        sendHttpTransactionEvent(requestData);
        pendingRequests.delete(requestId);
      });
    }
  }

  // Handle Network.loadingFailed
  if (method === 'Network.loadingFailed') {
    const { requestId } = params;
    pendingRequests.delete(requestId);
  }
});

/**
 * Send HTTP Transaction Event to Backend
 */
function sendHttpTransactionEvent(requestData) {
  const event = {
    eventId: generateUUID(),
    timestamp: requestData.timestamp,
    eventType: 'HTTP_TRANSACTION',
    url: requestData.request.url,
    data: {
      request: requestData.request,
      response: requestData.response
    }
  };

  console.log('[Sidecar] Sending HTTP_TRANSACTION:', event.url);
  messageLogger.logMessage(event);
  backendConnection.sendEvent(event);
}

/**
 * Handle messages from content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Sidecar] Received message from content script:', message);

  if (message.type === 'DOM_SNAPSHOT') {
    const event = {
      eventId: generateUUID(),
      timestamp: new Date().toISOString(),
      eventType: 'DOM_SNAPSHOT',
      url: message.url,
      data: {
        html: message.html,
        mutations: message.mutations || []
      }
    };

    console.log('[Sidecar] Sending DOM_SNAPSHOT:', event.url);
    messageLogger.logMessage(event);
    backendConnection.sendEvent(event);
    sendResponse({ success: true });
  } 
  else if (message.type === 'JS_EXECUTION') {
    const event = {
      eventId: generateUUID(),
      timestamp: new Date().toISOString(),
      eventType: 'JS_EXECUTION',
      url: message.url,
      data: {
        functionName: message.functionName,
        inputValue: message.inputValue,
        stackTrace: message.stackTrace
      }
    };

    console.log('[Sidecar] Sending JS_EXECUTION:', message.functionName);
    messageLogger.logMessage(event);
    backendConnection.sendEvent(event);
    sendResponse({ success: true });
  }
  else if (message.type === 'STORAGE_STATE') {
    const event = {
      eventId: generateUUID(),
      timestamp: new Date().toISOString(),
      eventType: 'STORAGE_STATE',
      url: message.url,
      data: {
        localStorage: message.localStorage,
        sessionStorage: message.sessionStorage,
        cookies: message.cookies
      }
    };

    console.log('[Sidecar] Sending STORAGE_STATE:', event.url);
    messageLogger.logMessage(event);
    backendConnection.sendEvent(event);
    sendResponse({ success: true });
  }
  else if (message.type === 'START_MONITORING') {
    startMonitoring(message.tabId);
    sendResponse({ success: true });
  }
  else if (message.type === 'STOP_MONITORING') {
    stopMonitoring(message.tabId);
    sendResponse({ success. true });
  }
  else if (message.type === 'DOWNLOAD_LOGS') {
    messageLogger.downloadLogs();
    sendResponse({ success: true });
  }
  else if (message.type === 'CLEAR_LOGS') {
    messageLogger.clearLogs();
    sendResponse({ success: true });
  }

  return true; // Keep channel open for async response
});

/**
 * Handle tab closure
 */
chrome.tabs.onRemoved.addListener((tabId) => {
  if (monitoredTabs.has(tabId)) {
    stopMonitoring(tabId);
  }
});

/**
 * Handle debugger detach
 */
chrome.debugger.onDetach.addListener((source, reason) => {
  const tabId = source.tabId;
  console.log('[Sidecar] Debugger detached from tab:', tabId, 'Reason:', reason);
  monitoredTabs.delete(tabId);
});

/**
 * Utility Functions
 */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Initialize Extension
 */
console.log('[Sidecar] Background service worker initialized');
backendConnection.connect();
