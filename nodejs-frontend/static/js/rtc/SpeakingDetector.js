/*
 * Copyright 2026 SejonJang (wkdtpwhs@gmail.com)
 *
 * Licensed under the  GNU General Public License v3.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   https://www.gnu.org/licenses/gpl-3.0.html
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * SpeakingDetector - 참가자별 발화 여부를 실시간 감지해 `.participant` 타일에 speaking 클래스를 토글하는 모듈
 * 공유 AudioContext 1개 + 단일 requestAnimationFrame 루프로 전 참가자를 순회한다 (참가자당 루프 생성 금지).
 * AudioMixer.js의 AudioContext/createMediaStreamSource 패턴을 재사용하되, destination에는 연결하지 않는
 * read-only 분석 전용 tap으로 구성해 재생/녹화 경로에 영향을 주지 않는다.
 */
const SPEAKING_DETECT_CONFIG = {
    FFT_SIZE: 512,              // 시간영역 분석 버퍼 크기 (작게 유지 - CPU 절감)
    RMS_THRESHOLD: 0.05,        // 발화 판정 RMS 임계값 (0.0~1.0, 실측 튜닝 대상)
    RELEASE_DEBOUNCE_MS: 250    // 임계값 하회 후 하이라이트 유지 시간 (과민 반응 방지)
};

const SpeakingDetector = {
    audioContext: null,
    analysers: null,
    rafId: null,
    isRunning: false,
    nextToken: 1,

    /**
     * 참가자 오디오 스트림에 발화 감지용 analyser를 부착한다.
     * @param {string} userId
     * @param {MediaStream} stream - 로컬 원본 스트림 또는 원격 audio-only 스트림
     * @param {HTMLElement} targetElement - speaking 클래스를 토글할 participant 컨테이너
     * @return {number|null} detach 시 소유권 확인에 사용하는 token
     */
    attachSpeaking: function (userId, stream, targetElement) {
        const self = this;

        if (!stream || !stream.getAudioTracks || stream.getAudioTracks().length === 0) {
            console.warn('[SpeakingDetector] 오디오 트랙 없음, attach skip:', userId);
            return null;
        }

        try {
            self._ensureContext();

            // 동일 userId 재attach(재연결) 시 기존 노드 정리 후 재생성 — AudioMixer.addAudioStream과 동일 패턴
            if (self.analysers.has(userId)) {
                const existingEntry = self.analysers.get(userId);
                self._setSpeakingClass(existingEntry, false);
                self._disconnectEntry(existingEntry);
                self.analysers.delete(userId);
            }

            if (self.audioContext.state === 'suspended') {
                self.audioContext.resume().catch(function (error) {
                    console.error('[SpeakingDetector] AudioContext resume 실패:', error);
                });
            }

            const source = self.audioContext.createMediaStreamSource(stream);
            const analyser = self.audioContext.createAnalyser();
            analyser.fftSize = SPEAKING_DETECT_CONFIG.FFT_SIZE;
            // destination에 연결하지 않는다 — 재생/녹화 sink와 분리된 read-only 분석 전용 tap
            source.connect(analyser);

            const token = self.nextToken++;
            self.analysers.set(userId, {
                token: token,
                source: source,
                analyser: analyser,
                data: new Uint8Array(analyser.fftSize),
                audioTrack: stream.getAudioTracks()[0],
                targetElement: targetElement || document.getElementById(userId),
                speaking: false,
                belowSince: null
            });

            self._ensureLoop();
            return token;
        } catch (error) {
            console.error('[SpeakingDetector] attach 실패:', userId, error);
            return null;
        }
    },

    /**
     * 참가자 analyser를 정리한다. Map이 비면 rAF 루프를 중단한다.
     * @param {string} userId
     * @param {number|null} ownerToken - stale participant cleanup 방지용 attach token
     */
    detachSpeaking: function (userId, ownerToken) {
        const self = this;
        if (!self.analysers || !self.analysers.has(userId)) {
            return;
        }

        const entry = self.analysers.get(userId);
        if (arguments.length > 1 && entry.token !== ownerToken) {
            return;
        }

        self._disconnectEntry(entry);
        self.analysers.delete(userId);
        self._setSpeakingClass(entry, false);

        if (self.analysers.size === 0) {
            self._stopLoop();
        }
    },

    /**
     * 방 나가기 시 전체 자원을 정리한다 (rAF 중단, 전 analyser disconnect, AudioContext close).
     * detachSpeaking 누락 대비 방어적 재호출로도 안전하도록 idempotent하게 동작한다.
     */
    stopSpeaking: function () {
        const self = this;

        self._stopLoop();

        if (self.analysers) {
            self.analysers.forEach(function (entry) {
                self._disconnectEntry(entry);
                self._setSpeakingClass(entry, false);
            });
            self.analysers.clear();
        }

        if (self.audioContext && self.audioContext.state !== 'closed') {
            self.audioContext.close().catch(function (error) {
                console.error('[SpeakingDetector] AudioContext close 실패:', error);
            });
        }
        self.audioContext = null;
    },

    // AudioContext/Map을 최초 attach 시점에 지연 생성한다 (미사용 시 자원 소비 없음)
    _ensureContext: function () {
        const self = this;
        if (!self.analysers) {
            self.analysers = new Map();
        }
        if (!self.audioContext || self.audioContext.state === 'closed') {
            const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
            self.audioContext = new AudioContextCtor();
        }
    },

    _ensureLoop: function () {
        const self = this;
        if (self.isRunning) {
            return;
        }
        self.isRunning = true;
        self.rafId = requestAnimationFrame(function loop() {
            self._tick();
            if (self.isRunning) {
                self.rafId = requestAnimationFrame(loop);
            }
        });
    },

    _stopLoop: function () {
        const self = this;
        if (self.rafId !== null) {
            cancelAnimationFrame(self.rafId);
            self.rafId = null;
        }
        self.isRunning = false;
    },

    // 상승은 즉시 반영하고, 하강은 RELEASE_DEBOUNCE_MS 이상 지속돼야 반영 — 과민 반응 방지
    _tick: function () {
        const self = this;
        const now = performance.now();

        self.analysers.forEach(function (entry, userId) {
            // 마이크 off(트랙 disabled)면 판정 스킵 + 즉시 하이라이트 해제
            if (!entry.audioTrack || !entry.audioTrack.enabled) {
                entry.belowSince = null;
                self._setSpeaking(userId, entry, false);
                return;
            }

            entry.analyser.getByteTimeDomainData(entry.data);
            const rms = self._computeRms(entry.data);

            if (rms >= SPEAKING_DETECT_CONFIG.RMS_THRESHOLD) {
                entry.belowSince = null;
                self._setSpeaking(userId, entry, true);
            } else if (entry.speaking) {
                if (entry.belowSince === null) {
                    entry.belowSince = now;
                } else if (now - entry.belowSince >= SPEAKING_DETECT_CONFIG.RELEASE_DEBOUNCE_MS) {
                    self._setSpeaking(userId, entry, false);
                }
            }
        });
    },

    _computeRms: function (data) {
        let sumSquares = 0;
        for (let i = 0; i < data.length; i++) {
            const normalized = (data[i] - 128) / 128;
            sumSquares += normalized * normalized;
        }
        return Math.sqrt(sumSquares / data.length);
    },

    _setSpeaking: function (userId, entry, flag) {
        if (entry.speaking === flag) {
            return; // 상태 변화 없으면 DOM 조작 생략 (idempotent)
        }
        entry.speaking = flag;
        this._setSpeakingClass(entry, flag);
    },

    _setSpeakingClass: function (entry, flag) {
        if (entry.targetElement) {
            entry.targetElement.classList.toggle('speaking', flag);
        }
    },

    _disconnectEntry: function (entry) {
        try {
            entry.source.disconnect();
        } catch (error) {
            console.error('[SpeakingDetector] source disconnect 실패:', error);
        }
    }
};

// 전역 스코프에 노출 (AudioMixer.js와 동일 패턴)
window.SpeakingDetector = SpeakingDetector;
