/* ============================================
   CareerPilot AI — Main Application JavaScript
   Navbar, sidebar, notifications, utilities
   ============================================ */

// ── Global App Namespace ────────────────────────
const CareerPilot = {
    apiBase: '',
    
    // ── Initialize App ──────────────────────────
    init() {
        this.initNavbar();
        this.initSidebar();
        this.initAlerts();
        this.initRevealAnimations();
        this.initMobileMenu();
    },

    // ── Navbar Scroll Effect ────────────────────
    initNavbar() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;

        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    },

    // ── Sidebar & Mobile Navigation ──────────────────────────
    initSidebar() {
        const toggle = document.getElementById('sidebarToggle');
        const sidebar = document.querySelector('.sidebar');
        const nav = document.querySelector('.navbar-nav');
        const backdrop = document.getElementById('mobileBackdrop');
        
        const closeAllDrawers = () => {
            if (sidebar) sidebar.classList.remove('active');
            if (nav) nav.classList.remove('active');
            if (backdrop) backdrop.classList.remove('active');
            document.body.style.overflow = '';
        };

        if (toggle) {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                if (sidebar) {
                    const isActive = sidebar.classList.toggle('active');
                    if (backdrop) backdrop.classList.toggle('active', isActive);
                    document.body.style.overflow = isActive ? 'hidden' : '';
                } else if (nav) {
                    const isActive = nav.classList.toggle('active');
                    if (backdrop) backdrop.classList.toggle('active', isActive);
                    document.body.style.overflow = isActive ? 'hidden' : '';
                }
            });
        }

        if (backdrop) {
            backdrop.addEventListener('click', closeAllDrawers);
        }

        // Close when clicking nav links on mobile
        document.querySelectorAll('.sidebar .nav-link, .navbar-nav .nav-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 1024) {
                    closeAllDrawers();
                }
            });
        });

        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeAllDrawers();
            }
        });
    },

    // ── Mobile Menu Stub ─────────────────────────────
    initMobileMenu() {
        // Handled in initSidebar for unified backdrop and drawer management
    },

    // ── Auto-dismiss Alerts ─────────────────────
    initAlerts() {
        document.querySelectorAll('.alert').forEach(alert => {
            // Auto dismiss after 5 seconds
            setTimeout(() => {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                setTimeout(() => alert.remove(), 300);
            }, 5000);

            // Close button
            const closeBtn = alert.querySelector('.alert-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    alert.style.opacity = '0';
                    setTimeout(() => alert.remove(), 300);
                });
            }
        });
    },

    // ── Reveal on Scroll ────────────────────────
    initRevealAnimations() {
        const reveals = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
        if (!reveals.length) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        reveals.forEach(el => observer.observe(el));
    },

    // ── API Helper ──────────────────────────────
    async api(url, options = {}) {
        const defaults = {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        };

        const config = { ...defaults, ...options };
        if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            CareerPilot.showNotification(error.message || 'An error occurred', 'danger');
            throw error;
        }
    },

    // ── Show Notification ───────────────────────
    showNotification(message, type = 'info', duration = 4000) {
        const container = document.getElementById('notifications') || this.createNotificationContainer();
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            <span>${message}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(alert);
        
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => alert.remove(), 300);
        }, duration);
    },

    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notifications';
        container.style.cssText = 'position:fixed;top:80px;right:20px;z-index:3000;display:flex;flex-direction:column;gap:8px;max-width:400px;';
        document.body.appendChild(container);
        return container;
    },

    // ── Loading State ───────────────────────────
    showLoading(message = 'Processing...') {
        let overlay = document.getElementById('loadingOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loadingOverlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="spinner spinner-lg"></div>
                <div class="loading-text">${message}</div>
            `;
            document.body.appendChild(overlay);
        } else {
            overlay.querySelector('.loading-text').textContent = message;
        }
        requestAnimationFrame(() => overlay.classList.add('active'));
    },

    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('active');
            setTimeout(() => overlay.remove(), 300);
        }
    },

    // ── Show AI Processing ──────────────────────
    showAIProcessing(container, message = 'AI is analyzing...') {
        const el = document.createElement('div');
        el.className = 'ai-processing';
        el.id = 'aiProcessing';
        el.innerHTML = `
            <div class="ai-dots">
                <span></span><span></span><span></span>
            </div>
            <span class="ai-text">${message}</span>
        `;
        container.appendChild(el);
        return el;
    },

    hideAIProcessing() {
        const el = document.getElementById('aiProcessing');
        if (el) el.remove();
    },

    // ── Format Number ───────────────────────────
    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    },

    // ── Animate Counter ─────────────────────────
    animateCounter(element, target, duration = 1500) {
        let start = 0;
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            
            const current = Math.round(start + (target - start) * eased);
            element.textContent = current;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    },

    // ── Debounce ────────────────────────────────
    debounce(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    // ── Skeleton Loader ─────────────────────────
    createSkeleton(container, count = 3, type = 'card') {
        container.innerHTML = '';
        for (let i = 0; i < count; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'card';
            skeleton.innerHTML = `
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text short"></div>
                <div class="skeleton skeleton-text"></div>
            `;
            container.appendChild(skeleton);
        }
    }
};

// ── Initialize on DOM Ready ─────────────────────
document.addEventListener('DOMContentLoaded', () => {
    CareerPilot.init();
});
