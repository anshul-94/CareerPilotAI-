/**
 * CareerPilot AI — Career DNA Profile Page JavaScript
 * Handles: resync from resume, completeness update, toast notifications.
 */
'use strict';

// ─── Resync Resume ─────────────────────────────────────────
async function resyncResume() {
    const btn = document.getElementById('resyncBtn');
    if (!btn) return;

    btn.classList.add('spinning');
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Syncing...`;

    try {
        const resp = await fetch('/profile/api/resync-resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await resp.json();

        if (data.success) {
            showToast('✅ Profile synced from resume! Refreshing...', 'success');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showToast('❌ ' + (data.error || 'Sync failed. Upload a resume first.'), 'error');
        }
    } catch (err) {
        showToast('❌ Network error. Please try again.', 'error');
    } finally {
        btn.classList.remove('spinning');
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Re-sync from Resume`;
    }
}

// ─── Toast Notification ────────────────────────────────────
function showToast(msg, type) {
    const el = document.getElementById('profileToast');
    if (!el) return;

    el.textContent = msg;
    el.style.display = 'block';
    el.style.background = type === 'success'
        ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)';
    el.style.border = type === 'success'
        ? '1px solid rgba(34,197,94,0.4)' : '1px solid rgba(239,68,68,0.4)';
    el.style.color = type === 'success' ? '#86efac' : '#fca5a5';
    el.style.backdropFilter = 'blur(12px)';
    el.style.maxWidth = '360px';

    setTimeout(() => { el.style.display = 'none'; }, 4000);
}

// ─── Auto-detect manual field changes ─────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('profileForm');
    if (!form) return;

    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            const label = input.previousElementSibling;
            if (!label) return;
            // Remove AI tag, add MANUAL indication
            const aiTag = label.querySelector('.source-tag.resume');
            if (aiTag && input.value.trim()) {
                aiTag.className = 'source-tag manual';
                aiTag.textContent = 'MANUAL';
            }
        });
    });
});
