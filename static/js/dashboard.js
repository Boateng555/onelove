/**
 * Poll live yes/no activity and her choices for the admin dashboard.
 */
function initLiveActivity(apiUrl, personId) {
    const feed = document.getElementById('live-feed');
    const updatedEl = document.getElementById('live-updated');
    const liveDot = document.getElementById('live-dot');
    const choicesBody = document.getElementById('choices-body');
    const responsesBody = document.getElementById('responses-body');

    if (!apiUrl) return;

    let sinceClickId = 0;
    let lastProposalCheck = new Date(Date.now() - 60000).toISOString();
    const knownFeedKeys = new Set();

    function resetLiveDisplay() {
        updateStats({
            yes_today: 0,
            no_today: 0,
            yes_total: 0,
            no_total: 0,
            scheduled_total: 0,
        });
        if (feed) {
            feed.innerHTML = '<li class="dash-live-empty">Waiting for activity...</li>';
        }
        knownFeedKeys.clear();
        sinceClickId = 0;
        lastProposalCheck = new Date().toISOString();
        [choicesBody, responsesBody].forEach((tbody) => {
            if (!tbody) return;
            const cols = tbody.id === 'responses-body' ? 6 : 5;
            tbody.innerHTML = `<tr><td colspan="${cols}" class="dash-empty">Waiting for choices...</td></tr>`;
        });
    }

    if (new URLSearchParams(window.location.search).get('cleared') === '1') {
        resetLiveDisplay();
        const cleanUrl = new URL(window.location);
        cleanUrl.searchParams.delete('cleared');
        window.history.replaceState({}, '', cleanUrl);
    }

    function timeAgo(iso) {
        const diff = Date.now() - new Date(iso).getTime();
        const secs = Math.floor(diff / 1000);
        if (secs < 5) return 'just now';
        if (secs < 60) return `${secs}s ago`;
        const mins = Math.floor(secs / 60);
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        return `${hrs}h ago`;
    }

    function updateStats(stats) {
        const map = {
            'stat-yes-today': stats.yes_today,
            'stat-no-today': stats.no_today,
            'stat-yes-total': stats.yes_total,
            'stat-no-total': stats.no_total,
            'stat-scheduled-total': stats.scheduled_total,
        };
        Object.entries(map).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        });
    }

    function badgeClass(proposal) {
        if (proposal.completed) return 'dash-badge-done';
        if (proposal.food_choice && proposal.food_choice !== '—') return 'dash-badge-food';
        return 'dash-badge-yes';
    }

    function renderProposalRow(proposal, isNew, fullRow) {
        const tr = document.createElement('tr');
        if (proposal.completed) tr.className = 'dash-row-done';
        if (isNew) tr.classList.add('dash-row-new');
        tr.dataset.proposalId = proposal.id;

        if (fullRow) {
            tr.innerHTML = `
                <td><span class="dash-badge ${badgeClass(proposal)}">${proposal.status}</span></td>
                <td>${proposal.food_choice}</td>
                <td>${proposal.date}</td>
                <td>${proposal.time_slot}</td>
                <td>${proposal.said_yes_at}</td>
                <td>${proposal.updated_full}</td>
            `;
        } else {
            tr.innerHTML = `
                <td><span class="dash-badge ${badgeClass(proposal)}">${proposal.status}</span></td>
                <td>${proposal.food_choice}</td>
                <td>${proposal.date}</td>
                <td>${proposal.time_slot}</td>
                <td>${proposal.updated}</td>
            `;
        }
        return tr;
    }

    function refreshChoicesTable(proposals, newProposals) {
        [choicesBody, responsesBody].forEach((tbody) => {
            if (!tbody) return;
            const fullRow = tbody.id === 'responses-body';

            if (!proposals.length) {
                const cols = fullRow ? 6 : 5;
                tbody.innerHTML = `<tr><td colspan="${cols}" class="dash-empty">Waiting for choices...</td></tr>`;
                return;
            }

            if (tbody.querySelector('.dash-empty')) {
                tbody.innerHTML = '';
            }

            const newIds = new Set(newProposals.map(p => String(p.id)));

            proposals.forEach((proposal) => {
                let row = tbody.querySelector(`tr[data-proposal-id="${proposal.id}"]`);
                const isNew = newIds.has(String(proposal.id));
                if (row) {
                    row.replaceWith(renderProposalRow(proposal, isNew, fullRow));
                } else {
                    tbody.prepend(renderProposalRow(proposal, isNew, fullRow));
                }
            });

            const liveIds = new Set(proposals.map(p => String(p.id)));
            tbody.querySelectorAll('tr[data-proposal-id]').forEach((row) => {
                if (!liveIds.has(row.dataset.proposalId)) {
                    row.remove();
                }
            });
        });
    }

    function renderClickEvent(event, isNew) {
        const li = document.createElement('li');
        li.className = 'dash-live-item' + (event.choice === 'yes' ? ' dash-live-yes' : ' dash-live-no');
        if (isNew) li.classList.add('dash-live-item-new');
        li.dataset.feedKey = 'click-' + event.id;
        li.innerHTML = `
            <span class="dash-live-item-badge">${event.label}</span>
            <span class="dash-live-item-time">${event.time}</span>
            <span class="dash-live-item-ago">${timeAgo(event.iso)}</span>
        `;
        return li;
    }

    function renderProposalEvent(proposal, isNew) {
        const li = document.createElement('li');
        li.className = 'dash-live-item dash-live-choice';
        if (proposal.completed) li.classList.add('dash-live-scheduled');
        if (isNew) li.classList.add('dash-live-item-new');
        li.dataset.feedKey = 'proposal-' + proposal.id + '-' + proposal.iso;
        li.innerHTML = `
            <span class="dash-live-item-badge">${proposal.label}</span>
            <span class="dash-live-item-time">${proposal.updated}</span>
            <span class="dash-live-item-ago">${timeAgo(proposal.iso)}</span>
        `;
        return li;
    }

    function refreshFeed(clicks, newClicks, newProposals) {
        if (!feed) return;

        const hasActivity = clicks.length || newProposals.length;
        if (!hasActivity && !feed.children.length) {
            feed.innerHTML = '<li class="dash-live-empty">Waiting for activity...</li>';
            return;
        }

        if (feed.querySelector('.dash-live-empty')) {
            feed.innerHTML = '';
        }

        newProposals.forEach((proposal) => {
            const key = 'proposal-' + proposal.id + '-' + proposal.iso;
            if (knownFeedKeys.has(key)) return;
            knownFeedKeys.add(key);
            feed.prepend(renderProposalEvent(proposal, true));
        });

        newClicks.forEach((event) => {
            const key = 'click-' + event.id;
            if (knownFeedKeys.has(key)) return;
            knownFeedKeys.add(key);
            feed.prepend(renderClickEvent(event, true));
        });

        while (feed.children.length > 60) {
            feed.removeChild(feed.lastChild);
        }
    }

    async function poll() {
        try {
            const personSelect = document.getElementById('person-select');
            const filterId = personId || (personSelect ? personSelect.value : '');
            let url = `${apiUrl}?since=${sinceClickId}&since_proposal_time=${encodeURIComponent(lastProposalCheck)}`;
            if (filterId) url += `&person=${encodeURIComponent(filterId)}`;
            const res = await fetch(url, { credentials: 'same-origin' });
            if (!res.ok) throw new Error('fetch failed');

            const data = await res.json();
            updateStats(data.stats);
            refreshFeed(data.events, data.new_events, data.new_proposals || []);
            refreshChoicesTable(data.proposals || [], data.new_proposals || []);

            if (data.latest_id > sinceClickId) sinceClickId = data.latest_id;
            lastProposalCheck = new Date().toISOString();

            if (liveDot) liveDot.classList.remove('dash-live-dot-error');
            if (updatedEl) {
                updatedEl.textContent = 'Updated ' + new Date().toLocaleTimeString([], {
                    hour: 'numeric',
                    minute: '2-digit',
                    second: '2-digit',
                });
            }
        } catch {
            if (liveDot) liveDot.classList.add('dash-live-dot-error');
            if (updatedEl) updatedEl.textContent = 'Reconnecting...';
        }
    }

    poll();
    setInterval(poll, 2000);
}

/**
 * Live preview on Ask page tab — updates as you type messages.
 */
function initAskPreview(personName) {
    const titleInput = document.getElementById('field-ask-title');
    const messagesInput = document.getElementById('field-runaway-messages');
    const yesInput = document.querySelector('[name="ask_yes_button"]');
    const noInput = document.querySelector('[name="ask_no_button"]');

    const previewTitle = document.getElementById('preview-title');
    const previewYes = document.getElementById('preview-yes');
    const previewNo = document.getElementById('preview-no');
    const previewList = document.getElementById('preview-messages');

    if (!titleInput || !previewTitle) return;

    const displayName = personName || 'Name';

    function formatLine(line) {
        return line.replace(/\{name\}/g, displayName);
    }

    function updatePreview() {
        const title = titleInput ? titleInput.value : '';
        previewTitle.textContent = title.replace(/\{name\}/g, displayName).replace(/\s{2,}/g, ' ').trim();
        if (previewYes && yesInput) previewYes.textContent = yesInput.value;
        if (previewNo && noInput) previewNo.textContent = noInput.value;

        if (previewList && messagesInput) {
            const lines = messagesInput.value.split('\n').map(l => l.trim()).filter(Boolean);
            previewList.innerHTML = lines.length
                ? lines.map(l => `<li>${formatLine(l)}</li>`).join('')
                : `<li>please ${displayName}...</li>`;
        }
    }

    [titleInput, messagesInput, yesInput, noInput].forEach(el => {
        if (el) el.addEventListener('input', updatePreview);
    });
    updatePreview();
}

function initCopyInviteLinks() {
    document.querySelectorAll('.dash-copy-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const input = document.getElementById(btn.dataset.copy);
            if (!input) return;
            input.select();
            input.setSelectionRange(0, 99999);
            try {
                await navigator.clipboard.writeText(input.value);
                btn.textContent = 'Copied ✓';
                setTimeout(() => { btn.textContent = 'Copy link'; }, 2000);
            } catch {
                document.execCommand('copy');
                btn.textContent = 'Copied ✓';
                setTimeout(() => { btn.textContent = 'Copy link'; }, 2000);
            }
        });
    });
}

/**
 * Compress gift-loop videos in the browser so they stay tiny on Vercel.
 */
function initGiftVideoCompress(maxMb) {
    const maxBytes = Math.max(1, maxMb) * 1024 * 1024;
    const targetBytes = Math.floor(maxBytes * 0.75);

    document.querySelectorAll('input[data-gift-video], input[data-gift-media]').forEach((input) => {
        input.addEventListener('change', async () => {
            const file = input.files && input.files[0];
            if (!file) return;

            const wrap = input.closest('.dash-file-wrap');
            const status = wrap && wrap.querySelector('.dash-gift-compress-status');

            if (!file.type.startsWith('video/')) {
                if (status) {
                    status.hidden = false;
                    status.textContent = file.type.includes('gif') ? 'Live GIF ready ✓' : 'Photo ready ✓';
                }
                return;
            }

            if (file.size <= targetBytes) return;

            if (!window.MediaRecorder || !HTMLCanvasElement.prototype.captureStream) {
                if (file.size > maxBytes) {
                    alert(`Gift video is ${(file.size / (1024 * 1024)).toFixed(1)}MB. Trim to a short clip under ${maxMb}MB.`);
                    input.value = '';
                }
                return;
            }

            if (status) {
                status.hidden = false;
                status.textContent = 'Compressing gift video…';
            }

            try {
                const compressed = await compressGiftVideoFile(file, { maxBytes: targetBytes });
                const dt = new DataTransfer();
                dt.items.add(compressed);
                input.files = dt.files;

                if (status) {
                    const kb = Math.round(compressed.size / 1024);
                    status.textContent = `Compressed to ${kb}KB ✓`;
                    status.hidden = false;
                }

                if (compressed.size > maxBytes) {
                    alert(`Still too large after compress (${(compressed.size / (1024 * 1024)).toFixed(1)}MB). Trim to 3–5 seconds.`);
                    input.value = '';
                    if (status) status.hidden = true;
                }
            } catch {
                if (file.size > maxBytes) {
                    alert(`Could not compress. Trim the clip under ${maxMb}MB.`);
                    input.value = '';
                }
                if (status) status.hidden = true;
            }
        });
    });
}

function compressGiftVideoFile(file, options = {}) {
    const maxBytes = options.maxBytes || 1.5 * 1024 * 1024;
    const maxSide = options.maxSide || 280;
    const maxDuration = options.maxDuration || 8;
    const bitrate = options.bitrate || 120000;

    if (file.size <= maxBytes) {
        return Promise.resolve(file);
    }

    return new Promise((resolve) => {
        const video = document.createElement('video');
        video.muted = true;
        video.playsInline = true;
        video.preload = 'auto';
        const objectUrl = URL.createObjectURL(file);

        const finish = (result) => {
            URL.revokeObjectURL(objectUrl);
            resolve(result);
        };

        video.onloadedmetadata = () => {
            const duration = Math.min(video.duration || maxDuration, maxDuration);
            const scale = Math.min(1, maxSide / Math.max(video.videoWidth, video.videoHeight, 1));
            const w = Math.max(2, Math.round((video.videoWidth * scale) / 2) * 2);
            const h = Math.max(2, Math.round((video.videoHeight * scale) / 2) * 2);

            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');

            const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
                ? 'video/webm;codecs=vp8'
                : 'video/webm';

            if (!MediaRecorder.isTypeSupported(mimeType)) {
                finish(file);
                return;
            }

            const stream = canvas.captureStream(20);
            const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: bitrate });
            const chunks = [];

            recorder.ondataavailable = (event) => {
                if (event.data && event.data.size) chunks.push(event.data);
            };
            recorder.onstop = () => {
                const blob = new Blob(chunks, { type: 'video/webm' });
                const out = new File([blob], 'gift-loop.webm', { type: 'video/webm' });
                finish(out.size < file.size ? out : file);
            };
            recorder.onerror = () => finish(file);

            video.src = objectUrl;
            video.play().then(() => {
                recorder.start(120);
                const start = performance.now();

                const tick = () => {
                    const elapsed = (performance.now() - start) / 1000;
                    if (video.ended || video.currentTime >= duration || elapsed >= duration) {
                        video.pause();
                        if (recorder.state !== 'inactive') recorder.stop();
                        return;
                    }
                    ctx.drawImage(video, 0, 0, w, h);
                    requestAnimationFrame(tick);
                };
                tick();
            }).catch(() => finish(file));
        };

        video.onerror = () => finish(file);
        video.src = objectUrl;
    });
}

/**
 * Block oversized phone videos before upload — Vercel rejects large files silently.
 */
function initVideoUploadLimit(maxMb) {
    const limitBytes = Math.max(1, maxMb) * 1024 * 1024;
    const safeBytes = Math.floor(limitBytes * 0.9);

    document.querySelectorAll('input[type="file"][accept*="video"]').forEach((input) => {
        input.addEventListener('change', () => {
            const file = input.files && input.files[0];
            if (!file || !file.type.startsWith('video/')) return;
            if (file.size > safeBytes) {
                const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
                alert(
                    `That video is ${sizeMb}MB — too big (max ${maxMb}MB on Vercel).\n\n` +
                    'Trim it shorter on your phone, or paste a direct MP4 link in the "Or video link" field instead.'
                );
                input.value = '';
            }
        });
    });

    document.querySelectorAll('form.dash-form').forEach((form) => {
        form.addEventListener('submit', (event) => {
            const videoInput = form.querySelector('input[type="file"][accept*="video"]');
            const file = videoInput && videoInput.files && videoInput.files[0];
            if (file && file.type.startsWith('video/') && file.size > safeBytes) {
                event.preventDefault();
                alert(`Video is too large. Max ${maxMb}MB — trim it or use a video link instead.`);
            }
        });
    });
}
