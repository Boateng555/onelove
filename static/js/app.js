/**
 * Track yes/no clicks for live dashboard.
 */
function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

function trackClick(trackUrl, choice) {
    if (!trackUrl) return;

    const body = new URLSearchParams({ choice });
    fetch(trackUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken(),
        },
        body,
        keepalive: true,
    }).catch(() => {});
}

function initAskTracking(trackUrl) {
    const yesBtn = document.getElementById('yes-btn');
    if (yesBtn) {
        yesBtn.addEventListener('click', () => trackClick(trackUrl, 'yes'));
    }
}

/**
 * Runaway "no" button — gentle, sweet movement (not frantic).
 */
function initRunawayButton(buttonId, trackUrl, options = {}) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;

    const url = trackUrl || (typeof window.ASK_TRACK_URL !== 'undefined' ? window.ASK_TRACK_URL : '');
    const messages = options.messages && options.messages.length ? options.messages : ['please...'];
    const bubble = document.getElementById('no-bubble');
    let msgIndex = 0;
    let lastMove = 0;
    let bubbleTimer = null;
    const MOVE_COOLDOWN = 900;

    const showMessage = () => {
        if (!bubble) return;

        bubble.textContent = messages[msgIndex % messages.length];
        bubble.hidden = false;
        bubble.style.opacity = '1';
        bubble.classList.remove('no-bubble-pop');
        void bubble.offsetWidth;
        bubble.classList.add('no-bubble-pop');
        msgIndex += 1;

        const rect = btn.getBoundingClientRect();
        const bubbleRect = bubble.getBoundingClientRect();
        let left = rect.left + rect.width / 2 - bubbleRect.width / 2;
        let top = rect.top - bubbleRect.height - 14;

        left = Math.max(8, Math.min(left, window.innerWidth - bubbleRect.width - 8));
        top = Math.max(8, top);

        bubble.style.left = left + 'px';
        bubble.style.top = top + 'px';

        clearTimeout(bubbleTimer);
        bubbleTimer = setTimeout(() => {
            bubble.style.opacity = '0';
            setTimeout(() => {
                bubble.hidden = true;
                bubble.style.opacity = '1';
            }, 500);
        }, 3200);
    };

    const moveButton = () => {
        const now = Date.now();
        if (now - lastMove < MOVE_COOLDOWN) return;
        lastMove = now;

        trackClick(url, 'no');
        btn.classList.add('runaway');

        const rect = btn.getBoundingClientRect();
        const maxX = window.innerWidth - rect.width - 16;
        const maxY = window.innerHeight - rect.height - 16;

        // Soft dodge — small hop nearby, not wild jumps
        const hopX = (Math.random() - 0.5) * 140;
        const hopY = (Math.random() - 0.5) * 100;
        let x = rect.left + hopX;
        let y = rect.top + hopY;

        x = Math.max(8, Math.min(x, maxX));
        y = Math.max(8, Math.min(y, maxY));

        btn.style.left = x + 'px';
        btn.style.top = y + 'px';

        setTimeout(showMessage, 200);
    };

    btn.addEventListener('mouseenter', moveButton);
    btn.addEventListener('touchstart', (e) => {
        e.preventDefault();
        moveButton();
    }, { passive: false });

    btn.addEventListener('click', (e) => {
        e.preventDefault();
        moveButton();
    });
}

/**
 * Food selection grid — tap to select, enable submit.
 */
function initFoodSelection() {
    const form = document.getElementById('food-form');
    const hiddenInput = document.getElementById('food-choice');
    const submitBtn = document.getElementById('food-submit');
    const options = document.querySelectorAll('.food-option');

    if (!form || !options.length) return;

    options.forEach((option) => {
        option.addEventListener('click', () => {
            options.forEach((o) => {
                o.classList.remove('selected');
                o.setAttribute('aria-pressed', 'false');
            });

            option.classList.add('selected');
            option.setAttribute('aria-pressed', 'true');
            hiddenInput.value = option.dataset.value;
            submitBtn.disabled = false;
        });
    });
}

/**
 * Show video when file loads; hide placeholder hint.
 */
function hideVideoHintIfLoaded() {
    const wrap = document.querySelector('.video-wrap');
    const video = document.querySelector('.final-video');
    if (!wrap || !video) return;

    const source = video.querySelector('source');
    if (!source) return;

    fetch(source.src, { method: 'HEAD' })
        .then((res) => {
            if (res.ok) {
                wrap.classList.add('has-video');
                video.load();
            }
        })
        .catch(() => {});
}

/**
 * Final page — show poster first, then start video when it can actually play.
 */
function initFinalVideo() {
    const video = document.getElementById('final-video');
    const poster = document.getElementById('video-poster');
    if (!video) return;

    let started = false;

    const revealVideo = () => {
        video.classList.add('is-playing');
        if (poster) {
            setTimeout(() => poster.classList.add('is-hidden'), 400);
        }
    };

    const startVideo = () => {
        if (started) return;
        started = true;

        const playPromise = video.play();
        if (playPromise && typeof playPromise.then === 'function') {
            playPromise.then(revealVideo).catch(() => {
                started = false;
                video.classList.remove('is-playing');
            });
        } else {
            revealVideo();
        }
    };

    video.addEventListener('error', () => {
        started = false;
        video.classList.remove('is-playing');
        if (poster) poster.classList.remove('is-hidden');
    });

    video.load();
    setTimeout(startVideo, 3500);
}
