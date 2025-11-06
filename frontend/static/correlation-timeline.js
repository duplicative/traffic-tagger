/**
 * Correlation Timeline
 * 
 * Displays HTTP records with their correlated sidecar events in chronological order
 */

// State
let timelineState = {
    currentPage: 1,
    pageSize: 20,
    totalPages: 1,
    urlFilter: '',
    timeline: [],
    stats: null
};

// Event type icons
const EVENT_TYPE_ICONS = {
    'DOM_SNAPSHOT': '📄',
    'JS_EXECUTION': '⚡',
    'STORAGE_STATE': '💾'
};

// Event type colors
const EVENT_TYPE_COLORS = {
    'DOM_SNAPSHOT': '#3b82f6',
    'JS_EXECUTION': '#f59e0b',
    'STORAGE_STATE': '#8b5cf6'
};

/**
 * Initialize correlation timeline
 */
function initCorrelationTimeline() {
    console.log('[Timeline] Initializing correlation timeline');
    
    // Load statistics
    loadTimelineStats();
    
    // Load timeline data
    loadTimelineData();
    
    // Setup event listeners
    setupTimelineEventListeners();
}

/**
 * Setup event listeners for timeline controls
 */
function setupTimelineEventListeners() {
    // Apply filters
    document.getElementById('apply-timeline-filters').addEventListener('click', () => {
        timelineState.urlFilter = document.getElementById('url-filter-timeline').value;
        timelineState.currentPage = 1;
        loadTimelineData();
    });
    
    // Clear filters
    document.getElementById('clear-timeline-filters').addEventListener('click', () => {
        document.getElementById('url-filter-timeline').value = '';
        timelineState.urlFilter = '';
        timelineState.currentPage = 1;
        loadTimelineData();
    });
    
    // Pagination
    document.getElementById('timeline-prev-page').addEventListener('click', () => {
        if (timelineState.currentPage > 1) {
            timelineState.currentPage--;
            loadTimelineData();
        }
    });
    
    document.getElementById('timeline-next-page').addEventListener('click', () => {
        if (timelineState.currentPage < timelineState.totalPages) {
            timelineState.currentPage++;
            loadTimelineData();
        }
    });
}

/**
 * Load timeline statistics
 */
async function loadTimelineStats() {
    try {
        const response = await fetch('/api/correlation-stats');
        const stats = await response.json();
        
        timelineState.stats = stats;
        renderTimelineStats(stats);
    } catch (error) {
        console.error('[Timeline] Error loading stats:', error);
        document.getElementById('timeline-stats').innerHTML = 
            '<span class="stat error">Error loading statistics</span>';
    }
}

/**
 * Render timeline statistics
 */
function renderTimelineStats(stats) {
    const statsContainer = document.getElementById('timeline-stats');
    
    const correlationRate = stats.http_records.correlation_rate || 0;
    const totalRecords = stats.http_records.total || 0;
    const withEvents = stats.http_records.with_correlated_events || 0;
    const totalEvents = stats.enrichment_events.total || 0;
    const avgEvents = stats.correlation_metrics.avg_events_per_record || 0;
    
    statsContainer.innerHTML = `
        <span class="stat">
            <strong>${totalRecords}</strong> HTTP Records
        </span>
        <span class="stat">
            <strong>${withEvents}</strong> Correlated (${correlationRate}%)
        </span>
        <span class="stat">
            <strong>${totalEvents}</strong> Sidecar Events
        </span>
        <span class="stat">
            Avg <strong>${avgEvents}</strong> events/record
        </span>
    `;
}

/**
 * Load timeline data from API
 */
async function loadTimelineData() {
    const container = document.getElementById('timeline-container');
    container.innerHTML = '<p class="info">Loading timeline...</p>';
    
    try {
        // Build query parameters
        const params = new URLSearchParams({
            page: timelineState.currentPage,
            page_size: timelineState.pageSize
        });
        
        if (timelineState.urlFilter) {
            params.append('url_filter', timelineState.urlFilter);
        }
        
        const response = await fetch(`/api/correlation-timeline?${params}`);
        const data = await response.json();
        
        timelineState.timeline = data.timeline;
        timelineState.totalPages = data.pagination.total_pages;
        
        renderTimeline(data);
        updateTimelinePagination(data.pagination);
    } catch (error) {
        console.error('[Timeline] Error loading timeline:', error);
        container.innerHTML = '<p class="error">Error loading timeline data</p>';
    }
}

/**
 * Render timeline entries
 */
function renderTimeline(data) {
    const container = document.getElementById('timeline-container');
    
    if (data.timeline.length === 0) {
        container.innerHTML = `
            <div class="timeline-empty">
                <p>No correlated records found.</p>
                <p class="info">Records will appear here when sidecar events are correlated with HTTP traffic.</p>
            </div>
        `;
        return;
    }
    
    const timelineHTML = data.timeline.map(entry => renderTimelineEntry(entry)).join('');
    container.innerHTML = timelineHTML;
    
    // Setup expand/collapse handlers
    setupTimelineEntryHandlers();
}

/**
 * Render a single timeline entry
 */
function renderTimelineEntry(entry) {
    const record = entry.http_record;
    const events = entry.correlated_events;
    const stats = entry.statistics;
    const window = entry.correlation_window;
    
    // Format timestamp
    const timestamp = new Date(record.timestamp * 1000).toLocaleString();
    
    // Status code class
    const statusClass = record.status >= 200 && record.status < 300 ? 'status-success' :
                       record.status >= 400 && record.status < 500 ? 'status-client-error' :
                       record.status >= 500 ? 'status-server-error' : '';
    
    // Time window
    const windowStart = new Date(window.start * 1000).toLocaleString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const windowEnd = window.end ? new Date(window.end * 1000).toLocaleString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    }) : '∞';
    
    // Build event types summary
    const eventTypesSummary = Object.entries(stats.event_types)
        .map(([type, count]) => `${EVENT_TYPE_ICONS[type]} ${count}`)
        .join(' ');
    
    return `
        <div class="timeline-entry" data-record-id="${record.id}">
            <div class="timeline-entry-header" onclick="toggleTimelineEntry('${record.id}')">
                <div class="timeline-timestamp">${timestamp}</div>
                <div class="timeline-http-info">
                    <span class="http-method method-${record.method}">${record.method}</span>
                    <span class="http-url">${record.path}</span>
                    <span class="http-status ${statusClass}">${record.status}</span>
                </div>
                <div class="timeline-stats-compact">
                    <span class="stat-badge">${stats.total_events} events</span>
                    ${stats.tags_added > 0 ? `<span class="stat-badge tags-badge">${stats.tags_added} tags</span>` : ''}
                    <span class="expand-icon">▼</span>
                </div>
            </div>
            
            <div class="timeline-entry-content" style="display: none;">
                <div class="timeline-meta">
                    <div class="meta-row">
                        <strong>Full URL:</strong> ${record.url}
                    </div>
                    <div class="meta-row">
                        <strong>Correlation Window:</strong> ${windowStart} → ${windowEnd}
                        ${window.end ? ` (${Math.round((window.end - window.start) / 60)}m)` : ''}
                    </div>
                    ${record.tags.length > 0 ? `
                    <div class="meta-row">
                        <strong>Tags:</strong> ${record.tags.map(tag => 
                            `<span class="tag-badge">${tag}</span>`
                        ).join(' ')}
                    </div>
                    ` : ''}
                </div>
                
                ${events.length > 0 ? `
                <div class="correlated-events">
                    <h4>Correlated Events (${events.length})</h4>
                    ${events.map(event => renderCorrelatedEvent(event)).join('')}
                </div>
                ` : '<p class="info">No correlated events</p>'}
            </div>
        </div>
    `;
}

/**
 * Render a correlated event
 */
function renderCorrelatedEvent(event) {
    const icon = EVENT_TYPE_ICONS[event.eventType] || '📦';
    const color = EVENT_TYPE_COLORS[event.eventType] || '#6b7280';
    
    // Format time delta
    const deltaStr = event.time_delta > 0 ? `+${event.time_delta}s` : `${event.time_delta}s`;
    
    return `
        <div class="event-item">
            <span class="event-icon" style="color: ${color}">${icon}</span>
            <span class="event-type">${event.eventType}</span>
            <span class="event-delta">${deltaStr}</span>
            <span class="event-id">${event.eventId.substring(0, 8)}...</span>
        </div>
    `;
}

/**
 * Toggle timeline entry expansion
 */
function toggleTimelineEntry(recordId) {
    const entry = document.querySelector(`.timeline-entry[data-record-id="${recordId}"]`);
    if (!entry) return;
    
    const content = entry.querySelector('.timeline-entry-content');
    const icon = entry.querySelector('.expand-icon');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.textContent = '▲';
        entry.classList.add('expanded');
    } else {
        content.style.display = 'none';
        icon.textContent = '▼';
        entry.classList.remove('expanded');
    }
}

/**
 * Setup event handlers for timeline entries
 */
function setupTimelineEntryHandlers() {
    // Already handled via onclick in HTML
}

/**
 * Update timeline pagination controls
 */
function updateTimelinePagination(pagination) {
    const paginationContainer = document.getElementById('timeline-pagination');
    const pageInfo = document.getElementById('timeline-page-info');
    const prevButton = document.getElementById('timeline-prev-page');
    const nextButton = document.getElementById('timeline-next-page');
    
    if (pagination.total_pages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    
    paginationContainer.style.display = 'flex';
    pageInfo.textContent = `Page ${pagination.page} of ${pagination.total_pages}`;
    
    prevButton.disabled = pagination.page <= 1;
    nextButton.disabled = pagination.page >= pagination.total_pages;
}

// Initialize when tab is activated
document.addEventListener('DOMContentLoaded', () => {
    // Listen for tab changes
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            if (this.dataset.tab === 'correlation-timeline') {
                // Delay to ensure tab is visible
                setTimeout(() => {
                    initCorrelationTimeline();
                }, 100);
            }
        });
    });
});
