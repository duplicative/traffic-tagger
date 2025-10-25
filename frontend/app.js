let selectedTags = [];

async function fetchTags() {
    const response = await fetch('/api/tags');
    const data = await response.json();
    const tagsList = document.getElementById('tags-list');
    data.tags.forEach(tag => {
        const button = document.createElement('button');
        button.className = 'tag-button';
        button.textContent = `${tag.name} (${tag.count})`;
        button.onclick = () => toggleTag(tag.name);
        tagsList.appendChild(button);
    });
}

function toggleTag(tagName) {
    const index = selectedTags.indexOf(tagName);
    if (index > -1) {
        selectedTags.splice(index, 1);
    } else {
        selectedTags.push(tagName);
    }
    fetchRecords();
}

async function fetchRecords() {
    const tagsParam = selectedTags.join(',');
    const url = tagsParam ? `/api/records?tags=${encodeURIComponent(tagsParam)}` : '/api/records';
    const response = await fetch(url);
    const data = await response.json();
    const recordsList = document.getElementById('records-list');
    recordsList.innerHTML = '';
    data.records.forEach(record => {
        const recordDiv = document.createElement('div');
        recordDiv.className = 'record-item';
        recordDiv.innerHTML = `
            <strong>${record.method} ${record.path}</strong><br>
            Host: ${record.host}<br>
            Status: ${record.response_status_code}<br>
            Tags: ${record.tags.join(', ')}
        `;
        recordDiv.onclick = () => toggleRecordDetails(recordDiv, record.id);
        recordsList.appendChild(recordDiv);
    });
}

async function toggleRecordDetails(recordDiv, recordId) {
    const details = recordDiv.querySelector('.record-details');
    if (details) {
        details.style.display = details.style.display === 'none' ? 'block' : 'none';
    } else {
        const response = await fetch(`/api/record/${recordId}`);
        const record = await response.json();
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'record-details';
        detailsDiv.innerHTML = `
            <h3>Decoded Request</h3>
            <pre>${record.decoded_request}</pre>
            <h3>Decoded Response</h3>
            <pre>${record.decoded_response}</pre>
        `;
        recordDiv.appendChild(detailsDiv);
        detailsDiv.style.display = 'block';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchTags();
    fetchRecords();  // initial load all
});
