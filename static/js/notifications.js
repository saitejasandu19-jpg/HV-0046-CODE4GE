/**
 * Synchronized Popup Notification Toast Manager for Vignan Campus Transport System
 * Creates visible, dynamic toast cards on the student/driver/admin UI.
 */

function showPopupNotification(type, message, busId = null) {
    const container = document.getElementById('toast-container');

    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast-card';

    let iconClass = 'fa-info-circle';
    let typeClass = 'toast-info';

    if (type === 'EMERGENCY' || message.includes('Emergency') || message.includes('emergency')) {
        iconClass = 'fa-triangle-exclamation';
        typeClass = 'toast-emergency';
    } else if (type === 'BUS_ARRIVED' || message.includes('arrived')) {
        iconClass = 'fa-circle-check';
        typeClass = 'toast-arrival';
    } else if (type === 'REPLACEMENT_BUS' || message.includes('replacement')) {
        iconClass = 'fa-repeat';
        typeClass = 'toast-replacement';
    } else if (type === 'BUS_STARTED') {
        iconClass = 'fa-circle-play';
        typeClass = 'toast-arrival';
    }

    toast.classList.add(typeClass);

    toast.innerHTML = `
        <div class="toast-icon"><i class="fa-solid ${iconClass}"></i></div>
        <div class="toast-body">
            <h5>${type.replace('_', ' ')}</h5>
            <p>${message}</p>
        </div>
        <button type="button" class="btn-close ms-auto" onclick="this.parentElement.remove()">&times;</button>
    `;

    if (container) {
        container.prepend(toast);
        // Auto remove after 7 seconds
        setTimeout(() => {
            if (toast && toast.parentElement) {
                toast.remove();
            }
        }, 7000);
    }

    // Also add to feed if feed exists
    addNotificationToFeed(type, message);
}

function addNotificationToFeed(type, message) {
    const feed = document.getElementById('notification-feed');
    if (!feed) return;

    if (feed.children.length === 1 && feed.children[0].classList.contains('text-center')) {
        feed.innerHTML = '';
    }

    const item = document.createElement('div');
    item.className = `notif-item ${type.toLowerCase()}`;
    item.style.padding = '0.5rem 0';
    item.style.borderBottom = '1px solid #e2e8f0';
    item.style.fontSize = '0.85rem';

    const nowStr = new Date().toLocaleTimeString();

    item.innerHTML = `
        <div style="display: flex; gap: 0.5rem; align-items: flex-start;">
            <i class="fa-solid fa-bell text-primary" style="margin-top: 0.2rem;"></i>
            <div>
                <p style="margin: 0; font-weight: 600; color: #1e293b;">${message}</p>
                <small style="color: #94a3b8;">${nowStr}</small>
            </div>
        </div>
    `;

    feed.prepend(item);
}
