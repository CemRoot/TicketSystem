/**
 * Main JavaScript file for the Ticket Management System
 */

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Dynamic form functionality for ticket create/edit
function updateCategoryDropdown() {
    const departmentSelect = document.getElementById('id_department');
    const categorySelect = document.getElementById('id_category');
    const subcategorySelect = document.getElementById('id_subcategory');
    
    // Exit if any of the required elements don't exist
    if (!departmentSelect || !categorySelect || !subcategorySelect) {
        return;
    }
    
    const departmentId = departmentSelect.value;
    
    if (departmentId) {
        // Clear current options
        categorySelect.innerHTML = '<option value="">Select Category</option>';
        subcategorySelect.innerHTML = '<option value="">Select Subcategory</option>';
        
        // Fetch categories for the selected department
        fetch(`/api/categories/?department_id=${departmentId}`)
            .then(response => response.json())
            .then(data => {
                data.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category.id;
                    option.textContent = category.name;
                    categorySelect.appendChild(option);
                });
                
                // Enable category select
                categorySelect.disabled = false;
            })
            .catch(error => console.error('Error fetching categories:', error));
    } else {
        // Disable selects if no department is selected
        categorySelect.innerHTML = '<option value="">Select Category</option>';
        categorySelect.disabled = true;
        subcategorySelect.innerHTML = '<option value="">Select Subcategory</option>';
        subcategorySelect.disabled = true;
    }
}

// Update subcategories when category changes
function updateSubcategoryDropdown() {
    const categorySelect = document.getElementById('id_category');
    if (!categorySelect) return; // Exit if element doesn't exist
    
    const categoryId = categorySelect.value;
    const subcategorySelect = document.getElementById('id_subcategory');
    
    if (!subcategorySelect) return; // Exit if element doesn't exist
    
    if (categoryId) {
        // Clear current options
        subcategorySelect.innerHTML = '<option value="">Select Subcategory</option>';
        
        // Fetch subcategories for the selected category
        fetch(`/api/subcategories/?category_id=${categoryId}`)
            .then(response => response.json())
            .then(data => {
                data.forEach(subcategory => {
                    const option = document.createElement('option');
                    option.value = subcategory.id;
                    option.textContent = subcategory.name;
                    subcategorySelect.appendChild(option);
                });
                
                // Enable subcategory select
                subcategorySelect.disabled = false;
            })
            .catch(error => console.error('Error fetching subcategories:', error));
    } else {
        // Disable subcategory select if no category is selected
        subcategorySelect.innerHTML = '<option value="">Select Subcategory</option>';
        subcategorySelect.disabled = true;
    }
}

// Initialize department/category/subcategory dropdowns
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page with the ticket form
    const departmentSelect = document.getElementById('id_department');
    const categorySelect = document.getElementById('id_category');
    
    // Only set up listeners if the form elements exist
    if (departmentSelect && categorySelect) {
        departmentSelect.addEventListener('change', updateCategoryDropdown);
        categorySelect.addEventListener('change', updateSubcategoryDropdown);
        
        // Initialize values if we're editing a ticket
        if (departmentSelect.value) {
            updateCategoryDropdown();
            
            // If category is also pre-selected, update subcategories
            if (categorySelect.value) {
                updateSubcategoryDropdown();
            }
        }
    }
});

// Mark notification as read
function markNotificationAsRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/mark-read/`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ is_read: true })
    })
    .then(response => {
        if (response.ok) {
            // Update UI to mark notification as read
            const notificationElement = document.getElementById(`notification-${notificationId}`);
            if (notificationElement) {
                notificationElement.classList.remove('notification-unread');
            }
            
            // Update notification count
            const countElement = document.getElementById('notification-count');
            if (countElement) {
                let count = parseInt(countElement.textContent);
                if (count > 0) {
                    countElement.textContent = count - 1;
                }
            }
        }
    })
    .catch(error => console.error('Error marking notification as read:', error));
}

// Get CSRF Token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// AI Analysis Tooltips
document.addEventListener('DOMContentLoaded', function() {
    const aiAnalysisElements = document.querySelectorAll('.ai-analysis-badge');
    
    aiAnalysisElements.forEach(element => {
        element.addEventListener('click', function() {
            const ticketId = this.getAttribute('data-ticket-id');
            
            fetch(`/api/tickets/${ticketId}/ai-analysis/`)
                .then(response => response.json())
                .then(data => {
                    // Safely handle confidence score which might be missing
                    const confidenceScore = data.confidence_score !== undefined ? 
                        data.confidence_score : 
                        (data.category_confidence !== undefined ? data.category_confidence : 'N/A');
                    
                    // Safely handle department which might be missing
                    const suggestedDepartment = data.suggested_department || 'N/A';
                    
                    const content = `
                        <div class="ai-tooltip">
                            <div><strong>Sentiment:</strong> ${data.sentiment_score || 'N/A'}</div>
                            <div><strong>Priority Suggestion:</strong> ${data.suggested_priority || 'N/A'}</div>
                            <div><strong>Category Suggestion:</strong> ${data.suggested_category || 'N/A'}</div>
                            <div><strong>Department Suggestion:</strong> ${suggestedDepartment}</div>
                            <div><strong>Staff Suggestion:</strong> ${data.suggested_staff || 'None'}</div>
                        </div>
                    `;
                    
                    // Update popover content
                    const popover = bootstrap.Popover.getInstance(element);
                    if (popover) {
                        popover.setContent({
                            '.popover-body': content
                        });
                    }
                })
                .catch(error => console.error('Error fetching AI analysis:', error));
        });
    });
});

// Dashboard charts initialization
function initDashboardCharts() {
    // Check if charts container exists
    if (!document.getElementById('ticket-status-chart') || 
        !document.getElementById('ticket-priority-chart') || 
        !document.getElementById('tickets-over-time-chart')) {
        return;
    }
    
    // Fetch dashboard data
    fetch('/api/dashboard-data/')
        .then(response => response.json())
        .then(data => {
            // Status distribution chart
            const statusCtx = document.getElementById('ticket-status-chart').getContext('2d');
            new Chart(statusCtx, {
                type: 'doughnut',
                data: {
                    labels: data.status_distribution.labels,
                    datasets: [{
                        data: data.status_distribution.values,
                        backgroundColor: [
                            '#007bff', '#ffc107', '#28a745', '#dc3545', '#6c757d'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right',
                        }
                    }
                }
            });
            
            // Priority distribution chart
            const priorityCtx = document.getElementById('ticket-priority-chart').getContext('2d');
            new Chart(priorityCtx, {
                type: 'pie',
                data: {
                    labels: data.priority_distribution.labels,
                    datasets: [{
                        data: data.priority_distribution.values,
                        backgroundColor: [
                            '#28a745', '#ffc107', '#fd7e14', '#dc3545'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right',
                        }
                    }
                }
            });
            
            // Tickets over time chart
            const timeCtx = document.getElementById('tickets-over-time-chart').getContext('2d');
            new Chart(timeCtx, {
                type: 'line',
                data: {
                    labels: data.tickets_over_time.labels,
                    datasets: [{
                        label: 'New Tickets',
                        data: data.tickets_over_time.values,
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Ticket Count'
                            },
                            beginAtZero: true
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Error fetching dashboard data:', error));
}

// Initialize dashboard charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.dashboard-container')) {
        // Load Chart.js from CDN if not already loaded
        if (typeof Chart === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
            script.onload = initDashboardCharts;
            document.head.appendChild(script);
        } else {
            initDashboardCharts();
        }
    }
});
