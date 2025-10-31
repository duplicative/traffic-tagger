/**
 * Sidecar Popup Script
 * Controls extension behavior through the popup UI
 */

let currentTabId = null;
let isMonitoring = false;

// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const openConsoleBtn = document.getElementById('openConsoleBtn');
const backendStatus = document.getElementById('backendStatus');
const backendStatusText = document.getElementById('backendStatusText');
const monitoringStatus = document.getElementById('monitoringStatus');
const monitoringStatusText = document.getElementById('monitoringStatusText');
const activeTabDisplay = document.getElementById('activeTab');
const eventCountDisplay = document.getElementById('eventCount');
const downloadLogsBtn = document.getElementById('downloadLogsBtn');
const clearLogsBtn = document.getElementById('clearLogsBtn');

/**
 * Initialize popup
 */
async function initialize() {
  // Get current active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    currentTabId = tab.id;
    updateActiveTabDisplay(tab);
  }

  // Check backend connection status
  checkBackendStatus();

  // Setup event listeners
  startBtn.addEventListener('click', startMonitoring);
  stopBtn.addEventListener('click', stopMonitoring);
  openConsoleBtn.addEventListener('click', openAttackConsole);
  downloadLogsBtn.addEventListener('click', downloadLogs);
  clearLogsBtn.addEventListener('click', clearLogs);

  // Update UI periodically
  setInterval(updateUI, 1000);
}

/**
 * Update active tab display
 */
function updateActiveTabDisplay(tab) {
  const url = new URL(tab.url);
  activeTabDisplay.textContent = url.hostname || 'Unknown';
}

/**
 * Get backend HTTP URL from storage
 */
function getBackendHttpUrl() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(['backendIp', 'backendPort'], (result) => {
      const ip = result.backendIp || 'localhost';
      const port = result.backendPort || '8555';
      resolve(`http://${ip}:${port}`);
    });
  });
}

/**
 * Check backend connection status
 */
async function checkBackendStatus() {
  const backendUrl = await getBackendHttpUrl();
  // Try to connect to check status
  fetch(`${backendUrl}/`)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'running') {
        backendStatus.classList.add('connected');
        backendStatusText.textContent = 'Backend Connected';
      }
    })
    .catch(error => {
      backendStatus.classList.remove('connected');
      backendStatusText.textContent = 'Backend Offline';
      console.error('Backend connection error:', error);
    });
}

/**
 * Start monitoring current tab
 */
async function startMonitoring() {
  if (!currentTabId) {
    alert('No active tab');
    return;
  }

  try {
    // Send message to background script to start monitoring
    const response = await chrome.runtime.sendMessage({
      type: 'START_MONITORING',
      tabId: currentTabId
    });

    if (response && response.success) {
      isMonitoring = true;
      updateMonitoringUI(true);
      console.log('Monitoring started for tab:', currentTabId);
    } else {
      alert('Failed to start monitoring. Check console for errors.');
    }
  } catch (error) {
    console.error('Error starting monitoring:', error);
    alert('Error starting monitoring: ' + error.message);
  }
}

/**
 * Stop monitoring current tab
 */
async function stopMonitoring() {
  if (!currentTabId) {
    return;
  }

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'STOP_MONITORING',
      tabId: currentTabId
    });

    if (response && response.success) {
      isMonitoring = false;
      updateMonitoringUI(false);
      console.log('Monitoring stopped for tab:', currentTabId);
    }
  } catch (error) {
    console.error('Error stopping monitoring:', error);
  }
}

/**
 * Update monitoring UI state
 */
function updateMonitoringUI(monitoring) {
  if (monitoring) {
    monitoringStatus.classList.add('monitoring');
    monitoringStatusText.textContent = 'Monitoring Active';
    startBtn.disabled = true;
    stopBtn.disabled = false;
  } else {
    monitoringStatus.classList.remove('monitoring');
    monitoringStatusText.textContent = 'Not Monitoring';
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }
}

/**
 * Open Attack Console UI
 */
async function openAttackConsole() {
  const consoleUrl = await getBackendHttpUrl();
  // Open the Attack Console in a new tab
  chrome.tabs.create({ url: consoleUrl });
}

/**
 * Download all logs as markdown files
 */
async function downloadLogs() {
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'DOWNLOAD_LOGS'
    });
    
    if (response && response.success) {
      alert('Logs downloaded to your Downloads folder in sidecar_logs/');
    }
  } catch (error) {
    console.error('Error downloading logs:', error);
    alert('Error downloading logs: ' + error.message);
  }
}

/**
 * Clear all stored logs
 */
async function clearLogs() {
  if (confirm('Are you sure you want to clear all logs?')) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'CLEAR_LOGS'
      });
      
      if (response && response.success) {
        alert('All logs cleared');
      }
    } catch (error) {
      console.error('Error clearing logs:', error);
      alert('Error clearing logs: ' + error.message);
    }
  }
}

/**
 * Update UI periodically
 */
async function updateUI() {
  const backendUrl = await getBackendHttpUrl();
  // Update event count (you could get this from background script storage)
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

// Initialize on load
document.addEventListener('DOMContentLoaded', initialize);
