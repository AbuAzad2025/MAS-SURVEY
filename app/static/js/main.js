/**
 * MAS - Surveying Computerized System
 * Main JavaScript
 */

const MAS = {
    /**
     * API base URL
     */
    apiBase: '/api',
    
    /**
     * Set current working file
     * @param {string} filename - File name to set as current
     * @param {function} callback - Callback function on success
     */
    setCurrentFile: function(filename, callback) {
        if (!filename) return;
        
        fetch(this.apiBase + '/set-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: filename })
        })
        .then(response => response.json())
        .then(data => {
            if (callback && typeof callback === 'function') {
                callback(data);
            }
        })
        .catch(error => {
            console.error('Error setting current file:', error);
        });
    },
    
    /**
     * Get current file info
     * @param {function} callback - Callback with file data
     */
    getCurrentFile: function(callback) {
        fetch(this.apiBase + '/current-file')
            .then(response => response.json())
            .then(data => {
                if (callback && typeof callback === 'function') {
                    callback(data.file);
                }
            })
            .catch(error => {
                console.error('Error getting current file:', error);
            });
    },
    
    /**
     * Load settings from API
     * @param {function} callback - Callback with settings object
     */
    loadSettings: function(callback) {
        fetch(this.apiBase + '/settings')
            .then(response => response.json())
            .then(data => {
                if (callback && typeof callback === 'function') {
                    callback(data);
                }
            })
            .catch(error => {
                console.error('Error loading settings:', error);
            });
    },
    
    /**
     * Save settings to API
     * @param {object} settings - Settings object to save
     * @param {function} callback - Callback on success
     */
    saveSettings: function(settings, callback) {
        fetch(this.apiBase + '/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        })
        .then(response => response.json())
        .then(data => {
            if (callback && typeof callback === 'function') {
                callback(data);
            }
        })
        .catch(error => {
            console.error('Error saving settings:', error);
        });
    },
    
    /**
     * Get points for current file
     * @param {function} callback - Callback with points array
     */
    getPoints: function(callback) {
        fetch(this.apiBase + '/points')
            .then(response => response.json())
            .then(data => {
                if (callback && typeof callback === 'function') {
                    callback(data);
                }
            })
            .catch(error => {
                console.error('Error getting points:', error);
            });
    },
    
    /**
     * Save points for current file
     * @param {array} points - Array of point objects
     * @param {function} callback - Callback on success
     */
    savePoints: function(points, callback) {
        fetch(this.apiBase + '/points', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ points: points })
        })
        .then(response => response.json())
        .then(data => {
            if (callback && typeof callback === 'function') {
                callback(data);
            }
        })
        .catch(error => {
            console.error('Error saving points:', error);
        });
    },
    
    /**
     * Calculate area from points
     * @param {array} points - Array of point objects with y and x
     * @param {function} callback - Callback with result
     */
    calculateArea: function(points, callback) {
        fetch(this.apiBase + '/calculate/area', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ points: points })
        })
        .then(response => response.json())
        .then(data => {
            if (callback && typeof callback === 'function') {
                callback(data);
            }
        })
        .catch(error => {
            console.error('Error calculating area:', error);
        });
    },
    
    /**
     * Show alert message
     * @param {string} message - Message to display
     * @param {string} type - Alert type ('success', 'error', 'info')
     */
    showAlert: function(message, type = 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;
        
        const container = document.querySelector('.main-content');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    },
    
    /**
     * Format number with fixed decimals
     * @param {number} value - Number to format
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted number
     */
    formatNumber: function(value, decimals = 2) {
        return Number(value).toFixed(decimals);
    },
    
    /**
     * Create new file
     * @param {string} name - File name
     * @param {string} date - File date
     * @param {string} place - Place/Location
     * @param {function} callback - Callback on success
     */
    createFile: function(name, date, place, callback) {
        fetch(this.apiBase + '/files', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: name, date: date, place: place })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                this.showAlert(data.error, 'error');
            } else if (callback && typeof callback === 'function') {
                callback(data);
            }
        })
        .catch(error => {
            console.error('Error creating file:', error);
            this.showAlert('Error creating file', 'error');
        });
    },
    
    /**
     * Delete file
     * @param {string} name - File name to delete
     * @param {function} callback - Callback on success
     */
    deleteFile: function(name, callback) {
        if (!confirm(`Are you sure you want to delete "${name}"?`)) {
            return;
        }
        
        fetch(this.apiBase + '/files/' + encodeURIComponent(name), {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (callback && typeof callback === 'function') {
                callback(data);
            }
        })
        .catch(error => {
            console.error('Error deleting file:', error);
            this.showAlert('Error deleting file', 'error');
        });
    }
};

/**
 * Initialize page functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    // File selector change handler
    const fileSelect = document.getElementById('file-select');
    if (fileSelect) {
        fileSelect.addEventListener('change', function() {
            const filename = this.value;
            if (filename) {
                MAS.setCurrentFile(filename, function() {
                    location.reload();
                });
            }
        });
    }
});
