// Enhanced Face Attendance System JavaScript
class AttendanceSystem {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeComponents();
        this.startRealTimeUpdates();
    }

    setupEventListeners() {
        // Global click handlers
        document.addEventListener('click', this.handleGlobalClicks.bind(this));
        
        // Form submissions
        document.addEventListener('submit', this.handleFormSubmissions.bind(this));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
    }

    initializeComponents() {
        this.initializeTooltips();
        this.initializeModals();
        this.initializeNotifications();
    }

    startRealTimeUpdates() {
        // Update clock every minute
        setInterval(() => {
            this.updateClock();
        }, 60000);

        // Check for new notifications every 30 seconds
        setInterval(() => {
            this.checkNotifications();
        }, 30000);
    }

    // Utility Functions
    showNotification(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${this.getNotificationIcon(type)} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        const container = document.querySelector('.toast-container') || this.createToastContainer();
        container.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();

        // Remove from DOM after hide
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }

    updateClock() {
        const clockElements = document.querySelectorAll('.live-clock');
        if (clockElements.length > 0) {
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
            clockElements.forEach(el => {
                el.textContent = timeString;
            });
        }
    }

    async checkNotifications() {
        // Simulate checking for new notifications
        if (Math.random() > 0.8) { // 20% chance of new notification
            this.showNotification('New attendance record submitted', 'info');
        }
    }

    // API Functions
    async apiCall(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        };

        try {
            const response = await fetch(endpoint, { ...defaultOptions, ...options });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            this.showNotification('Network error occurred', 'danger');
            throw error;
        }
    }

    async markAttendance(studentId, courseId, method = 'auto', confidence = null) {
        try {
            const data = await this.apiCall('/api/manual-attendance', {
                method: 'POST',
                body: JSON.stringify({
                    student_id: studentId,
                    course_id: courseId,
                    method: method,
                    confidence: confidence
                })
            });

            this.showNotification(`Attendance marked for student`, 'success');
            return data;
        } catch (error) {
            this.showNotification('Failed to mark attendance', 'danger');
            throw error;
        }
    }

    async exportData(courseId, format = 'csv', startDate = null, endDate = null) {
        try {
            let url = `/api/export-attendance/${courseId}`;
            const params = new URLSearchParams();
            
            if (format) params.append('format', format);
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            
            if (params.toString()) {
                url += `?${params.toString()}`;
            }

            // Trigger download
            const link = document.createElement('a');
            link.href = url;
            link.download = `attendance_${courseId}_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            this.showNotification('Export started successfully', 'success');
        } catch (error) {
            this.showNotification('Export failed', 'danger');
            throw error;
        }
    }

    // UI Components
    initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    initializeModals() {
        // Auto-focus first input in modals
        document.addEventListener('shown.bs.modal', function (event) {
            const modal = event.target;
            const input = modal.querySelector('input, select, textarea');
            if (input) {
                input.focus();
            }
        });
    }

    initializeNotifications() {
        // Notification bell animation
        const notificationBell = document.querySelector('.fa-bell');
        if (notificationBell) {
            notificationBell.addEventListener('click', function() {
                this.classList.add('fa-shake');
                setTimeout(() => this.classList.remove('fa-shake'), 500);
            });
        }
    }

    // Event Handlers
    handleGlobalClicks(event) {
        // Handle data-action attributes
        const actionElement = event.target.closest('[data-action]');
        if (actionElement) {
            const action = actionElement.getAttribute('data-action');
            this.handleAction(action, actionElement);
        }

        // Handle confirmation dialogs
        if (event.target.hasAttribute('data-confirm')) {
            const message = event.target.getAttribute('data-confirm');
            if (!confirm(message)) {
                event.preventDefault();
                event.stopPropagation();
            }
        }
    }

    handleAction(action, element) {
        const actions = {
            'export-data': () => this.handleExport(element),
            'mark-present': () => this.handleMarkPresent(element),
            'mark-absent': () => this.handleMarkAbsent(element),
            'view-details': () => this.handleViewDetails(element),
            'quick-stats': () => this.handleQuickStats(element)
        };

        if (actions[action]) {
            actions[action]();
        }
    }

    handleFormSubmissions(event) {
        const form = event.target;
        
        // Add loading state
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Processing...';
            submitButton.disabled = true;

            // Revert after form processing (you might want to do this in the form's success callback)
            setTimeout(() => {
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }, 3000);
        }
    }

    handleKeyboardShortcuts(event) {
        // Ctrl/Cmd + S for save
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {
            event.preventDefault();
            this.quickSave();
        }

        // Escape key to close modals
        if (event.key === 'Escape') {
            this.closeAllModals();
        }
    }

    // Specific Action Handlers
    handleExport(element) {
        const courseId = element.getAttribute('data-course-id');
        const format = element.getAttribute('data-format') || 'csv';
        this.exportData(courseId, format);
    }

    handleMarkPresent(element) {
        const studentId = element.getAttribute('data-student-id');
        const courseId = element.getAttribute('data-course-id');
        this.markAttendance(studentId, courseId, 'manual', 100);
    }

    handleMarkAbsent(element) {
        const studentId = element.getAttribute('data-student-id');
        const courseId = element.getAttribute('data-course-id');
        
        this.apiCall('/api/mark-absent', {
            method: 'POST',
            body: JSON.stringify({
                student_id: studentId,
                course_id: courseId
            })
        }).then(() => {
            this.showNotification('Student marked as absent', 'warning');
        });
    }

    handleViewDetails(element) {
        const itemId = element.getAttribute('data-item-id');
        const type = element.getAttribute('data-item-type');
        
        // This would typically open a detailed view modal
        console.log(`Viewing details for ${type} with ID: ${itemId}`);
    }

    handleQuickStats(element) {
        const courseId = element.getAttribute('data-course-id');
        
        this.apiCall(`/api/course-stats/${courseId}`)
            .then(stats => {
                this.showStatsModal(stats);
            });
    }

    // Additional Utility Methods
    quickSave() {
        this.showNotification('Changes saved successfully', 'success');
    }

    closeAllModals() {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }

    showStatsModal(stats) {
        // Create and show a stats modal
        const modalHtml = `
            <div class="modal fade" id="statsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Course Statistics</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <strong>Total Students:</strong> ${stats.total_students}
                                </div>
                                <div class="col-md-6">
                                    <strong>Today Present:</strong> ${stats.today_present}
                                </div>
                                <div class="col-md-6">
                                    <strong>Average Attendance:</strong> ${stats.avg_attendance}
                                </div>
                                <div class="col-md-6">
                                    <strong>Attendance Rate:</strong> ${stats.attendance_rate}%
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('statsModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add new modal to DOM and show it
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('statsModal'));
        modal.show();
    }

    // Search and Filter functionality
    initializeSearch(tableId, searchInputId) {
        const searchInput = document.getElementById(searchInputId);
        const table = document.getElementById(tableId);
        
        if (!searchInput || !table) return;

        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // Real-time updates for live attendance
    initializeLiveAttendance(courseId) {
        // This would set up WebSocket or polling for real-time updates
        setInterval(() => {
            this.updateLiveAttendance(courseId);
        }, 5000); // Update every 5 seconds
    }

    async updateLiveAttendance(courseId) {
        try {
            const response = await this.apiCall(`/api/live-attendance-stats/${courseId}`);
            this.updateAttendanceDisplay(response);
        } catch (error) {
            console.error('Failed to update live attendance:', error);
        }
    }

    updateAttendanceDisplay(stats) {
        // Update the attendance counters and progress bars
        const presentCount = document.getElementById('presentCount');
        const attendanceProgress = document.getElementById('attendanceProgress');
        
        if (presentCount) {
            presentCount.textContent = stats.present_count;
        }
        
        if (attendanceProgress) {
            const percentage = (stats.present_count / stats.total_students * 100).toFixed(1);
            attendanceProgress.style.width = `${percentage}%`;
            attendanceProgress.textContent = `${percentage}%`;
        }
    }
}

// Camera and Face Recognition Utilities
class CameraManager {
    constructor() {
        this.stream = null;
        this.isActive = false;
    }

    async startCamera(videoElement, constraints = { video: true }) {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            videoElement.srcObject = this.stream;
            this.isActive = true;
            return true;
        } catch (error) {
            console.error('Error starting camera:', error);
            throw error;
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
            this.isActive = false;
        }
    }

    captureFrame(videoElement, canvasElement) {
        const context = canvasElement.getContext('2d');
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
        context.drawImage(videoElement, 0, 0);
        return canvasElement.toDataURL('image/jpeg');
    }

    takePhoto(videoElement) {
        const canvas = document.createElement('canvas');
        return this.captureFrame(videoElement, canvas);
    }
}

// Initialize the system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.attendanceSystem = new AttendanceSystem();
    window.cameraManager = new CameraManager();
    
    // Add any additional initialization here
    console.log('Face Attendance System initialized');
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AttendanceSystem, CameraManager };
}