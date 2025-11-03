/**
 * Sidecar Background Service Worker
 * Manages network interception, debugger attachment, and WebSocket communication with backend.
 * Implements PRD section 3.1.
 */

// Import message logger
import { messageLogger } from './message-logger.js';

// Configuration
const RECONNECT_DELAY = 5000; // 5 seconds
const TAGGER_API_URL = 'http://localhost:8000/api/enrichment-events'; // Traffic Tagger API

// State management
let websocket = null;
let monitoredTabs = new Set();
let pendingRequests = new Map(); // requestId -> request data
let eventQueue = []; // Queue for events when WebSocket is disconnected
const MAX_QUEUE_SIZE = 100;
let enrichmentEventsBatch = []; // Batch enrichment events for traffic-tagger
const BATCH_SIZE = 10;
const BATCH_TIMEOUT = 5000; // 5 seconds
let batchTimer = null;

/**
 * WebSocket Connection Management (DISABLED for traffic-tagger integration)
 * Enrichment events now go directly to traffic-tagger API via HTTP
 */
class BackendConnection {
  constructor() {
    // WebSocket functionality disabled
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.isConnecting = false;
    this.backendUrl = '';
  }

  async getBackendUrl() {
    // Disabled - using HTTP API instead
    return null;
  }

  async connect() {
    // Disabled - using HTTP API instead
    console.log('[Sidecar] WebSocket connection disabled - using HTTP API for enrichment events');
  }

  scheduleReconnect() {
    // Disabled
  }

  sendEvent(event) {
    // Disabled - HTTP_TRANSACTION events no longer sent
    console.log('[Sidecar] WebSocket sendEvent disabled - HTTP_TRANSACTION events not sent');
  }

  queueEvent(event) {
    // Disabled
  }

  flushQueue() {
    // Disabled
  }

  handleMessage(message) {
    // Disabled
  }

  disconnect() {
    // Disabled
  }
}

const backendConnection = new BackendConnection();

/**
 * Send enrichment events to traffic-tagger API
 */
async function sendEnrichmentData(events) {
  if (events.length === 0) {
    return;
  }

  try {
    const response = await fetch(TAGGER_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ events })
    });

    if (response.ok) {
      const result = await response.json();
      console.log('[Sidecar] Sent enrichment events to traffic-tagger:', result);
    } else {
      console.error('[Sidecar] Error sending enrichment events:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('[Sidecar] Error sending enrichment events:', error);
  }
}

/**
 * Batch enrichment events and send periodically
 */
function addEnrichmentEvent(event) {
  enrichmentEventsBatch.push(event);
  
  // Send immediately if batch is full
  if (enrichmentEventsBatch.length >= BATCH_SIZE) {
    flushEnrichmentBatch();
  } else {
    // Schedule batch send if not already scheduled
    if (!batchTimer) {
      batchTimer = setTimeout(flushEnrichmentBatch, BATCH_TIMEOUT);
    }
  }
}

function flushEnrichmentBatch() {
  if (batchTimer) {
    clearTimeout(batchTimer);
    batchTimer = null;
  }
  
  if (enrichmentEventsBatch.length > 0) {
    const eventsToSend = [...enrichmentEventsBatch];
    enrichmentEventsBatch = [];
    sendEnrichmentData(eventsToSend);
  }
}

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
 * Send HTTP Transaction Event to Backend (DISABLED)
 * HTTP traffic is ingested via CSV files in traffic-tagger
 */
function sendHttpTransactionEvent(requestData) {
  // HTTP_TRANSACTION events disabled - traffic-tagger uses CSV ingestion
  console.log('[Sidecar] HTTP_TRANSACTION event disabled (CSV ingestion used):', requestData.request.url);
  // No longer sending HTTP_TRANSACTION events
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

    console.log('[Sidecar] Batching DOM_SNAPSHOT for traffic-tagger:', event.url);
    messageLogger.logMessage(event);
    addEnrichmentEvent(event);
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

    console.log('[Sidecar] Batching JS_EXECUTION for traffic-tagger:', message.functionName);
    messageLogger.logMessage(event);
    addEnrichmentEvent(event);
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

    console.log('[Sidecar] Batching STORAGE_STATE for traffic-tagger:', event.url);
    messageLogger.logMessage(event);
    addEnrichmentEvent(event);
    sendResponse({ success: true });
  }
  else if (message.type === 'START_MONITORING') {
    startMonitoring(message.tabId);
    sendResponse({ success: true });
  }
  else if (message.type === 'STOP_MONITORING') {
    stopMonitoring(message.tabId);
    sendResponse({ success: true });
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
console.log('[Sidecar] Traffic-tagger integration mode: enrichment events sent to', TAGGER_API_URL);
console.log('[Sidecar] HTTP_TRANSACTION events disabled (CSV ingestion used)');
// backendConnection.connect(); // Disabled - using HTTP API instead
