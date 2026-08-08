// =============================================================
// video_analysis.js  —  Video-Based Crop Disease Analysis Module
// Self-contained. Does NOT modify script.js or existing image flow.
// =============================================================

(function () {
    "use strict";

    // ----------------------------------------------------------
    // Constants
    // ----------------------------------------------------------
    const VIDEO_MIN_DURATION = 5;   // seconds
    const VIDEO_MAX_DURATION = 15;  // seconds
    const VIDEO_MAX_SIZE_MB  = 200; // MB
    const VIDEO_MAX_FRAMES   = 8;   // frames sent to AI
    const FRAME_MIN_BRIGHTNESS = 20; // 0-255 — skip near-black frames
    const FRAME_JPEG_QUALITY   = 0.80;
    const FRAME_MAX_DIMENSION  = 768; // resize long edge to this before AI

    // ----------------------------------------------------------
    // DOM references (created in detect.html video panel)
    // ----------------------------------------------------------
    const videoRecordInput   = document.getElementById("videoRecordInput");
    const videoGalleryInput  = document.getElementById("videoGalleryInput");
    const videoPreviewEl     = document.getElementById("videoPreview");
    const videoPreviewWrap   = document.getElementById("videoPreviewWrapper");
    const videoRemoveBtn     = document.getElementById("videoRemoveBtn");
    const videoRecordBtn     = document.getElementById("videoRecordBtn");
    const videoSelectBtn     = document.getElementById("videoSelectBtn");
    const videoAnalyzeBtn    = document.getElementById("videoAnalyzeBtn");
    const videoErrorBox      = document.getElementById("videoErrorBox");
    const videoErrorMsg      = document.getElementById("videoErrorMsg");
    const videoLoadingSection = document.getElementById("videoLoading");
    const videoResultSection  = document.getElementById("videoResultSection");
    const videoStepText       = document.getElementById("videoStepText");
    const videoStepList       = document.getElementById("videoStepList");

    // ----------------------------------------------------------
    // State
    // ----------------------------------------------------------
    let selectedVideoFile = null;
    let isVideoAnalyzing  = false;

    // ----------------------------------------------------------
    // Utility helpers
    // ----------------------------------------------------------
    function showVideoError(msg) {
        if (!videoErrorBox || !videoErrorMsg) { alert(msg); return; }
        videoErrorMsg.textContent = msg;
        videoErrorBox.classList.remove("hidden");
        videoErrorBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function hideVideoError() {
        if (videoErrorBox) videoErrorBox.classList.add("hidden");
    }

    function setVideoStep(text) {
        if (videoStepText) videoStepText.textContent = text;
    }

    function markStepDone(text) {
        if (!videoStepList) return;
        const li = document.createElement("li");
        li.className = "flex items-center gap-2 text-green-700 text-sm font-medium";
        li.innerHTML = `<span class="text-green-500 text-base">✔</span><span>${text}</span>`;
        videoStepList.appendChild(li);
    }

    function markStepActive(text) {
        if (!videoStepList) return;
        // Remove any existing "active" item
        const prev = videoStepList.querySelector(".va-step-active");
        if (prev) prev.remove();
        const li = document.createElement("li");
        li.className = "va-step-active flex items-center gap-2 text-blue-700 text-sm font-semibold animate-pulse";
        li.innerHTML = `<span class="inline-block w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></span><span>${text}</span>`;
        videoStepList.appendChild(li);
        if (videoStepText) videoStepText.textContent = text;
    }

    function clearStepList() {
        if (videoStepList) videoStepList.innerHTML = "";
    }

    // ----------------------------------------------------------
    // Video selection & preview
    // ----------------------------------------------------------
    function handleVideoFile(file) {
        if (!file) return;

        hideVideoError();

        // Basic type check
        const ext = file.name.split(".").pop().toLowerCase();
        const allowedTypes = ["mp4", "webm", "mov", "avi", "mkv"];
        if (!file.type.startsWith("video/") && !allowedTypes.includes(ext)) {
            showVideoError("Unsupported file format. Please upload an MP4, WebM, MOV, or AVI video.");
            return;
        }

        // File size check
        const sizeMB = file.size / (1024 * 1024);
        if (sizeMB > VIDEO_MAX_SIZE_MB) {
            showVideoError(`Video file is too large (${sizeMB.toFixed(1)} MB). Maximum allowed size is ${VIDEO_MAX_SIZE_MB} MB.`);
            return;
        }

        selectedVideoFile = file;

        // Show preview
        const url = URL.createObjectURL(file);
        if (videoPreviewEl) {
            videoPreviewEl.src = url;
            videoPreviewEl.load();
        }
        if (videoPreviewWrap) videoPreviewWrap.classList.remove("hidden");
        if (videoAnalyzeBtn) videoAnalyzeBtn.classList.remove("hidden");
        if (videoRemoveBtn) videoRemoveBtn.classList.remove("hidden");

        // Hide the pick buttons once a file is chosen
        const pickArea = document.getElementById("videoPickers");
        if (pickArea) pickArea.classList.add("hidden");
    }

    function removeVideoSelection() {
        selectedVideoFile = null;
        if (videoPreviewEl) { videoPreviewEl.src = ""; }
        if (videoPreviewWrap) videoPreviewWrap.classList.add("hidden");
        if (videoAnalyzeBtn) videoAnalyzeBtn.classList.add("hidden");
        if (videoRemoveBtn) videoRemoveBtn.classList.remove("hidden");
        const pickArea = document.getElementById("videoPickers");
        if (pickArea) pickArea.classList.remove("hidden");
        if (videoRemoveBtn) videoRemoveBtn.classList.add("hidden");
        hideVideoError();
        if (videoResultSection) videoResultSection.classList.add("hidden");
        if (videoLoadingSection) videoLoadingSection.classList.add("hidden");
    }

    // ----------------------------------------------------------
    // Video validation (duration + resolution)
    // ----------------------------------------------------------
    async function validateVideo(videoEl) {
        return new Promise((resolve, reject) => {
            videoEl.addEventListener("loadedmetadata", function onMeta() {
                videoEl.removeEventListener("loadedmetadata", onMeta);
                const duration = videoEl.duration;
                const width    = videoEl.videoWidth;
                const height   = videoEl.videoHeight;

                if (duration < VIDEO_MIN_DURATION) {
                    reject(`Video is too short (${duration.toFixed(1)}s). Please record a video of at least ${VIDEO_MIN_DURATION} seconds.`);
                    return;
                }
                if (duration > VIDEO_MAX_DURATION) {
                    reject(`Video is too long (${duration.toFixed(1)}s). Please record a video under ${VIDEO_MAX_DURATION} seconds.`);
                    return;
                }
                if (width < 240 || height < 240) {
                    reject(`Video quality is too low (${width}×${height}). Please record a clearer video of the affected crop.`);
                    return;
                }
                resolve({ duration, width, height });
            });
            videoEl.addEventListener("error", function onErr() {
                videoEl.removeEventListener("error", onErr);
                reject("Failed to load video for validation. Please try a different file or format.");
            });
        });
    }

    // ----------------------------------------------------------
    // Frame extraction (client-side via Canvas)
    // ----------------------------------------------------------
    async function extractFrames(videoEl, duration, count) {
        const canvas = document.createElement("canvas");
        const ctx    = canvas.getContext("2d");
        const frames = [];

        // Evenly spaced timestamps (avoid first/last 0.3s for edge artifacts)
        const margin = Math.min(0.3, duration * 0.05);
        const usableDuration = duration - 2 * margin;
        const interval = usableDuration / (count + 1);

        for (let i = 1; i <= count; i++) {
            const time = margin + i * interval;
            const blob = await captureFrameAtTime(videoEl, canvas, ctx, time);
            if (blob) frames.push({ blob, time });
        }

        return frames;
    }

    function captureFrameAtTime(videoEl, canvas, ctx, time) {
        return new Promise((resolve) => {
            const onSeeked = () => {
                videoEl.removeEventListener("seeked", onSeeked);

                const origW = videoEl.videoWidth;
                const origH = videoEl.videoHeight;
                const scale = Math.min(1, FRAME_MAX_DIMENSION / Math.max(origW, origH));
                canvas.width  = Math.round(origW * scale);
                canvas.height = Math.round(origH * scale);

                ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

                // Quality filter: skip near-black/blank frames
                if (!isFrameUsable(ctx, canvas.width, canvas.height)) {
                    resolve(null);
                    return;
                }

                canvas.toBlob(resolve, "image/jpeg", FRAME_JPEG_QUALITY);
            };

            videoEl.addEventListener("seeked", onSeeked);
            videoEl.currentTime = time;
        });
    }

    function isFrameUsable(ctx, w, h) {
        try {
            const data = ctx.getImageData(0, 0, w, h).data;
            let total = 0;
            const step = 4 * 100; // sample every 100th pixel
            let count  = 0;
            for (let i = 0; i < data.length; i += step) {
                total += (data[i] + data[i + 1] + data[i + 2]) / 3;
                count++;
            }
            const avgBrightness = count > 0 ? total / count : 0;
            return avgBrightness >= FRAME_MIN_BRIGHTNESS;
        } catch (e) {
            return true; // if we can't read pixels, assume usable
        }
    }

    // ----------------------------------------------------------
    // Main analysis flow
    // ----------------------------------------------------------
    async function analyzeVideo() {
        if (isVideoAnalyzing) return;
        if (!selectedVideoFile) {
            showVideoError("Please select or record a video first.");
            return;
        }

        hideVideoError();
        isVideoAnalyzing = true;

        // Cancel any active TTS from image analysis
        if (window.speechSynthesis) window.speechSynthesis.cancel();

        // Show loading, hide any previous result
        if (videoResultSection) videoResultSection.classList.add("hidden");
        if (videoLoadingSection) videoLoadingSection.classList.remove("hidden");
        clearStepList();

        const uploadSection = document.getElementById("videoAnalysisPanel");
        if (uploadSection) uploadSection.classList.add("hidden");

        // Scroll to loading
        if (videoLoadingSection) videoLoadingSection.scrollIntoView({ behavior: "smooth" });

        // Also hide the main image result section if visible
        const imgResult = document.getElementById("resultSection");
        if (imgResult) imgResult.classList.add("hidden");

        try {
            // ------ Step 1: Validate ------
            markStepActive("Uploading Video...");
            await sleep(400);
            markStepDone("Uploading Video...");

            // Create a temporary video element for processing
            const tempVideo = document.createElement("video");
            tempVideo.muted = true;
            tempVideo.preload = "metadata";
            const objUrl = URL.createObjectURL(selectedVideoFile);
            tempVideo.src = objUrl;

            markStepActive("Preparing Video...");
            let videoMeta;
            try {
                videoMeta = await validateVideo(tempVideo);
            } catch (valErr) {
                showVideoError(valErr);
                return;
            }
            markStepDone(`Preparing Video... (${videoMeta.duration.toFixed(1)}s, ${videoMeta.width}×${videoMeta.height})`);

            // ------ Step 2: Extract frames ------
            markStepActive("Extracting Frames...");
            const rawFrames = await extractFrames(tempVideo, videoMeta.duration, VIDEO_MAX_FRAMES);
            URL.revokeObjectURL(objUrl);

            if (rawFrames.length === 0) {
                showVideoError("No usable frames could be extracted from the video. Please record a clearer, steadier video in good lighting.");
                return;
            }
            markStepDone(`Extracting Frames... (${rawFrames.length} frames captured)`);

            // ------ Step 3: Select useful frames ------
            markStepActive("Selecting Useful Frames...");
            await sleep(300);
            markStepDone(`Selecting Useful Frames... (${rawFrames.length} selected)`);

            // ------ Step 4: Build FormData ------
            markStepActive("Analyzing Crop Symptoms...");
            const preference = document.querySelector('input[name="treatment_preference"]:checked')?.value || "organic";
            const formData = new FormData();
            formData.append("treatment_preference", preference);

            rawFrames.forEach((frame, idx) => {
                formData.append(`frame_${idx}`, frame.blob, `frame_${idx}.jpg`);
            });

            // ------ Step 5: Send to server ------
            markStepActive("Comparing Observations...");
            const response = await fetch("/predict-video", {
                method: "POST",
                body: formData
            });

            markStepDone("Comparing Observations...");
            markStepActive("Preparing Disease Report...");

            const data = await response.json();

            if (!data.success) {
                showVideoError(data.message || "Analysis failed. Please try again.");
                return;
            }

            markStepDone("Preparing Disease Report...");
            await sleep(200);

            // ------ Step 6: Render result ------
            renderVideoResult(data, rawFrames);

        } catch (err) {
            console.error("Video analysis error:", err);
            if (err && err.message && err.message.toLowerCase().includes("failed to fetch")) {
                showVideoError("Network error — could not reach the server. Please check your connection and try again.");
            } else {
                showVideoError("An unexpected error occurred during video analysis. Please try again.");
            }
        } finally {
            isVideoAnalyzing = false;
            if (videoLoadingSection) videoLoadingSection.classList.add("hidden");
            if (uploadSection) uploadSection.classList.remove("hidden");
        }
    }

    // ----------------------------------------------------------
    // Render video result
    // ----------------------------------------------------------
    function renderVideoResult(data, rawFrames) {
        const result      = data.result;
        const treatment   = data.treatment_guidance;
        const frameCount  = data.frames_analyzed || rawFrames.length;
        const thumbsB64   = data.frame_thumbnails || [];

        if (!videoResultSection) return;
        videoResultSection.classList.remove("hidden");

        // Populate summary fields
        setEl("vr-crop",       result.crop_name || "Unknown");
        setEl("vr-disease",    result.disease_name || "Unknown");
        setEl("vr-confidence", result.confidence || "N/A");
        setEl("vr-severity",   result.severity || "N/A");
        setEl("vr-frames",     frameCount);
        setEl("vr-notes",      result.additional_notes || "");

        // Severity badge colour
        const sevBadge = document.getElementById("vr-severity-badge");
        if (sevBadge) {
            sevBadge.textContent = result.severity || "N/A";
            const sev = (result.severity || "").toLowerCase();
            sevBadge.className = "px-3 py-1 rounded-full text-xs font-bold " + (
                sev === "severe"   ? "bg-red-100 text-red-700 border border-red-200" :
                sev === "moderate" ? "bg-orange-100 text-orange-700 border border-orange-200" :
                sev === "mild"     ? "bg-yellow-100 text-yellow-700 border border-yellow-200" :
                sev === "healthy"  ? "bg-green-100 text-green-700 border border-green-200" :
                                     "bg-gray-100 text-gray-600 border border-gray-200"
            );
        }

        // Confidence badge
        const confBadge = document.getElementById("vr-confidence-badge");
        if (confBadge) {
            confBadge.textContent = result.confidence || "N/A";
            const conf = (result.confidence || "").toLowerCase();
            confBadge.className = "px-3 py-1 rounded-full text-xs font-bold " + (
                conf === "high"   ? "bg-green-100 text-green-700 border border-green-200" :
                conf === "medium" ? "bg-yellow-100 text-yellow-700 border border-yellow-200" :
                                    "bg-red-100 text-red-600 border border-red-200"
            );
        }

        // Observed symptoms list
        populateVideoList("vr-symptoms", result.symptoms);

        // Frame evidence gallery
        renderFrameGallery(rawFrames, thumbsB64);

        // Re-use existing treatment guidance rendering from script.js
        // We do this by calling the global displayResult function which already
        // handles the treatmentGuidanceSection in detect.html
        if (typeof displayResult === "function") {
            // Store result so voice/PDF also work
            displayResult(result, treatment);
            // After displayResult, scroll to the video result instead
            videoResultSection.scrollIntoView({ behavior: "smooth" });
        } else {
            // Fallback: show basic treatment info inline
            renderTreatmentFallback(treatment);
        }

        videoResultSection.scrollIntoView({ behavior: "smooth" });
    }

    function setEl(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function populateVideoList(id, arr) {
        const ul = document.getElementById(id);
        if (!ul) return;
        ul.innerHTML = "";
        if (!arr || arr.length === 0) {
            ul.innerHTML = "<li class='text-gray-500 italic'>No symptoms detected.</li>";
            return;
        }
        arr.forEach(item => {
            const li = document.createElement("li");
            li.className = "flex items-start gap-2 text-sm text-gray-700";
            li.innerHTML = `<span class="text-red-400 mt-0.5 shrink-0">•</span><span>${item}</span>`;
            ul.appendChild(li);
        });
    }

    // ----------------------------------------------------------
    // Frame gallery
    // ----------------------------------------------------------
    function renderFrameGallery(rawFrames, thumbsB64) {
        const gallery = document.getElementById("videoFrameGallery");
        if (!gallery) return;
        gallery.innerHTML = "";

        // Prefer server-returned thumbnails (already compressed); fall back to local blobs
        const sources = thumbsB64.length > 0
            ? thumbsB64.map(b64 => `data:image/jpeg;base64,${b64}`)
            : rawFrames.map(f => URL.createObjectURL(f.blob));

        sources.forEach((src, idx) => {
            const wrap = document.createElement("div");
            wrap.className = "relative shrink-0 cursor-pointer rounded-xl overflow-hidden border-2 border-transparent hover:border-green-500 transition shadow-sm";
            wrap.style.width  = "80px";
            wrap.style.height = "60px";

            const img = document.createElement("img");
            img.src = src;
            img.alt = `Frame ${idx + 1}`;
            img.className = "w-full h-full object-cover";
            img.loading = "lazy";

            const label = document.createElement("span");
            label.className = "absolute bottom-0 left-0 right-0 text-center text-[10px] font-bold text-white bg-black/50 py-0.5";
            label.textContent = `Frame ${idx + 1}`;

            wrap.appendChild(img);
            wrap.appendChild(label);

            // Tap to enlarge
            wrap.addEventListener("click", () => openFrameLightbox(src, idx + 1));

            gallery.appendChild(wrap);
        });
    }

    // ----------------------------------------------------------
    // Frame lightbox (tap-to-enlarge)
    // ----------------------------------------------------------
    function openFrameLightbox(src, frameNum) {
        const existing = document.getElementById("va-lightbox");
        if (existing) existing.remove();

        const overlay = document.createElement("div");
        overlay.id = "va-lightbox";
        overlay.className = "fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 cursor-pointer";
        overlay.innerHTML = `
            <div class="relative max-w-2xl w-full">
                <button class="absolute -top-10 right-0 text-white text-3xl font-bold leading-none">✕</button>
                <img src="${src}" alt="Frame ${frameNum}" class="w-full rounded-2xl shadow-2xl">
                <p class="text-center text-white text-xs mt-3 font-semibold opacity-70">Frame ${frameNum}</p>
            </div>
        `;
        overlay.addEventListener("click", () => overlay.remove());
        document.body.appendChild(overlay);
    }

    function renderTreatmentFallback(treatment) {
        const sec = document.getElementById("treatmentGuidanceSection");
        if (!sec) return;
        if (!treatment) {
            sec.classList.remove("hidden");
            const fb = document.getElementById("treatmentFallback");
            const vr = document.getElementById("treatmentVerified");
            if (fb) fb.classList.remove("hidden");
            if (vr) vr.classList.add("hidden");
        }
    }

    // ----------------------------------------------------------
    // Camera permission for video recording
    // ----------------------------------------------------------
    async function triggerVideoRecord() {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                stream.getTracks().forEach(t => t.stop());
                if (videoRecordInput) videoRecordInput.click();
            } catch (err) {
                if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
                    showVideoError("Camera permission was denied. Please enable camera access in your browser settings, or select a video from your gallery instead.");
                } else {
                    showVideoError(`Camera error: ${err.message || err}. Please select a video from your gallery instead.`);
                }
            }
        } else {
            // Fallback: just trigger the input (many browsers handle it natively)
            if (videoRecordInput) videoRecordInput.click();
        }
    }

    // ----------------------------------------------------------
    // Utility
    // ----------------------------------------------------------
    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    // ----------------------------------------------------------
    // Wire up event listeners (defensive — elements may not exist
    // on non-detect pages)
    // ----------------------------------------------------------
    if (videoRecordInput) {
        videoRecordInput.addEventListener("change", () => {
            if (videoRecordInput.files.length > 0) handleVideoFile(videoRecordInput.files[0]);
        });
    }

    if (videoGalleryInput) {
        videoGalleryInput.addEventListener("change", () => {
            if (videoGalleryInput.files.length > 0) handleVideoFile(videoGalleryInput.files[0]);
        });
    }

    if (videoRecordBtn) {
        videoRecordBtn.addEventListener("click", e => { e.stopPropagation(); triggerVideoRecord(); });
    }

    if (videoSelectBtn) {
        videoSelectBtn.addEventListener("click", e => { e.stopPropagation(); if (videoGalleryInput) videoGalleryInput.click(); });
    }

    if (videoRemoveBtn) {
        videoRemoveBtn.addEventListener("click", e => { e.stopPropagation(); removeVideoSelection(); });
    }

    if (videoAnalyzeBtn) {
        videoAnalyzeBtn.addEventListener("click", e => { e.stopPropagation(); analyzeVideo(); });
    }

    // ----------------------------------------------------------
    // Show/hide video panel toggle (3rd button in detect.html)
    // ----------------------------------------------------------
    const videoAnalysisPanel = document.getElementById("videoAnalysisPanel");
    const uploadForm = document.getElementById("uploadForm");
    // The upload card is the white rounded box that wraps the upload form
    const uploadCard = uploadForm ? uploadForm.closest(".bg-white.rounded-3xl") : null;
    // Desktop entry point card (contains the "Analyze Video Instead" button)
    const desktopVideoEntryDiv = document.getElementById("videoOptionBtnDesktop")?.closest("div");

    function openVideoPanel() {
        // Hide image card and desktop entry
        if (uploadCard) uploadCard.classList.add("hidden");
        if (desktopVideoEntryDiv) desktopVideoEntryDiv.classList.add("hidden");
        // Show video panel
        if (videoAnalysisPanel) {
            videoAnalysisPanel.classList.remove("hidden");
            videoAnalysisPanel.scrollIntoView({ behavior: "smooth" });
        }
        // Hide any existing results
        const resultSec = document.getElementById("resultSection");
        if (resultSec) resultSec.classList.add("hidden");
        if (videoResultSection) videoResultSection.classList.add("hidden");
    }

    function closeVideoPanel() {
        if (videoAnalysisPanel) videoAnalysisPanel.classList.add("hidden");
        if (uploadCard) uploadCard.classList.remove("hidden");
        if (desktopVideoEntryDiv) desktopVideoEntryDiv.classList.remove("hidden");
        removeVideoSelection();
    }

    // Mobile button
    const videoOptionBtnMobile = document.getElementById("videoOptionBtn");
    if (videoOptionBtnMobile) {
        videoOptionBtnMobile.addEventListener("click", e => { e.stopPropagation(); openVideoPanel(); });
    }
    // Desktop button
    const videoOptionBtnDesktop = document.getElementById("videoOptionBtnDesktop");
    if (videoOptionBtnDesktop) {
        videoOptionBtnDesktop.addEventListener("click", e => { e.stopPropagation(); openVideoPanel(); });
    }

    // Back-to-image button inside video panel
    const backToImageBtn = document.getElementById("backToImageBtn");
    if (backToImageBtn && videoAnalysisPanel) {
        backToImageBtn.addEventListener("click", e => { e.stopPropagation(); closeVideoPanel(); });
    }

})();
