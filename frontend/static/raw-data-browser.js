// Raw Data Browser functionality

const rawDataBrowser = {
    currentPage: 1,
    pageSize: 50,
    source: 'csv',
    category: null,
    
    init() {
        this.setupTabSwitching();
        this.setupFilters();
        this.setupPagination();
    },
    
    setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Remove active class from all buttons and contents
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Add active class to clicked button and corresponding content
                button.classList.add('active');
                const tabName = button.getAttribute('data-tab');
                const tabContent = document.getElementById(`${tabName}-tab`);
                if (tabContent) {
                    tabContent.classList.add('active');
                    
                    // Load raw data when switching to raw data tab
                    if (tabName === 'raw-data') {
                        this.loadRecords();
                    }
                }
            });
        });
    },
    
    setupFilters() {
        const sourceFilter = document.getElementById('source-filter');
        const categoryFilterGroup = document.getElementById('category-filter-group');
        const applyButton = document.getElementById('apply-filters');
        
        // Show/hide category filter based on source selection
        sourceFilter.addEventListener('change', (e) => {
            if (e.target.value === 'sidecar') {
                categoryFilterGroup.style.display = 'block';
            } else {
                categoryFilterGroup.style.display = 'none';
            }
        });
        
        // Apply filters
        applyButton.addEventListener('click', () => {
            this.source = sourceFilter.value;
            this.category = document.getElementById('category-filter').value || null;
            this.currentPage = 1;
            this.loadRecords();
        });
    },
    
    setupPagination() {
        document.getElementById('prev-page').addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadRecords();
            }
        });
        
        document.getElementById('next-page').addEventListener('click', () => {
            this.currentPage++;
            this.loadRecords();
        });
    },
    
    async loadRecords() {
        const container = document.getElementById('raw-records-container');
        container.innerHTML = '<p class="loading">Loading records...</p>';
        
        try {
            // Build query parameters
            const params = new URLSearchParams({
                source: this.source,
                page: this.currentPage,
                page_size: this.pageSize
            });
            
            if (this.source === 'sidecar' && this.category) {
                params.append('category', this.category);
            }
            
            const response = await fetch(`/api/raw-records?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.records.length === 0) {
                container.innerHTML = '<p class="info">No records found matching the current filters.</p>';
                document.getElementById('raw-pagination').style.display = 'none';
                return;
            }
            
            this.renderRecords(data.records);
            this.updatePagination(data.current_page, data.total_pages, data.total_records);
            
        } catch (error) {
            console.error('Error loading raw records:', error);
            container.innerHTML = '<p class="error">Error loading records. Please try again.</p>';
        }
    },
    
    renderRecords(records) {
        const container = document.getElementById('raw-records-container');
        
        container.innerHTML = records.map((record, index) => {
            // Pretty print JSON
            const jsonString = JSON.stringify(record, null, 2);
            const highlightedCode = hljs.highlight(jsonString, { language: 'json' }).value;
            
            return `
                <div class="raw-record-item">
                    <div class="record-header">
                        <span class="record-number">#${(this.currentPage - 1) * this.pageSize + index + 1}</span>
                        ${this.getRecordTitle(record)}
                        <button class="toggle-btn" onclick="rawDataBrowser.toggleRecord(${index})">
                            <span id="toggle-icon-${index}">▼</span>
                        </button>
                    </div>
                    <div class="record-body" id="record-body-${index}">
                        <pre><code class="hljs language-json">${highlightedCode}</code></pre>
                    </div>
                </div>
            `;
        }).join('');
    },
    
    getRecordTitle(record) {
        // Generate a descriptive title based on record type
        if (record.method && record.host) {
            // CSV record
            return `<span class="record-title">${record.method} ${record.host}${record.path || ''}</span>`;
        } else if (record.eventType) {
            // Sidecar enrichment record
            return `<span class="record-title">${record.eventType} - ${record.url || 'No URL'}</span>`;
        } else if (record._collection) {
            // Sidecar record with collection info
            return `<span class="record-title">${record._collection} - ${record.url || 'No URL'}</span>`;
        } else {
            return `<span class="record-title">Record ID: ${record._id}</span>`;
        }
    },
    
    toggleRecord(index) {
        const body = document.getElementById(`record-body-${index}`);
        const icon = document.getElementById(`toggle-icon-${index}`);
        
        if (body.style.display === 'none') {
            body.style.display = 'block';
            icon.textContent = '▼';
        } else {
            body.style.display = 'none';
            icon.textContent = '▶';
        }
    },
    
    updatePagination(currentPage, totalPages, totalRecords) {
        const pagination = document.getElementById('raw-pagination');
        const pageInfo = document.getElementById('page-info');
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        
        pagination.style.display = 'flex';
        pageInfo.textContent = `Page ${currentPage} of ${totalPages} (${totalRecords} total records)`;
        
        prevButton.disabled = currentPage <= 1;
        nextButton.disabled = currentPage >= totalPages;
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    rawDataBrowser.init();
});
