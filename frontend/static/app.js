document.addEventListener("DOMContentLoaded", () => {
    const tagsList = document.getElementById("tags-list");
    const recordsList = document.getElementById("records-list");

    let selectedTags = [];

    const fetchTags = async () => {
        try {
            const response = await fetch("/api/tags");
            const data = await response.json();
            renderTags(data.tags);
        } catch (error) {
            console.error("Error fetching tags:", error);
        }
    };

    const fetchRecords = async () => {
        try {
            let url = "/api/records";
            if (selectedTags.length > 0) {
                url += `?tags=${selectedTags.join(",")}`;
            }
            const response = await fetch(url);
            const data = await response.json();
            renderRecords(data.records);
        } catch (error) {
            console.error("Error fetching records:", error);
        }
    };

    const fetchRecordDetails = async (recordId, detailsElement) => {
        try {
            const response = await fetch(`/api/record/${recordId}`);
            const data = await response.json();
            renderRecordDetails(data, detailsElement);
        } catch (error) {
            console.error("Error fetching record details:", error);
        }
    };

    const renderTags = (tags) => {
        tagsList.innerHTML = "";
        tags.forEach(tag => {
            const li = document.createElement("li");
            li.textContent = `${tag.name} (${tag.count})`;
            li.dataset.tagName = tag.name;
            li.addEventListener("click", () => toggleTag(tag.name, li));
            tagsList.appendChild(li);
        });
    };

    const renderRecords = (records) => {
        recordsList.innerHTML = "";
        records.forEach(record => {
            const li = document.createElement("li");
            li.className = "record";

            const summary = document.createElement("div");
            summary.className = "record-summary";
            summary.textContent = `${record.method} ${record.host}${record.path}`;
            
            const details = document.createElement("div");
            details.className = "record-details";

            summary.addEventListener("click", () => {
                if (details.style.display === "block") {
                    details.style.display = "none";
                } else {
                    details.style.display = "block";
                    if (!details.innerHTML) {
                        fetchRecordDetails(record._id, details);
                    }
                }
            });

            li.appendChild(summary);
            li.appendChild(details);
            recordsList.appendChild(li);
        });
    };

    const renderRecordDetails = (record, detailsElement) => {
        detailsElement.innerHTML = `
            <h4>Request</h4>
            <pre>${record.decoded_request}</pre>
            <h4>Response</h4>
            <pre>${record.decoded_response}</pre>
        `;
    };

    const toggleTag = (tagName, element) => {
        const index = selectedTags.indexOf(tagName);
        if (index > -1) {
            selectedTags.splice(index, 1);
            element.style.backgroundColor = "";
        } else {
            selectedTags.push(tagName);
            element.style.backgroundColor = "#ddd";
        }
        fetchRecords();
    };

    fetchTags();
    fetchRecords();
});
