/**
 * Message Logger for Sidecar Extension
 * Logs all outgoing messages to markdown files in the logging directory
 */

class MessageLogger {
  constructor() {
    this.enabled = true;
  }

  /**
   * Log a message to the appropriate markdown file based on event type
   * @param {Object} event - The event object being sent to backend
   */
  async logMessage(event) {
    if (!this.enabled) return;

    try {
      const eventType = event.eventType;
      const timestamp = new Date().toISOString();
      const filename = `${eventType}.md`;

      // Format the message as markdown
      const logEntry = this.formatLogEntry(event, timestamp);

      // Send to background script to write to file
      // Note: Chrome extensions can't directly write files, so we'll use console.log
      // with a special format that can be captured if needed
      console.log(`[MESSAGE_LOG:${filename}]`, JSON.stringify({
        timestamp,
        event
      }, null, 2));

      // For now, we'll keep logs in memory and provide download capability
      this.storeLog(filename, logEntry);
    } catch (error) {
      console.error('[MessageLogger] Error logging message:', error);
    }
  }

  /**
   * Format a log entry as markdown
   */
  formatLogEntry(event, timestamp) {
    const separator = '\n---\n\n';
    
    let entry = `## Event: ${event.eventId}\n\n`;
    entry += `**Timestamp:** ${timestamp}\n\n`;
    entry += `**Event Type:** ${event.eventType}\n\n`;
    entry += `**URL:** ${event.url}\n\n`;
    entry += `**Data:**\n\n`;
    entry += '```json\n';
    entry += JSON.stringify(event.data, null, 2);
    entry += '\n```\n';
    entry += separator;

    return entry;
  }

  /**
   * Store log in memory for later download
   */
  storeLog(filename, entry) {
    // Store in chrome.storage.local
    chrome.storage.local.get([filename], (result) => {
      const currentLog = result[filename] || `# ${filename.replace('.md', '')} Events Log\n\n`;
      const updatedLog = currentLog + entry;
      
      chrome.storage.local.set({
        [filename]: updatedLog
      });
    });
  }

  /**
   * Download all logs as markdown files
   */
  async downloadLogs() {
    const filenames = [
      'HTTP_TRANSACTION.md',
      'DOM_SNAPSHOT.md',
      'JS_EXECUTION.md',
      'STORAGE_STATE.md'
    ];

    for (const filename of filenames) {
      chrome.storage.local.get([filename], (result) => {
        if (result[filename]) {
          const blob = new Blob([result[filename]], { type: 'text/markdown' });
          const url = URL.createObjectURL(blob);
          
          chrome.downloads.download({
            url: url,
            filename: `sidecar_logs/${filename}`,
            saveAs: false
          });
        }
      });
    }
  }

  /**
   * Clear all stored logs
   */
  clearLogs() {
    const filenames = [
      'HTTP_TRANSACTION.md',
      'DOM_SNAPSHOT.md',
      'JS_EXECUTION.md',
      'STORAGE_STATE.md'
    ];

    chrome.storage.local.remove(filenames);
    console.log('[MessageLogger] Logs cleared');
  }
}

// Export for use in other scripts
const messageLogger = new MessageLogger();
