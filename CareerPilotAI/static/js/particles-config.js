/* ============================================
   CareerPilot AI — Particles.js Configuration
   Animated background for landing page
   ============================================ */

function initParticles() {
    if (typeof particlesJS === 'undefined') return;
    
    particlesJS('particles-js', {
        particles: {
            number: {
                value: 60,
                density: { enable: true, value_area: 1000 }
            },
            color: { value: ['#6C63FF', '#00D4AA', '#3B82F6'] },
            shape: { type: 'circle' },
            opacity: {
                value: 0.3,
                random: true,
                anim: { enable: true, speed: 0.5, opacity_min: 0.1 }
            },
            size: {
                value: 3,
                random: true,
                anim: { enable: true, speed: 2, size_min: 0.5 }
            },
            line_linked: {
                enable: true,
                distance: 150,
                color: '#6C63FF',
                opacity: 0.1,
                width: 1
            },
            move: {
                enable: true,
                speed: 1,
                direction: 'none',
                random: true,
                straight: false,
                out_mode: 'out',
                bounce: false
            }
        },
        interactivity: {
            detect_on: 'canvas',
            events: {
                onhover: { enable: true, mode: 'grab' },
                onclick: { enable: true, mode: 'push' },
                resize: true
            },
            modes: {
                grab: { distance: 140, line_linked: { opacity: 0.3 } },
                push: { particles_nb: 3 }
            }
        },
        retina_detect: true
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('particles-js')) {
        initParticles();
    }
});
