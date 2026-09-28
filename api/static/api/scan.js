(() => {
    // ---------- Auth guard ----------
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login/';
        return;
    }
    document.getElementById('current-user').textContent =
        localStorage.getItem('username') || 'staff';

    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.clear();
        window.location.href = '/login/';
    });

    // ---------- State machine ----------
    const steps = [
        { key: 'tag',    title: 'Scan Cooler Tag',  hint: 'Point the camera at the cooler tag barcode.' },
        { key: 'serial', title: 'Scan Serial Number', hint: 'Point the camera at the serial number barcode.' },
        { key: 'asset',  title: 'Enter Asset Number', hint: 'Asset number is usually typed.', manualOnly: true },
    ];

    let stepIndex = 0;
    const values = { tag: '', serial: '', asset: '' };

    // ---------- DOM ----------
    const stepLabel    = document.getElementById('step-label');
    const scanTitle    = document.getElementById('scan-title');
    const scanHint     = document.getElementById('scan-hint');
    const videoWrap    = document.getElementById('video-wrap');
    const video        = document.getElementById('video');
    const valueInput   = document.getElementById('value-input');
    const nextBtn      = document.getElementById('next-btn');
    const typeToggle   = document.getElementById('type-toggle-btn');
    const scanError    = document.getElementById('scan-error');
    const summaryCard  = document.getElementById('summary-card');
    const scanCard     = document.querySelector('.card');
    const summaryTag    = document.getElementById('summary-tag');
    const summarySerial = document.getElementById('summary-serial');
    const summaryAsset  = document.getElementById('summary-asset');
    const verifyBtn    = document.getElementById('verify-btn');
    const resetBtn     = document.getElementById('reset-btn');
    const resultBanner = document.getElementById('result-banner');

    // ---------- Barcode scanner ----------
    let stream = null;
    let detector = null;
    let scanning = false;

    async function startCamera() {
        if (!('BarcodeDetector' in window)) {
            showScanError('This browser cannot scan barcodes. Use Chrome on Android, or type manually.');
            enterManualMode();
            return;
        }

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: 'environment' } },
                audio: false,
            });
            video.srcObject = stream;
            await video.play();

            detector = new BarcodeDetector({
                formats: ['code_128', 'code_39', 'code_93', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'itf', 'codabar'],
            });
            scanning = true;
            loopScan();
        } catch (err) {
            showScanError('Camera access denied or unavailable. Type manually.');
            enterManualMode();
        }
    }

    async function loopScan() {
        if (!scanning) return;

        try {
            const barcodes = await detector.detect(video);
            if (barcodes.length > 0) {
                const raw = barcodes[0].rawValue;
                if (raw) {
                    valueInput.value = raw;
                    flashSuccess();
                }
            }
        } catch (_) {
            // ignore frame errors
        }

        if (scanning) {
            requestAnimationFrame(loopScan);
        }
    }

    function stopCamera() {
        scanning = false;
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            stream = null;
        }
    }

    function flashSuccess() {
        if (navigator.vibrate) navigator.vibrate(60);
        videoWrap.style.outline = '3px solid #198754';
        setTimeout(() => { videoWrap.style.outline = ''; }, 250);
    }

    function enterManualMode() {
        stopCamera();
        videoWrap.classList.add('d-none');
        valueInput.focus();
    }

    function showScanError(msg) {
        scanError.textContent = msg;
        scanError.classList.remove('d-none');
    }

    // ---------- Step navigation ----------
    function renderStep() {
        const step = steps[stepIndex];
        stepLabel.textContent = `Step ${stepIndex + 1} of ${steps.length}`;
        scanTitle.textContent = step.title;
        scanHint.textContent  = step.hint;
        valueInput.value = '';
        valueInput.type = 'text';
        scanError.classList.add('d-none');

        if (step.manualOnly) {
            stopCamera();
            videoWrap.classList.add('d-none');
            valueInput.focus();
            typeToggle.classList.add('d-none');
        } else {
            videoWrap.classList.remove('d-none');
            typeToggle.classList.remove('d-none');
            typeToggle.textContent = 'Type instead';
            startCamera();
        }
    }

    typeToggle.addEventListener('click', () => {
        if (videoWrap.classList.contains('d-none')) {
            // Switch back to camera
            videoWrap.classList.remove('d-none');
            startCamera();
            typeToggle.textContent = 'Type instead';
        } else {
            enterManualMode();
            typeToggle.textContent = 'Use camera';
        }
    });

    nextBtn.addEventListener('click', () => {
        const value = valueInput.value.trim();
        if (!value) {
            showScanError('Please scan or enter a value before continuing.');
            return;
        }

        values[steps[stepIndex].key] = value;
        stepIndex++;

        if (stepIndex >= steps.length) {
            stopCamera();
            showSummary();
        } else {
            renderStep();
        }
    });

    // ---------- Summary + verify ----------
    function showSummary() {
        scanCard.classList.add('d-none');
        summaryCard.classList.remove('d-none');
        summaryTag.textContent    = values.tag    || '—';
        summarySerial.textContent = values.serial || '—';
        summaryAsset.textContent  = values.asset  || '—';
    }

    resetBtn.addEventListener('click', () => {
        stepIndex = 0;
        values.tag = values.serial = values.asset = '';
        summaryCard.classList.add('d-none');
        scanCard.classList.remove('d-none');
        resultBanner.classList.add('d-none');
        renderStep();
    });

    verifyBtn.addEventListener('click', async () => {
        verifyBtn.disabled = true;
        verifyBtn.textContent = 'Verifying…';
        resultBanner.classList.add('d-none');

        const payload = {
            tag:       values.tag,
            serial:    values.serial,
            asset:     values.asset,
            staff_id:  localStorage.getItem('username') || 'staff',
            site_name: '',
        };

        // GPS capture (best-effort)
        try {
            const pos = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
            });
            payload.gps_lat = pos.coords.latitude;
            payload.gps_lng = pos.coords.longitude;
        } catch (_) {
            // ignore — GPS optional
        }

        try {
            const res = await fetch('/api/scan/verify/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                },
                body: JSON.stringify(payload),
            });

            if (res.status === 401) {
                localStorage.clear();
                window.location.href = '/login/';
                return;
            }

            const data = await res.json();
            showResult(data);
        } catch (err) {
            resultBanner.className = 'alert alert-danger';
            resultBanner.textContent = 'Network error. Please try again.';
            resultBanner.classList.remove('d-none');
        } finally {
            verifyBtn.disabled = false;
            verifyBtn.textContent = 'Verify';
        }
    });

    function showResult(data) {
        const cls = `alert alert-result-${data.result.toLowerCase()}`;
        resultBanner.className = cls;
        resultBanner.innerHTML = `
            <div class="fw-bold mb-1">${data.result}</div>
            <div>${data.message}</div>
        `;
        resultBanner.classList.remove('d-none');

        if (navigator.vibrate) {
            if (data.result === 'VERIFIED') navigator.vibrate(120);
            else if (data.result === 'MISMATCH') navigator.vibrate([80, 60, 80]);
        }

        // Scroll to result
        resultBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // ---------- Boot ----------
    renderStep();
})();