document.addEventListener('DOMContentLoaded', function() {
    // Image preview functionality
    const fileInput = document.getElementById('lane-images');
    const previewContainer = document.getElementById('image-previews');
    const uploadForm = document.getElementById('upload-form');
    const loadingIndicator = document.getElementById('loading');
    
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            previewContainer.innerHTML = ''; // Clear previous previews
            
            if (this.files.length < 2 || this.files.length > 4) {
                showAlert('Please select 2-4 images for traffic lanes', 'danger');
                this.value = ''; // Reset the input
                return;
            }
            
            // Create a preview row
            const row = document.createElement('div');
            row.className = 'row';
            previewContainer.appendChild(row);
            
            // Display previews for each selected file
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                
                // Check if file is an image
                if (!file.type.match('image.*')) {
                    showAlert('Please select only image files', 'danger');
                    fileInput.value = '';
                    previewContainer.innerHTML = '';
                    return;
                }
                
                // Create column for this preview
                const col = document.createElement('div');
                col.className = 'col-md-3 mb-3';
                
                // Create preview container
                const previewWrapper = document.createElement('div');
                previewWrapper.className = 'lane-container';
                
                // Create label
                const laneLabel = document.createElement('h6');
                laneLabel.textContent = `Lane ${i+1}`;
                laneLabel.className = 'mb-2';
                previewWrapper.appendChild(laneLabel);
                
                // Create image element
                const img = document.createElement('img');
                img.className = 'img-fluid';
                img.style.borderRadius = '5px';
                
                // Create file reader to read and display the image
                const reader = new FileReader();
                reader.onload = function(e) {
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
                
                previewWrapper.appendChild(img);
                col.appendChild(previewWrapper);
                row.appendChild(col);
            }
        });
    }
    
    // Handle form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            loadingIndicator.style.display = 'block';
        });
    }
    
    // Handle tabs
    const tabs = document.querySelectorAll('.nav-tabs .nav-link');
    if (tabs.length > 0) {
        tabs.forEach(tab => {
            tab.addEventListener('click', function(e) {
                e.preventDefault();
                const target = this.getAttribute('data-bs-target');
                
                // Hide all tab contents
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.remove('show', 'active');
                });
                
                // Deactivate all tabs
                tabs.forEach(t => {
                    t.classList.remove('active');
                });
                
                // Activate the clicked tab
                this.classList.add('active');
                
                // Show the target content
                document.querySelector(target).classList.add('show', 'active');
            });
        });
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Function to show alert messages
function showAlert(message, type) {
    const alertsContainer = document.getElementById('alerts');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // Auto-close alert after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            alertsContainer.removeChild(alert);
        }, 150);
    }, 5000);
}
