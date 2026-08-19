/**
 * Web Speech API Voice Manager for Vignan Campus Transport System
 * Synchronizes voice alerts with popup notifications & handles 50m voice auto-off rule.
 */
class VoiceManager {
    constructor() {
        this.isEnabled = localStorage.getItem('vignan_voice_enabled') !== 'false';
        this.synth = window.speechSynthesis;
        this.selectedBusId = null;
        this.selectedBusNumber = null;
        this.recentSpokenMessages = new Map();
        this.cooldownSeconds = 10; // Cooldown for repeat alerts

        this.triggeredThresholds = {
            dist_2km: false,
            dist_1km: false,
            dist_500m: false,
            arrived: false
        };

        this.isAutoOffArrived = false;

        // 15-Second Selected Bus Voice Cycle Timer
        this.timer15s = null;
        this.latestTelemetry = {
            distKm: null,
            etaMin: null,
            pickupName: "your pickup point"
        };

        console.log("VoiceManager initialized. Voice Enabled:", this.isEnabled);
    }

    setSelectedBus(busId, busNumber) {
        // Clear previous 15-second timer immediately on bus change
        this.clear15sVoiceTimer();

        this.selectedBusId = busId ? parseInt(busId) : null;
        this.selectedBusNumber = busNumber ? busNumber.toString() : null;
        this.resetThresholds();
        console.log(`VoiceManager scoped to Bus ID: ${this.selectedBusId} (${this.selectedBusNumber})`);

        // Start new 15-second cycle timer if voice is enabled and bus is selected
        if (this.selectedBusId && this.isEnabled) {
            this.start15sVoiceTimer();
        }
    }

    resetThresholds() {
        this.triggeredThresholds = { dist_2km: false, dist_1km: false, dist_500m: false, arrived: false };
        this.isAutoOffArrived = false;
    }

    start15sVoiceTimer() {
        this.clear15sVoiceTimer();
        if (!this.selectedBusId || !this.isEnabled) return;

        console.log(`▶ Starting 15-second voice update cycle for Bus ${this.selectedBusNumber}`);
        this.timer15s = setInterval(() => {
            this.trigger15sVoiceUpdate();
        }, 15000);
    }

    clear15sVoiceTimer() {
        if (this.timer15s) {
            clearInterval(this.timer15s);
            this.timer15s = null;
            console.log("⏹ Stopped 15-second voice update timer.");
        }
    }

    updateTelemetryData(distKm, etaMin, pickupName = null) {
        if (distKm !== undefined && distKm !== null) this.latestTelemetry.distKm = parseFloat(distKm);
        if (etaMin !== undefined && etaMin !== null) this.latestTelemetry.etaMin = parseInt(etaMin);
        if (pickupName) this.latestTelemetry.pickupName = pickupName;
    }

    trigger15sVoiceUpdate() {
        if (!this.isEnabled || !this.selectedBusId || this.isAutoOffArrived) {
            return;
        }

        const { distKm, etaMin, pickupName } = this.latestTelemetry;
        if (distKm === null || etaMin === null) return;

        // Arrival check (<= 50m)
        if (distKm <= 0.05) {
            this.clear15sVoiceTimer();
            return;
        }

        const voiceMsg = `${this.selectedBusNumber} is ${distKm} kilometers away from ${pickupName}. It will take approximately ${etaMin} minutes to reach your pickup point.`;
        const popupMsg = `${this.selectedBusNumber} — ${distKm} km away from ${pickupName} (ETA: ~${etaMin} min)`;

        console.log("⏰ 15-Second Voice Update:", voiceMsg);
        
        // Always display matching popup notification
        showPopupNotification('DISTANCE_UPDATE', popupMsg, this.selectedBusId);

        // Speak utterance if not currently speaking
        if (this.synth && !this.synth.speaking) {
            this.speakUtterance(voiceMsg);
        }
    }

    enableVoice() {
        this.isEnabled = true;
        localStorage.setItem('vignan_voice_enabled', 'true');
        this.speakFeedback("Voice announcements turned ON.");
        this.updateUiState(true, 'ON');
        if (this.selectedBusId) {
            this.start15sVoiceTimer();
        }
    }

    disableVoice(reason = 'OFF') {
        this.isEnabled = false;
        localStorage.setItem('vignan_voice_enabled', 'false');
        this.clear15sVoiceTimer();
        this.stopSpeaking();
        this.updateUiState(false, reason);
    }

    updateUiState(active, text) {
        const btn = document.getElementById('btn-toggle-voice');
        const textEl = document.getElementById('voice-status-text');
        const iconEl = document.getElementById('voice-icon');
        const cardInd = document.getElementById('card-voice-indicator');

        if (btn) {
            if (active) btn.classList.add('active');
            else btn.classList.remove('active');
        }
        if (textEl) textEl.innerText = text;
        if (iconEl) {
            iconEl.className = active ? 'fa-solid fa-volume-high' : 'fa-solid fa-volume-xmark';
        }
        if (cardInd) {
            cardInd.innerText = active ? '🔊 ON' : `🔇 ${text}`;
        }
    }

    stopSpeaking() {
        if (this.synth && this.synth.speaking) {
            this.synth.cancel();
        }
    }

    speakUtterance(text) {
        if (!this.synth || !this.isEnabled) return;
        this.stopSpeaking();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 1.0;
        utterance.lang = 'en-US';
        this.synth.speak(utterance);
    }

    /**
     * CRITICAL: Voice + Popup synchronized dispatcher!
     */
    speakAndNotify(message, type = 'NOTIFICATION', busId = null, overrideAutoOff = false) {
        showPopupNotification(type, message, busId);

        if (busId && this.selectedBusId && parseInt(busId) !== this.selectedBusId) {
            return;
        }

        if (!this.isEnabled && !overrideAutoOff) return;

        this.speakUtterance(message);
    }

    /**
     * Process distance threshold notifications and 50m AUTOMATIC VOICE OFF RULE
     */
    processDistanceTelemetry(distKm, stopName = "your pickup point") {
        if (!this.selectedBusNumber) return;

        this.updateTelemetryData(distKm, Math.ceil(distKm * 2.5), stopName);

        // 🛑 AUTOMATIC VOICE OFF RULE (Distance <= 50 meters = 0.05 km)
        if (distKm <= 0.05) {
            if (!this.triggeredThresholds.arrived) {
                this.triggeredThresholds.arrived = true;
                this.clear15sVoiceTimer();

                const arrivalMsg = `${this.selectedBusNumber} has arrived at your pickup point.`;
                this.speakAndNotify(arrivalMsg, 'BUS_ARRIVED', this.selectedBusId, true);

                setTimeout(() => {
                    console.log("🛑 AUTOMATIC VOICE OFF AT ARRIVAL TRIGGERED (<= 50m)");
                    this.isAutoOffArrived = true;
                    this.disableVoice('OFF (Arrived)');
                }, 2000);
            }
            return;
        }

        if (this.isAutoOffArrived || !this.isEnabled) return;

        // 500 Meters Threshold
        if (distKm <= 0.5 && !this.triggeredThresholds.dist_500m) {
            this.triggeredThresholds.dist_500m = true;
            const msg = `${this.selectedBusNumber} is approximately 500 meters from ${stopName}.`;
            this.speakAndNotify(msg, 'DISTANCE_UPDATE', this.selectedBusId);
        }
        // 1.0 Kilometer Threshold
        else if (distKm <= 1.1 && distKm > 0.5 && !this.triggeredThresholds.dist_1km) {
            this.triggeredThresholds.dist_1km = true;
            const msg = `${this.selectedBusNumber} is 1.0 kilometer away from ${stopName}.`;
            this.speakAndNotify(msg, 'DISTANCE_UPDATE', this.selectedBusId);
        }
        // 2.0 Kilometers Threshold
        else if (distKm <= 2.2 && distKm > 1.1 && !this.triggeredThresholds.dist_2km) {
            this.triggeredThresholds.dist_2km = true;
            const msg = `${this.selectedBusNumber} is 2.0 kilometers away from ${stopName}.`;
            this.speakAndNotify(msg, 'DISTANCE_UPDATE', this.selectedBusId);
        }
    }

    speakFeedback(msg) {
        if (!this.synth) return;
        this.stopSpeaking();
        const utterance = new SpeechSynthesisUtterance(msg);
        this.synth.speak(utterance);
    }
}

window.voiceManager = new VoiceManager();
