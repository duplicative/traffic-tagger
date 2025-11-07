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
            return `<div class="sidecar-event"><strong>${event.type}:</strong> ${event.eventType} at ${new Date(event.timestamp).toLocaleTimeString()}</div>`;
        }).join('');

        return `
            <div class="timeline-record">
                <div class="http-record" onclick="toggleSidecarEvents(this)">
                    <span class="record-method method-${httpRecord.method}">${httpRecord.method}</span>
                    <span class="record-status">${httpRecord.response_status_code}</span>
                    <span class="record-host">${httpRecord.host}</span>
                    <span class="record-path">${httpRecord.path}</span>
                    <span class="record-time">${new Date(httpRecord.response_created_at * 1000).toLocaleTimeString()}</span>
                </div>
                <div class="sidecar-events-container" style="display: none;">
                    ${sidecarEventsHtml}
                </div>
            </div>
        `;
    }).join('');
}

function toggleSidecarEvents(element) {
    const sidecarContainer = element.nextElementSibling;
    if (sidecarContainer.style.display === 'none') {
        sidecarContainer.style.display = 'block';
    } else {
        sidecarContainer.style.display = 'none';
    }
}
