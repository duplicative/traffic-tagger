const API_BASE_TIMELINE = '/api/timeline';

async function loadTimelineData() {
    const container = document.getElementById('timeline-container');
    container.innerHTML = '<p class="loading">Loading timeline data...</p>';

    try {
        const response = await fetch(API_BASE_TIMELINE);
        if (!response.ok) {
            throw new Error('Failed to fetch timeline data');
        }
        const data = await response.json();
        renderTimeline(data.timeline);
    } catch (error) {
        console.error('Error loading timeline data:', error);
        container.innerHTML = '<p class="error">Error loading timeline data. Please try again.</p>';
    }
}

function renderTimeline(timelineData) {
    const container = document.getElementById('timeline-container');
    if (!timelineData || timelineData.length === 0) {
        container.innerHTML = '<p class="info">No timeline data available.</p>';
        return;
    }

    container.innerHTML = timelineData.map(httpRecord => {
        const sidecarEventsHtml = httpRecord.sidecar_events.map(event => {
            const eventData = event.data ? JSON.stringify(event.data, null, 2) : '{}';
            return `
                <div class="sidecar-event">
                    <div class="sidecar-summary" onclick="toggleSidecarEventDetails(this)">
                        <strong>${event.type}</strong>: ${event.eventType}
                        <span class="event-time">${new Date(event.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div class="sidecar-details" style="display: none;">
                        <pre><code>${escapeHtml(eventData)}</code></pre>
                    </div>
                </div>
            `;
        }).join('');

        const request = httpRecord.decoded_request || '';
        const response = httpRecord.decoded_response || '';

        const reflections = Array.isArray(httpRecord.reflections) ? httpRecord.reflections : [];
        const reflectionsText = reflections.length > 0 ? `Reflected Values: ${reflections.join(', ')}` : '';
        const reflectionBadge = reflections.length > 0
            ? `<span class="reflection-badge" title="${escapeHtml(reflectionsText)}">[Input Reflected]</span>`
            : '';

        return `
            <div class="timeline-record">
                <div class="http-record" onclick="toggleHttpRecordDetails(this)">
                    <span class="record-method method-${httpRecord.method}">${httpRecord.method}</span>
                    <span class="record-status status-${getStatusClass(httpRecord.response_status_code)}">${httpRecord.response_status_code}</span>
                    <span class="record-host">${httpRecord.host}</span>
                    <span class="record-path">${httpRecord.path}</span>
                    ${reflectionBadge}
                    <span class="record-time">${new Date(httpRecord.response_created_at * 1000).toLocaleTimeString()}</span>
                </div>
                <div class="timeline-details" style="display: none;">
                    <div class="http-details">
                        <div class="http-content">
                            <h3>Request</h3>
                            <pre>${escapeHtml(request)}</pre>
                        </div>
                        <div class="http-content">
                            <h3>Response</h3>
                            <pre>${escapeHtml(response)}</pre>
                        </div>
                    </div>
                </div>
                <div class="sidecar-events-container" style="display: none;">
                    ${sidecarEventsHtml}
                </div>
            </div>
        `;
    }).join('');
}

function toggleHttpRecordDetails(element) {
    const detailsContainer = element.nextElementSibling;
    if (detailsContainer) {
        if (detailsContainer.style.display === 'none') {
            detailsContainer.style.display = 'block';
        } else {
            detailsContainer.style.display = 'none';
        }
    }
    const sidecarContainer = element.nextElementSibling.nextElementSibling;
    if (sidecarContainer) {
        if (sidecarContainer.style.display === 'none') {
            sidecarContainer.style.display = 'block';
        } else {
            sidecarContainer.style.display = 'none';
        }
    }
}

function toggleSidecarEventDetails(element) {
    const detailsContainer = element.nextElementSibling;
    if (detailsContainer) {
        if (detailsContainer.style.display === 'none') {
            detailsContainer.style.display = 'block';
        } else {
            detailsContainer.style.display = 'none';
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// This function is defined in app.js, but we need it here as well.
// This is not ideal, but it's the quickest way to get the status class.
function getStatusClass(statusCode) {
    if (statusCode >= 200 && statusCode < 300) return '2xx';
    if (statusCode >= 300 && statusCode < 400) return '3xx';
    if (statusCode >= 400 && statusCode < 500) return '4xx';
    if (statusCode >= 500) return '5xx';
    return '2xx';
}
