document.addEventListener('DOMContentLoaded', function () {
    // Sidebar toggle functionality
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('-translate-x-full');
            sidebarOverlay.classList.toggle('hidden');
        });
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function () {
            sidebar.classList.add('-translate-x-full');
            sidebarOverlay.classList.add('hidden');
        });
    }

    // Profile dropdown functionality
    const profileDropdownToggle = document.querySelector('.profile-dropdown-toggle');
    const profileDropdown = document.querySelector('.profile-dropdown');

    if (profileDropdownToggle && profileDropdown) {
        profileDropdownToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            profileDropdown.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!profileDropdownToggle.contains(e.target) && !profileDropdown.contains(e.target)) {
                profileDropdown.classList.add('hidden');
            }
        });
    }

    // Modules dropdown functionality
    const modulesDropdownToggle = document.querySelector('.modules-dropdown-toggle');
    const modulesDropdown = document.querySelector('.modules-dropdown');

    if (modulesDropdownToggle && modulesDropdown) {
        modulesDropdownToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            modulesDropdown.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!modulesDropdownToggle.contains(e.target) && !modulesDropdown.contains(e.target)) {
                modulesDropdown.classList.add('hidden');
            }
        });
    }

    // Close dropdowns when pressing Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if (profileDropdown) profileDropdown.classList.add('hidden');
            if (modulesDropdown) modulesDropdown.classList.add('hidden');
        }
    });
}); 