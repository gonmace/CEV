document.addEventListener('DOMContentLoaded', function () {
    // Notifications dropdown functionality
    const notificationsToggle = document.getElementById('notifications-toggle');
    const notificationsDropdown = document.getElementById('notifications-dropdown');

    if (notificationsToggle && notificationsDropdown) {
        notificationsToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            notificationsDropdown.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!notificationsToggle.contains(e.target) && !notificationsDropdown.contains(e.target)) {
                notificationsDropdown.classList.add('hidden');
            }
        });
    }

    // Mark all notifications as read functionality
    const markAllReadBtn = document.getElementById('mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function (e) {
            e.preventDefault();
            
            // Send AJAX request to mark all notifications as read
            fetch('/api/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Hide the notifications count
                    const notificationsCount = document.getElementById('notifications-count');
                    if (notificationsCount) {
                        notificationsCount.classList.add('hidden');
                    }
                    
                    // Update the notifications list
                    const notificationsList = document.getElementById('notifications-list');
                    if (notificationsList) {
                        notificationsList.innerHTML = `
                            <div class="px-4 py-6 text-center">
                                <i class="fas fa-bell-slash text-gray-400 text-2xl mb-2"></i>
                                <p class="text-sm text-gray-500">No hay notificaciones nuevas</p>
                            </div>
                        `;
                    }
                    
                    // Hide the mark all read button
                    markAllReadBtn.parentElement.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error marking notifications as read:', error);
            });
        });
    }

    // Function to get CSRF token from cookies
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

    // Close notifications dropdown when pressing Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && notificationsDropdown) {
            notificationsDropdown.classList.add('hidden');
        }
    });
}); 