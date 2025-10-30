// HTTP Traffic Tagger Frontend Application

const API_BASE = '/api';

// Application state
const state = {
    tags: [],
    selectedTags: new Set(),
    records: [],
    expandedRecords: new Set(),
    tagColors: {} // Map of tag name to color
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    loadTags();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('clear-filters').addEventListener('click', clearFilters);
}

// Generate a color palette for tags
function generateTagColors(tags) {
    // Predefined color palette with good contrast
    const colors = [
        '#e74c3c', // red
        '#3498db', // blue
        '#2ecc71', // green
        '#f39c12', // orange
        '#9b59b6', // purple
        '#1abc9c', // turquoise
        '#e67e22', // dark orange
        '#34495e', // dark gray
        '#16a085', // dark turquoise
        '#27ae60', // dark green
        '#2980b9', // dark blue
        '#8e44ad', // dark purple
        '#c0392b', // dark red
        '#d35400', // pumpkin
        '#7f8c8d', // gray
        '#e91e63', // pink
        '#00bcd4', // cyan
        '#ff5722', // deep orange
        '#795548', // brown
        '#607d8b'  // blue gray
    ];
    
    const tagColors = {};
    tags.forEach((tag, index) => {
        tagColors[tag.name] = colors[index % colors.length];
    });
    return tagColors;
}

// Load all available tags
async function loadTags() {
    try {
        const response = await fetch(`${API_BASE}/tags`);
        if (!response.ok) throw new Error('Failed to fetch tags');
        
        const data = await response.json();
        state.tags = data.tags || [];
        
        // Generate colors for all tags
        state.tagColors = generateTagColors(state.tags);
        
        renderTags();
    } catch (error) {
        console.error('Error loading tags:', error);
        document.getElementById('tags-container').innerHTML = 
            '<p class="error">Error loading tags. Please refresh the page.</p>';
    }
}

// Render tags in the sidebar
function renderTags() {
    const container = document.getElementById('tags-container');
    
    if (state.tags.length === 0) {
        container.innerHTML = '<p class="info">No tags found. Ingest data first.</p>';
        return;
    }
    
    container.innerHTML = state.tags.map(tag => {
        const color = state.tagColors[tag.name] || '#667eea';
        const style = state.selectedTags.has(tag.name) ? `style="background-color: ${color}; border-color: ${color};"` : '';
        return `
            <div class="tag-item ${state.selectedTags.has(tag.name) ? 'selected' : ''}" 
                 data-tag="${tag.name}"
                 ${style}
                 onclick="toggleTag('${escapeHtml(tag.name)}')">
                <input type="checkbox" 
                       ${state.selectedTags.has(tag.name) ? 'checked' : ''}
                       onclick="event.stopPropagation(); toggleTag('${escapeHtml(tag.name)}')">
                <span class="tag-name">${escapeHtml(tag.name)}</span>
                <span class="tag-count">${tag.count}</span>
            </div>
        `;
    }).join('');
}

// Toggle tag selection
function toggleTag(tagName) {
    if (state.selectedTags.has(tagName)) {
        state.selectedTags.delete(tagName);
    } else {
        state.selectedTags.add(tagName);
    }
    
    renderTags();
    renderSelectedTags();
    loadRecords();
}

// Clear all filters
function clearFilters() {
    state.selectedTags.clear();
    renderTags();
    renderSelectedTags();
    document.getElementById('records-container').innerHTML = 
        '<p class="info">Select tags to filter records</p>';
}

// Render selected tags in the content header
function renderSelectedTags() {
    const container = document.getElementById('selected-tags');
    
    if (state.selectedTags.size === 0) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = Array.from(state.selectedTags).map(tag => {
        const color = state.tagColors[tag] || '#667eea';
        return `
            <div class="selected-tag" style="background-color: ${color};">
                ${escapeHtml(tag)}
                <button onclick="toggleTag('${escapeHtml(tag)}')" title="Remove filter">×</button>
            </div>
        `;
    }).join('');
}

// Load records based on selected tags
async function loadRecords() {
    const container = document.getElementById('records-container');
    
    if (state.selectedTags.size === 0) {
        container.innerHTML = '<p class="info">Select tags to filter records</p>';
        return;
    }
    
    container.innerHTML = '<p class="loading">Loading records...</p>';
    
    try {
        const tagsParam = Array.from(state.selectedTags).join(',');
        const response = await fetch(`${API_BASE}/records?tags=${encodeURIComponent(tagsParam)}`);
        
        if (!response.ok) throw new Error('Failed to fetch records');
        
        const data = await response.json();
        state.records = data.records || [];
        
        renderRecords();
    } catch (error) {
        console.error('Error loading records:', error);
        container.innerHTML = '<p class="error">Error loading records. Please try again.</p>';
    }
}

// Render records list
function renderRecords() {
    const container = document.getElementById('records-container');
    
    if (state.records.length === 0) {
        container.innerHTML = '<p class="info">No records found with the selected tags.</p>';
        return;
    }
    
    container.innerHTML = state.records.map(record => `
        <div class="record-item" data-record-id="${record.id}">
            <div class="record-summary" onclick="toggleRecordDetails('${record.id}')">
                <div class="record-header">
                    <div>
                        <span class="record-method method-${record.method}">${record.method}</span>
                        <span class="record-status status-${getStatusClass(record.response_status_code)}">
                            ${record.response_status_code}
                        </span>
                    </div>
                    <span class="record-host">${escapeHtml(record.host)}</span>
                </div>
                <div class="record-path">${escapeHtml(record.path)}</div>
                <div class="record-tags">
                    ${record.tags.map(tag => {
                        const color = state.tagColors[tag] || '#667eea';
                        return `<span class="record-tag" style="background-color: ${color}; color: white;">${escapeHtml(tag)}</span>`;
                    }).join('')}
                </div>
            </div>
            <div class="record-details" id="details-${record.id}">
                <p class="loading">Loading details...</p>
            </div>
        </div>
    `).join('');
}

// Toggle record details expansion
async function toggleRecordDetails(recordId) {
    const detailsDiv = document.getElementById(`details-${recordId}`);
    
    if (state.expandedRecords.has(recordId)) {
        // Collapse
        state.expandedRecords.delete(recordId);
        detailsDiv.classList.remove('expanded');
    } else {
        // Expand and load details
        state.expandedRecords.add(recordId);
        detailsDiv.classList.add('expanded');
        
        // Load full record details if not already loaded
        if (detailsDiv.innerHTML.includes('Loading details')) {
            await loadRecordDetails(recordId);
        }
    }
}

// Load full record details
async function loadRecordDetails(recordId) {
    const detailsDiv = document.getElementById(`details-${recordId}`);
    
    try {
        const response = await fetch(`${API_BASE}/record/${recordId}`);
        
        if (!response.ok) throw new Error('Failed to fetch record details');
        
        const record = await response.json();
        
        // Apply highlights to request and response text
        const highlightedRequest = applyHighlights(record.decoded_request, record.highlights || {});
        const highlightedResponse = applyHighlights(record.decoded_response, record.highlights || {});
        
        detailsDiv.innerHTML = `
            <div class="http-content">
                <h3>Request</h3>
                <pre>${highlightedRequest}</pre>
            </div>
            <div class="http-content">
                <h3>Response</h3>
                <pre>${highlightedResponse}</pre>
            </div>
        `;
    } catch (error) {
        console.error('Error loading record details:', error);
        detailsDiv.innerHTML = '<p class="error">Error loading details. Please try again.</p>';
    }
}

// Apply highlights to text based on matched values
function applyHighlights(text, highlights) {
    if (!text || !highlights || Object.keys(highlights).length === 0) {
        return escapeHtml(text);
    }
    
    // Escape HTML first
    let highlightedText = escapeHtml(text);
    
    // Create a map of match -> tags (for coloring)
    const matchToTags = {};
    Object.entries(highlights).forEach(([tag, matches]) => {
        matches.forEach(match => {
            // Skip negative conditions and empty matches
            if (match && !match.startsWith('(not:')) {
                if (!matchToTags[match]) {
                    matchToTags[match] = [];
                }
                matchToTags[match].push(tag);
            }
        });
    });
    
    // Sort matches by length (descending) to handle longer matches first
    // This prevents partial matches from breaking longer ones
    const sortedMatches = Object.keys(matchToTags).sort((a, b) => b.length - a.length);
    
    // Apply highlights to each unique match with tag color
    sortedMatches.forEach(match => {
        if (match) {
            // Escape the match for use in regex
            const escapedMatch = match.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            // Create case-insensitive global regex
            const regex = new RegExp(escapedMatch, 'gi');
            
            // Get the first tag's color for this match
            const tag = matchToTags[match][0];
            const color = state.tagColors[tag] || '#ffeb3b';
            
            // Replace with highlighted version using tag color
            highlightedText = highlightedText.replace(regex, (matched) => {
                return `<span class="highlight" style="background-color: ${color};">${matched}</span>`;
            });
        }
    });
    
    return highlightedText;
}

// Get status code class for styling
function getStatusClass(statusCode) {
    if (statusCode >= 200 && statusCode < 300) return '2xx';
    if (statusCode >= 300 && statusCode < 400) return '3xx';
    if (statusCode >= 400 && statusCode < 500) return '4xx';
    if (statusCode >= 500) return '5xx';
    return '2xx';
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
