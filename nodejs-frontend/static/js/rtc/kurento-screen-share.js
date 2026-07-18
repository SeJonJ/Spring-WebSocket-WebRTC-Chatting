/*
 * Copyright 2023 SejonJang (wkdtpwhs@gmail.com)
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

/** 화면 공유 실행 과정
 * 나와 연결된 다른 peer 에 나의 화면을 공유하기 위해서는 다른 peer 에 보내는 Track 에서 stream 을 교체할 필요가 있다.
 * Track 이란 현재 MediaStream 을 구성하는 각 요소를 의미한다.
 *    - Track 는 오디오, 비디오, 자막 총 3개의 stream 으로 구성된다.
 *    - 때문에 Track 객체는 track[0] = 오디오, track[1] = 비디오 의 배열 구조로 되어있다
 * MediaStream 이란 video stream 과 audio steam 등의 미디어 스트림을 다루는 객체를 이야기한다
 * - stream(스트림)이란 쉽게 생각하자면 비디오와 오디오 데이터라고 이해하면 될 듯 하다 -
 *
 * 즉 상대방에게 보내는 track 에서 나의 웹캠 videoStream 대신 공유 화면에 해당하는 videoStream 으로 변경하는 것이다.
 *
 * 더 구체적으로는 아래 순서를 따른다.
 *
 * 1. startScreenShare() 함수를 호출합니다.
 * 2. ScreenHandler.start() 함수를 호출하여 shareView 변수에 화면 공유에 사용될 MediaStream 객체를 할당합니다.
 * 3. 화면 공유 화면을 로컬 화면에 표시합니다.
 * 4. 연결된 다른 peer에게 화면 공유 화면을 전송하기 위해 RTCRtpSender.replaceTrack() 함수를 사용하여 연결된 다른 peer에게 전송되는 비디오 Track을 shareView.getVideoTracks()[0]으로 교체합니다.
 * 5. shareView 객체의 비디오 Track이 종료되는 경우, stopScreenShare() 함수를 호출하여 화면 공유를 중지합니다.
 * 5. stopScreenShare() 함수에서는 ScreenHandler.end() 함수를 호출하여 shareView 객체에서 발생하는 모든 Track에 대해 stop() 함수를 호출하여 스트림 전송을 중지합니다.
 * 6. 원래 화면으로 되돌리기 위해 연결된 다른 peer에게 전송하는 Track을 로컬 비디오 Track으로 교체합니다.
 * 즉, 해당 코드는 WebRTC 기술을 사용하여 MediaStream 객체를 사용해 로컬에서 받은 Track을 다른 peer로 전송하고, replaceTrack() 함수를 사용하여 비디오 Track을 교체하여 화면 공유를 구현하는 코드입니다.
 * **/

// 화면 공유를 위한 변수 선언
const screenHandler = new ScreenHandler();
let shareView = null;

// 화면 공유 설정 및 통계
const screenShareConfig = {
    // 화질 프리셋
    qualityPresets: {
        'high': {
            width: { ideal: 1920, max: 1920 },
            height: { ideal: 1080, max: 1080 },
            frameRate: { ideal: 30, max: 30 }
        },
        'medium': {
            width: { ideal: 1280, max: 1280 },
            height: { ideal: 720, max: 720 },
            frameRate: { ideal: 15, max: 20 }
        },
        'low': {
            width: { ideal: 640, max: 640 },
            height: { ideal: 360, max: 360 },
            frameRate: { ideal: 10, max: 15 }
        },
        'auto': {
            width: { ideal: 1280, max: 1920 },
            height: { ideal: 720, max: 1080 },
            frameRate: { ideal: 15, max: 30 }
        }
    },
    
    // 현재 설정
    currentQuality: 'auto',
    
    // 통계 정보
    stats: {
        frameRate: 0,
        bitrate: 0,
        packetsLost: 0,
        timestamp: Date.now()
    },
    
    // 자동 최적화 설정
    autoOptimize: true,
    qualityAdjustInterval: null
};

function getScreenSharePeerConnection() {
    const participant = participants[userId];
    if (!participant || !participant.rtcPeer || !participant.rtcPeer.peerConnection) {
        return null;
    }
    return participant.rtcPeer.peerConnection;
}

function collectScreenShareStatsSnapshot() {
    const peerConnection = getScreenSharePeerConnection();
    if (!peerConnection) {
        return Promise.resolve(null);
    }

    return peerConnection.getStats()
        .then(function (stats) {
            let outboundRtp = null;
            let candidatePair = null;

            stats.forEach(function (report) {
                if (report.type === 'outbound-rtp' && report.kind === 'video') {
                    outboundRtp = report;
                } else if (report.type === 'candidate-pair' && report.state === 'succeeded') {
                    candidatePair = report;
                }
            });

            return {
                stats,
                outboundRtp,
                candidatePair,
                timestamp: Date.now()
            };
        });
}

function calculateNetworkQualityFromSnapshot(snapshot) {
    if (!snapshot || !snapshot.outboundRtp || !snapshot.candidatePair) {
        return 'medium';
    }

    const outboundRtp = snapshot.outboundRtp;
    const candidatePair = snapshot.candidatePair;
    const bitrate = outboundRtp.bytesSent * 8 / 1000;
    const packetLoss = outboundRtp.packetsLost || 0;
    const rtt = candidatePair.currentRoundTripTime * 1000 || 0;
    const jitter = outboundRtp.jitter || 0;

    let qualityScore = 100;
    if (bitrate > 2000) {
        qualityScore += 0;
    } else if (bitrate > 1000) {
        qualityScore -= 15;
    } else {
        qualityScore -= 30;
    }

    qualityScore -= Math.min(packetLoss * 2, 40);

    if (rtt > 200) {
        qualityScore -= 20;
    } else if (rtt > 100) {
        qualityScore -= 10;
    }

    if (jitter > 0.05) {
        qualityScore -= 10;
    }

    let quality;
    if (qualityScore >= 80) {
        quality = 'high';
    } else if (qualityScore >= 50) {
        quality = 'medium';
    } else {
        quality = 'low';
    }

    lastNetworkQuality = quality;
    return quality;
}

function selectOptimalQuality(networkQuality, deviceQuality) {
    const qualityMatrix = {
        'high_high': 'high',
        'high_medium': 'medium',
        'high_low': 'medium',
        'medium_high': 'medium',
        'medium_medium': 'medium',
        'medium_low': 'low',
        'low_high': 'low',
        'low_medium': 'low',
        'low_low': 'low'
    };

    const key = `${networkQuality}_${deviceQuality}`;
    return qualityMatrix[key] || 'medium';
}

function updateDevicePerformanceFromSnapshot(snapshot) {
    if (!snapshot || !snapshot.outboundRtp) {
        return 'medium';
    }

    const outboundRtp = snapshot.outboundRtp;
    const currentFrameRate = outboundRtp.framesPerSecond || 0;
    const framesSent = outboundRtp.framesSent || 0;
    const framesEncoded = outboundRtp.framesEncoded || 0;
    const frameDropRate = framesSent > 0 ? ((framesEncoded - framesSent) / framesEncoded) * 100 : 0;
    const encodeTime = outboundRtp.totalEncodeTime || 0;
    const encodedFrames = outboundRtp.framesEncoded || 1;
    const avgEncodeTime = (encodeTime * 1000) / encodedFrames;

    devicePerformance.metrics.frameDropRate = frameDropRate;
    devicePerformance.metrics.encodeTime = avgEncodeTime;
    devicePerformance.metrics.lastUpdated = Date.now();

    updatePerformanceHistory(currentFrameRate, avgEncodeTime, outboundRtp.bytesSent);
    return calculatePerformanceGrade();
}

function updateScreenShareStatsFromSnapshot(snapshot) {
    if (!shareView || !snapshot || !snapshot.outboundRtp) {
        return;
    }

    const outboundRtp = snapshot.outboundRtp;
    const now = snapshot.timestamp || Date.now();
    const timeDiff = (now - screenShareConfig.stats.timestamp) / 1000;
    if (timeDiff <= 0) {
        return;
    }

    const bytesDiff = outboundRtp.bytesSent - (screenShareConfig.stats.bytesLastSent || 0);
    screenShareConfig.stats.bitrate = (bytesDiff * 8) / (timeDiff * 1000);
    screenShareConfig.stats.frameRate = outboundRtp.framesPerSecond || 0;
    screenShareConfig.stats.packetsLost = outboundRtp.packetsLost || 0;
    screenShareConfig.stats.bytesLastSent = outboundRtp.bytesSent;
    screenShareConfig.stats.timestamp = now;

    screenShareConfig.stats.framesEncoded = outboundRtp.framesEncoded || 0;
    screenShareConfig.stats.framesSent = outboundRtp.framesSent || 0;
    screenShareConfig.stats.encodeTime = outboundRtp.totalEncodeTime || 0;
    screenShareConfig.stats.qualityLimitationReason = outboundRtp.qualityLimitationReason || 'none';

    analyzeQualityLimitation(outboundRtp.qualityLimitationReason);
    checkPerformanceWarnings();
    updateStatsDisplay();
}

// 네트워크 품질 감지
function detectNetworkQuality() {
    return collectScreenShareStatsSnapshot()
        .then(calculateNetworkQualityFromSnapshot)
        .catch(function (error) {
            console.warn('네트워크 품질 감지 실패:', error);
            return 'medium';
        });
}

// 디바이스 성능 감지 시스템
const devicePerformance = {
    // 성능 지표
    metrics: {
        cpuUsage: 0,
        memoryUsage: 0,
        frameDropRate: 0,
        encodeTime: 0,
        lastUpdated: Date.now()
    },
    
    // 성능 등급
    grade: 'medium', // 'high', 'medium', 'low'
    
    // 성능 히스토리 (최근 10개 측정값)
    history: {
        frameRates: [],
        encodeTimes: [],
        bitrates: []
    }
};

// 디바이스 성능 감지
function detectDevicePerformance() {
    return collectScreenShareStatsSnapshot()
        .then(updateDevicePerformanceFromSnapshot)
        .catch(function (error) {
            console.warn('디바이스 성능 감지 실패:', error);
            return 'medium';
        });
}

// 성능 히스토리 업데이트
function updatePerformanceHistory(frameRate, encodeTime, bitrate) {
    const maxHistorySize = 10;
    
    // 프레임률 히스토리
    devicePerformance.history.frameRates.push(frameRate);
    if (devicePerformance.history.frameRates.length > maxHistorySize) {
        devicePerformance.history.frameRates.shift();
    }
    
    // 인코딩 시간 히스토리
    devicePerformance.history.encodeTimes.push(encodeTime);
    if (devicePerformance.history.encodeTimes.length > maxHistorySize) {
        devicePerformance.history.encodeTimes.shift();
    }
    
    // 비트레이트 히스토리
    devicePerformance.history.bitrates.push(bitrate);
    if (devicePerformance.history.bitrates.length > maxHistorySize) {
        devicePerformance.history.bitrates.shift();
    }
}

// 성능 등급 계산
function calculatePerformanceGrade() {
    const { frameDropRate, encodeTime } = devicePerformance.metrics;
    const { frameRates, encodeTimes } = devicePerformance.history;
    
    // 평균값 계산
    const avgFrameRate = frameRates.length > 0 ? 
        frameRates.reduce((a, b) => a + b, 0) / frameRates.length : 0;
    const avgEncodeTime = encodeTimes.length > 0 ? 
        encodeTimes.reduce((a, b) => a + b, 0) / encodeTimes.length : 0;
    
    // 성능 점수 계산 (0-100)
    let score = 100;
    
    // 프레임 드롭률 페널티
    score -= Math.min(frameDropRate * 2, 30);
    
    // 인코딩 시간 페널티 (>20ms 시 페널티)
    if (avgEncodeTime > 20) {
        score -= Math.min((avgEncodeTime - 20) * 2, 30);
    }
    
    // 평균 프레임률 보너스/페널티
    if (avgFrameRate < 10) {
        score -= 20;
    } else if (avgFrameRate > 25) {
        score += 10;
    }
    
    // 성능 등급 결정
    if (score >= 80) {
        devicePerformance.grade = 'high';
        return 'high';
    } else if (score >= 50) {
        devicePerformance.grade = 'medium';
        return 'medium';
    } else {
        devicePerformance.grade = 'low';
        return 'low';
    }
}

// 통합 품질 결정 (네트워크 + 디바이스)
function determineOptimalQuality(snapshot) {
    const qualityPromise = arguments.length > 0
        ? Promise.resolve(snapshot)
        : collectScreenShareStatsSnapshot();

    return qualityPromise.then(function (statsSnapshot) {
        const networkQuality = calculateNetworkQualityFromSnapshot(statsSnapshot);
        const deviceQuality = updateDevicePerformanceFromSnapshot(statsSnapshot);
        const optimalQuality = selectOptimalQuality(networkQuality, deviceQuality);

        console.log(`품질 결정: 네트워크(${networkQuality}) + 디바이스(${deviceQuality}) = ${optimalQuality}`);
        return optimalQuality;
    });
}

// 고급 화면 공유 품질 자동 조정
function adjustScreenShareQuality(snapshot) {
    if (!shareView || !screenShareConfig.autoOptimize) {
        return Promise.resolve();
    }

    return determineOptimalQuality(snapshot)
        .then(function (optimalQuality) {
            if (optimalQuality === screenShareConfig.currentQuality) {
                return null;
            }

            const currentPreset = screenShareConfig.qualityPresets[optimalQuality];
            const videoTrack = shareView.getVideoTracks()[0];
            if (!videoTrack || !currentPreset) {
                return null;
            }

            return createSmoothQualityTransition(
                screenShareConfig.currentQuality,
                optimalQuality
            ).then(function (smoothTransition) {
                return videoTrack.applyConstraints(smoothTransition)
                    .then(function () {
                        screenShareConfig.currentQuality = optimalQuality;
                        console.log(`화면 공유 품질 조정: ${optimalQuality} (점진적 전환)`);
                        updateScreenShareUI(optimalQuality);
                        showQualityChangeNotification(optimalQuality);
                    })
                    .catch(function (error) {
                        console.warn('화면 공유 품질 조정 실패:', error);
                        const fallbackPreset = screenShareConfig.qualityPresets[screenShareConfig.currentQuality];
                        if (!fallbackPreset) {
                            return null;
                        }
                        return videoTrack.applyConstraints(fallbackPreset).catch(function (rollbackError) {
                            console.error('품질 롤백 실패:', rollbackError);
                            return null;
                        });
                    });
            });
        });
}

// 점진적 품질 전환 생성
function createSmoothQualityTransition(currentQuality, targetQuality) {
    const current = screenShareConfig.qualityPresets[currentQuality];
    const target = screenShareConfig.qualityPresets[targetQuality];
    
    // 중간값 계산으로 부드러운 전환
    const transition = {
        width: {
            ideal: Math.round((current.width.ideal + target.width.ideal) / 2),
            max: target.width.max
        },
        height: {
            ideal: Math.round((current.height.ideal + target.height.ideal) / 2),
            max: target.height.max
        },
        frameRate: {
            ideal: Math.round((current.frameRate.ideal + target.frameRate.ideal) / 2),
            max: target.frameRate.max
        }
    };
    
    return Promise.resolve(transition);
}

// 품질 변경 알림
function showQualityChangeNotification(quality) {
    const qualityLabels = {
        'high': '🟢 고화질',
        'medium': '🟡 중화질',
        'low': '🔴 저화질',
        'auto': '🔄 자동'
    };
    
    // 임시 알림 표시
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 50px;
        right: 10px;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    notification.textContent = `화질 조정: ${qualityLabels[quality]}`;
    
    document.body.appendChild(notification);
    
    // 페이드 인
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 100);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// 강화된 화면 공유 통계 업데이트
function updateScreenShareStats() {
    if (!shareView) {
        return Promise.resolve();
    }

    return collectScreenShareStatsSnapshot()
        .then(updateScreenShareStatsFromSnapshot)
        .catch(function (error) {
            console.warn('화면 공유 통계 업데이트 실패:', error);
        });
}

// 화질 제한 원인 분석
function analyzeQualityLimitation(reason) {
    const limitationReasons = {
        'none': '제한 없음',
        'cpu': 'CPU 성능 제한',
        'bandwidth': '대역폭 제한',
        'other': '기타 제한'
    };
    
    if (reason && reason !== 'none') {
        console.warn(`화질 제한 감지: ${limitationReasons[reason] || reason}`);
        
        // 제한 원인별 자동 대응
        if (reason === 'cpu') {
            // CPU 제한 시 프레임률 우선 감소
            suggestCpuOptimization();
        } else if (reason === 'bandwidth') {
            // 대역폭 제한 시 해상도 우선 감소
            suggestBandwidthOptimization();
        }
    }
}

// CPU 최적화 제안
function suggestCpuOptimization() {
    if (screenShareConfig.currentQuality !== 'low') {
        console.log('CPU 부하로 인한 자동 최적화 제안: 프레임률 감소');
        // 필요시 자동으로 낮은 품질로 전환
        if (screenShareConfig.autoOptimize) {
            const currentPreset = screenShareConfig.qualityPresets[screenShareConfig.currentQuality];
            const optimizedPreset = {
                ...currentPreset,
                frameRate: {
                    ideal: Math.max(currentPreset.frameRate.ideal - 5, 10),
                    max: currentPreset.frameRate.max
                }
            };
            
            const videoTrack = shareView.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.applyConstraints(optimizedPreset);
            }
        }
    }
}

// 대역폭 최적화 제안
function suggestBandwidthOptimization() {
    if (screenShareConfig.currentQuality !== 'low') {
        console.log('대역폭 부족으로 인한 자동 최적화 제안: 해상도 감소');
        // 필요시 자동으로 낮은 품질로 전환
        if (screenShareConfig.autoOptimize) {
            const currentPreset = screenShareConfig.qualityPresets[screenShareConfig.currentQuality];
            const optimizedPreset = {
                ...currentPreset,
                width: {
                    ideal: Math.round(currentPreset.width.ideal * 0.8),
                    max: currentPreset.width.max
                },
                height: {
                    ideal: Math.round(currentPreset.height.ideal * 0.8),
                    max: currentPreset.height.max
                }
            };
            
            const videoTrack = shareView.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.applyConstraints(optimizedPreset);
            }
        }
    }
}

// 강화된 통계 표시 UI 업데이트
function updateStatsDisplay() {
    const statsElement = document.getElementById('screenShareStats');
    if (statsElement) {
        const stats = screenShareConfig.stats;
        const deviceStats = devicePerformance.metrics;
        
        statsElement.innerHTML = `
            <div class="stats-item">📊 ${Math.round(stats.bitrate)} kbps</div>
            <div class="stats-item">🎞️ ${Math.round(stats.frameRate)} fps</div>
            <div class="stats-item">📉 ${stats.packetsLost} lost</div>
            <div class="stats-item">⚡ ${Math.round(deviceStats.encodeTime)}ms</div>
        `;
        
        // 성능 상태에 따른 색상 변경
        const performanceColor = getPerformanceColor();
        statsElement.style.borderLeft = `3px solid ${performanceColor}`;
        
        // 차트 데이터 업데이트
        updateChartData(stats.frameRate, stats.bitrate);
        
        // 네트워크 및 디바이스 상태 업데이트
        updateNetworkDeviceStatus();
    }
}

// 네트워크 및 디바이스 상태 업데이트
function updateNetworkDeviceStatus() {
    // 네트워크 상태 업데이트
    const networkElement = document.getElementById('networkStatus');
    if (networkElement) {
        const networkQuality = getLastNetworkQuality();
        const networkLabels = {
            'high': '🟢 우수',
            'medium': '🟡 보통',
            'low': '🔴 불량'
        };
        networkElement.textContent = networkLabels[networkQuality] || '🟡 보통';
    }
    
    // 디바이스 상태 업데이트
    const deviceElement = document.getElementById('deviceStatus');
    if (deviceElement) {
        const deviceGrade = devicePerformance.grade;
        const deviceLabels = {
            'high': '🟢 우수',
            'medium': '🟡 보통',
            'low': '🔴 불량'
        };
        deviceElement.textContent = deviceLabels[deviceGrade] || '🟡 보통';
    }
}

// 마지막 네트워크 품질 저장 및 반환
let lastNetworkQuality = 'medium';
function getLastNetworkQuality() {
    return lastNetworkQuality;
}

// 성능 상태 색상 결정
function getPerformanceColor() {
    const grade = devicePerformance.grade;
    switch (grade) {
        case 'high': return '#28a745'; // 초록
        case 'medium': return '#ffc107'; // 노랑
        case 'low': return '#dc3545'; // 빨강
        default: return '#6c757d'; // 회색
    }
}

// 화면 공유 UI 업데이트 개선
function updateScreenShareUI(quality) {
    const qualityElement = document.getElementById('screenShareQuality');
    if (qualityElement) {
        const qualityLabels = {
            'high': '🟢 고화질',
            'medium': '🟡 중화질', 
            'low': '🔴 저화질',
            'auto': '🔄 자동'
        };
        
        // 기본 품질 표시
        qualityElement.innerHTML = `
            <div>${qualityLabels[quality] || qualityLabels['auto']}</div>
        `;
        
        // 품질 선택 드롭다운 동기화
        const qualitySelector = document.getElementById('qualitySelector');
        if (qualitySelector && screenShareConfig.currentQuality !== 'auto') {
            qualitySelector.value = quality;
        }
    }
}

/**
 * ScreenHandler 클래스 정의
 */
function ScreenHandler() {
    /**
     * Cross Browser Screen Capture API를 호출합니다.
     * Chrome 72 이상에서는 navigator.mediaDevices.getDisplayMedia API 호출
     * Chrome 70~71에서는 navigator.getDisplayMedia API 호출 (experimental feature 활성화 필요)
     * 다른 브라우저에서는 screen sharing not supported in this browser 에러 반환
     * @returns {Promise<MediaStream>} 미디어 스트림을 반환합니다.
     */
    function getCrossBrowserScreenCapture() {
        // 화면 공유 최적화 제약조건 적용
        const constraints = {
            video: {
                ...screenShareConfig.qualityPresets[screenShareConfig.currentQuality],
                mediaSource: 'screen',
                // 화면 공유 최적화 설정
                googLeakyBucket: true,
                googCpuOveruseDetection: true,
                googCpuOveruseEncodeUsage: true,
                googHighStartBitrate: true,
                googVeryHighBitrate: true
            },
            audio: {
                // 시스템 오디오 캡처 활성화
                echoCancellation: false,  // 화면 공유 오디오에는 에코 제거 불필요
                noiseSuppression: false,  // 원본 소리 그대로 전달
                autoGainControl: false,   // 자동 볼륨 조절 비활성화
                sampleRate: 48000,        // 고품질 오디오
                channelCount: 2           // 스테레오
            }
        };

        if (navigator.mediaDevices.getDisplayMedia) {
            return navigator.mediaDevices.getDisplayMedia(constraints);
        } else if (navigator.getDisplayMedia) {
            return navigator.getDisplayMedia(constraints);
        } else {
            throw new Error('Screen sharing not supported in this browser');
        }
    }

    /**
     * 화면 공유를 시작합니다.
     * @returns {Promise<MediaStream>} 화면 공유에 사용되는 미디어 스트림을 반환합니다.
     */
    // 화면 공유 핵심 경로는 트랙 교체와 종료 이벤트 순서가 민감해서 async/await 흐름을 유지한다.
    async function start() {
        try {
            shareView = await getCrossBrowserScreenCapture();
            
            // 화면 공유 시작 시 모니터링 시작
            startScreenShareMonitoring();
            
            // 초기 화질 설정 적용
            const videoTrack = shareView.getVideoTracks()[0];
            if (videoTrack) {
                // contentHint 설정 - 화면 공유에 최적화
                videoTrack.contentHint = "detail"; // 텍스트나 상세한 내용에 최적화
                
                // 트랙 종료 이벤트 리스너
                videoTrack.addEventListener('ended', () => {
                    console.log('[WebRTC:Screen] 화면 공유가 종료되었습니다.');
                    stopScreenShare();
                });
            }
            
        } catch (err) {
            console.error('[WebRTC:Screen] getDisplayMedia 실패:', err);
            // 사용자 친화적인 에러 메시지
            showScreenShareError(err);
        }
        return shareView;
    }

    /**
     * 화면 공유를 종료합니다.
     */
    function end() {
        if (shareView) {
            // shareView에서 발생하는 모든 트랙들에 대해 stop() 함수를 호출하여 스트림 전송 중지
            shareView.getTracks().forEach(track => track.stop());
            shareView = null;
            
            // 모니터링 중지
            stopScreenShareMonitoring();
        }
    }

    // 생성자로 반환할 public 변수 선언
    this.start = start;
    this.end = end;
}

// 화면 공유 모니터링 시작 개선
function startScreenShareMonitoring() {
    // 기존 인터벌 정리
    if (screenShareConfig.qualityAdjustInterval) {
        clearInterval(screenShareConfig.qualityAdjustInterval);
    }
    
    // 통계 업데이트 및 품질 조정 (2초마다 - 더 빠른 반응성)
    screenShareConfig.qualityAdjustInterval = setInterval(function () {
        const controls = document.getElementById('screenShareControls');
        // 전체 패널이 닫힌 경우에만 중지한다. 미니멀 모드는 내부 섹션만 숨기므로 모니터링을 유지한다.
        if (!controls || controls.style.display === 'none') {
            pauseScreenShareMonitoring();
            return;
        }

        collectScreenShareStatsSnapshot()
            .then(function (snapshot) {
                updateScreenShareStatsFromSnapshot(snapshot);
                return adjustScreenShareQuality(snapshot);
            })
            .catch(function (error) {
                console.warn('화면 공유 모니터링 루프 실패:', error);
            });
    }, 2000);
    
    // UI 표시
    showScreenShareControls();
    
    // 초기 상태 업데이트
    setTimeout(() => {
        updateNetworkDeviceStatus();
    }, 1000);
}

// 화면 공유 모니터링 중지
function stopScreenShareMonitoring() {
    // UI 숨기기
    hideScreenShareControls();
}

function pauseScreenShareMonitoring() {
    if (screenShareConfig.qualityAdjustInterval) {
        clearInterval(screenShareConfig.qualityAdjustInterval);
        screenShareConfig.qualityAdjustInterval = null;
    }
}

function resumeScreenShareMonitoring() {
    if (!shareView || screenShareConfig.qualityAdjustInterval) {
        return;
    }

    startScreenShareMonitoring();
}

// 화면 공유 에러 표시
function showScreenShareError(error) {
    let message = '';
    switch (error.name) {
        case 'NotAllowedError':
            message = '화면 공유 권한이 거부되었습니다.';
            break;
        case 'NotFoundError':
            message = '공유할 화면을 찾을 수 없습니다.';
            break;
        case 'NotSupportedError':
            message = '브라우저에서 화면 공유를 지원하지 않습니다.';
            break;
        default:
            message = '화면 공유 중 오류가 발생했습니다.';
    }
    
    console.warn(`[WebRTC:Screen] 화면 공유 오류: ${message}`, error);
    showWarningToast(message);
}


// 화면 공유 컨트롤 UI 숨기기
function hideScreenShareControls() {
    const controls = document.getElementById('screenShareControls');
    if (controls) {
        controls.style.display = 'none';
    }
}

// 자동 최적화 토글
function toggleAutoOptimize() {
    screenShareConfig.autoOptimize = !screenShareConfig.autoOptimize;
    const btn = document.getElementById('autoOptimizeBtn');
    if (btn) {
        btn.textContent = screenShareConfig.autoOptimize ? '자동 최적화' : '수동 모드';
        btn.style.background = screenShareConfig.autoOptimize ? '#28a745' : '#6c757d';
    }
}

// 화면 공유 품질 수동 변경
function changeScreenShareQuality(quality) {
    screenShareConfig.currentQuality = quality;

    if (!shareView) {
        return Promise.resolve();
    }

    const videoTrack = shareView.getVideoTracks()[0];
    const constraints = screenShareConfig.qualityPresets[quality];

    if (!videoTrack || !constraints) {
        return Promise.resolve();
    }

    return videoTrack.applyConstraints(constraints)
        .then(function () {
            updateScreenShareUI(quality);
            console.log(`[WebRTC:Screen] 품질 변경: ${quality}`);
        })
        .catch(function (error) {
            console.warn('[WebRTC:Screen] 품질 변경 실패:', error);
        });
}

/**
 * 강화된 화면 공유 시작 함수
 * @returns {Promise<void>}
 */
// 이 구간은 WebRTC sender.replaceTrack와 AudioContext 정리 타이밍이 민감해 Promise 체인으로 바꾸지 않는다.
async function startScreenShare() {
    try {
        // 화면 공유 스트림 획득
        await screenHandler.start();
        
        if (!shareView) {
            console.error('[WebRTC:Screen] 스트림을 생성할 수 없습니다.');
            return;
        }

        const participant = participants[userId];
        if (!participant) {
            console.error('[WebRTC:Screen] 참가자를 찾을 수 없습니다.');
            return;
        }

        const video = participant.getVideoElement();

        // 기존 스트림 백업
        participant.setLocalStream(video.srcObject);

        // 로컬 비디오에 화면 공유 표시
        video.srcObject = shareView;
        
        // 원격 참가자들에게 화면 공유 전송 (비디오 + 오디오)
        const senders = participant.rtcPeer.peerConnection.getSenders();
        
        // 비디오 트랙 교체
        for (const sender of senders) {
            if (sender.track && sender.track.kind === 'video') {
                const videoTrack = shareView.getVideoTracks()[0];
                if (videoTrack) {
                    // 화면 공유에 최적화된 설정 적용
                    videoTrack.contentHint = "detail";
                    
                    // 트랙 교체
                    await sender.replaceTrack(videoTrack);
                    console.log('[WebRTC:Screen] 비디오 트랙 교체 완료');
                }
                break;
            }
        }
        
        // 오디오 트랙 처리: 시스템 오디오 + 마이크 오디오 믹싱
        const audioTracks = shareView.getAudioTracks();
        if (audioTracks.length > 0) {
            // 시스템 오디오가 있는 경우, 마이크와 믹싱
            for (const sender of senders) {
                if (sender.track && sender.track.kind === 'audio') {
                    const systemAudioTrack = audioTracks[0];
                    const microphoneTrack = sender.track;

                    try {
                        // 이전 AudioContext가 있으면 먼저 정리
                        if (participant.audioContext) {
                            try {
                                participant.systemSource?.disconnect();
                                participant.micSource?.disconnect();
                                participant.destination?.disconnect();
                                await participant.audioContext.close();
                                console.log('[WebRTC:Screen] 이전 AudioContext 정리 완료');
                            } catch (cleanupError) {
                                console.error('[WebRTC:Screen] 이전 AudioContext 정리 실패:', cleanupError);
                            }
                        }

                        // Web Audio API를 사용한 오디오 믹싱
                        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

                        // 시스템 오디오 소스 생성
                        const systemStream = new MediaStream([systemAudioTrack]);
                        const systemSource = audioContext.createMediaStreamSource(systemStream);

                        // 마이크 오디오 소스 생성
                        const micStream = new MediaStream([microphoneTrack]);
                        const micSource = audioContext.createMediaStreamSource(micStream);

                        // Destination (믹싱 출력)
                        const destination = audioContext.createMediaStreamDestination();

                        // 두 오디오를 destination으로 연결 (믹싱)
                        systemSource.connect(destination);
                        micSource.connect(destination);

                        // 믹싱된 오디오 트랙
                        const mixedAudioTrack = destination.stream.getAudioTracks()[0];

                        // 기존 트랙 백업 및 노드 참조 저장 (정리용)
                        participant.originalAudioTrack = microphoneTrack;
                        participant.audioContext = audioContext;
                        participant.systemSource = systemSource;
                        participant.micSource = micSource;
                        participant.destination = destination;

                        // 믹싱된 트랙으로 교체
                        await sender.replaceTrack(mixedAudioTrack);
                        console.log('[WebRTC:Screen] 시스템 오디오 + 마이크 오디오 믹싱 완료');
                    } catch (error) {
                        console.error('[WebRTC:Screen] 오디오 믹싱 실패, 시스템 오디오만 사용:', error);
                        // 믹싱 실패 시 시스템 오디오만 사용
                        participant.originalAudioTrack = sender.track;
                        await sender.replaceTrack(systemAudioTrack);
                        console.log('[WebRTC:Screen] 시스템 오디오 트랙으로 교체 완료');
                    }
                    break;
                }
            }
        } else {
            console.log('[WebRTC:Screen] 시스템 오디오 없음, 마이크 오디오만 유지');
        }

        console.log('[WebRTC:Screen] 화면 공유 시작됨');

        // 녹화 중이라면 믹싱된 오디오가 자동으로 녹화에 포함됩니다
        // (WebRTC를 통해 전송되므로 별도 처리 불필요)
        if (typeof recording !== 'undefined' && recording.isRecordingInProgress) {
            console.log('[WebRTC:Screen] 녹화 중: 시스템 오디오 + 마이크 오디오 모두 녹화');
        }

    } catch (error) {
        console.error('[WebRTC:Screen] 시작 실패:', error);
        showScreenShareError(error);
    }
}

/**
 * 강화된 화면 공유 중지 함수
 * @returns {Promise<void>}
 */
// 중지 시에는 원본 스트림 복원과 AudioContext close 순서가 중요해서 async/await를 유지한다.
async function stopScreenShare() {
    try {
        const participant = participants[userId];
        if (!participant) {
            console.error('[WebRTC:Screen] 참가자를 찾을 수 없습니다.');
            return;
        }

        const video = participant.getVideoElement();

        // 원래 스트림으로 복원
        const originalStream = participant.getLocalStream();
        if (originalStream) {
            video.srcObject = originalStream;
            
            // 원격 참가자들에게 원래 비디오/오디오 전송
            const senders = participant.rtcPeer.peerConnection.getSenders();
            
            // 비디오 트랙 복원
            for (const sender of senders) {
                if (sender.track && sender.track.kind === 'video') {
                    const videoTrack = originalStream.getVideoTracks()[0];
                    if (videoTrack) {
                        await sender.replaceTrack(videoTrack);
                        console.log('[WebRTC:Screen] 원래 비디오 트랙으로 복원 완료');
                    }
                    break;
                }
            }
            
            // 오디오 트랙 복원 (백업된 오디오 트랙이 있는 경우)
            if (participant.originalAudioTrack) {
                for (const sender of senders) {
                    if (sender.track && sender.track.kind === 'audio') {
                        await sender.replaceTrack(participant.originalAudioTrack);
                        console.log('[WebRTC:Screen] 원래 마이크 오디오 트랙으로 복원 완료');

                        // 백업 제거
                        delete participant.originalAudioTrack;
                        break;
                    }
                }
            }

            // Web Audio 노드 및 AudioContext 정리
            if (participant.systemSource) {
                try {
                    participant.systemSource.disconnect();
                    delete participant.systemSource;
                } catch (error) {
                    console.error('[WebRTC:Screen] systemSource 정리 중 에러:', error);
                }
            }

            if (participant.micSource) {
                try {
                    participant.micSource.disconnect();
                    delete participant.micSource;
                } catch (error) {
                    console.error('[WebRTC:Screen] micSource 정리 중 에러:', error);
                }
            }

            if (participant.destination) {
                try {
                    participant.destination.disconnect();
                    delete participant.destination;
                } catch (error) {
                    console.error('[WebRTC:Screen] destination 정리 중 에러:', error);
                }
            }

            if (participant.audioContext) {
                try {
                    participant.audioContext.close();
                    console.log('[WebRTC:Screen] AudioContext 정리 완료');
                    delete participant.audioContext;
                } catch (error) {
                    console.error('[WebRTC:Screen] AudioContext 정리 중 에러:', error);
                }
            }
        }

        // 화면 공유 스트림 정리
        await screenHandler.end();

        // 버튼 상태 초기화
        const screenShareBtn = $("#screenShareBtn");
        screenShareBtn.data("flag", false);
        screenShareBtn.attr("src", "/images/webrtc/screen-share-on.svg");

        console.log('[WebRTC:Screen] 화면 공유 중지됨');

        // 녹화 중이라면 원래 마이크 오디오로 자동 전환됩니다
        // (WebRTC를 통해 전송되므로 별도 처리 불필요)
        if (typeof recording !== 'undefined' && recording.isRecordingInProgress) {
            console.log('[WebRTC:Screen] 녹화: 마이크 오디오로 전환됨');
        }

    } catch (error) {
        console.error('[WebRTC:Screen] 중지 실패:', error);
    }
}

/**
 * 화면 공유 토글 함수 (버튼 클릭 시 호출)
 * @returns {Promise<void>}
 */
// 토글 함수는 시작/중지 성공 여부를 순차적으로 반영해야 해서 async/await를 유지한다.
async function screenShare() {
    const screenShareBtn = $("#screenShareBtn");
    const isScreenShare = screenShareBtn.data("flag");

    if (isScreenShare) {
        // 화면 공유 중지
        await stopScreenShare();
    } else {
        // 화면 공유 시작
        await startScreenShare();
        
        // 시작 성공 시 버튼 상태 업데이트
        if (shareView) {
        screenShareBtn.data("flag", true);
            screenShareBtn.attr("src", "/images/webrtc/screen-share-off.svg");
        }
    }
}

// 성능 차트 초기화
function initPerformanceChart() {
    const canvas = document.getElementById('chartCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // 차트 데이터 초기화
    screenShareConfig.chartData = {
        frameRates: Array(30).fill(0),
        bitrates: Array(30).fill(0),
        times: Array(30).fill(0)
    };
    
    // 첫 번째 차트 그리기
    drawPerformanceChart(ctx);
}

// 성능 차트 그리기
function drawPerformanceChart(ctx) {
    const canvas = ctx.canvas;
    const width = canvas.width;
    const height = canvas.height;
    
    // 캔버스 클리어
    ctx.clearRect(0, 0, width, height);
    
    const { frameRates, bitrates } = screenShareConfig.chartData;
    const maxPoints = frameRates.length;
    
    // 배경 그리드
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 4; i++) {
        const y = (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }
    
    // 프레임률 그래프 (녹색)
    ctx.strokeStyle = '#28a745';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < maxPoints; i++) {
        const x = (width / (maxPoints - 1)) * i;
        const y = height - (frameRates[i] / 60) * height; // 60fps 기준
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
    
    // 비트레이트 그래프 (파란색) - 스케일 조정
    ctx.strokeStyle = '#007bff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < maxPoints; i++) {
        const x = (width / (maxPoints - 1)) * i;
        const y = height - (bitrates[i] / 5000) * height; // 5000kbps 기준
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
    
    // 범례
    ctx.fillStyle = '#28a745';
    ctx.fillRect(5, 5, 10, 2);
    ctx.fillStyle = 'white';
    ctx.font = '10px Arial';
    ctx.fillText('FPS', 20, 12);
    
    ctx.fillStyle = '#007bff';
    ctx.fillRect(5, 15, 10, 2);
    ctx.fillStyle = 'white';
    ctx.fillText('Kbps', 20, 22);
}

// 차트 데이터 업데이트
function updateChartData(frameRate, bitrate) {
    if (!screenShareConfig.chartData) return;
    
    // 새 데이터 추가하고 오래된 데이터 제거
    screenShareConfig.chartData.frameRates.push(frameRate);
    screenShareConfig.chartData.frameRates.shift();
    
    screenShareConfig.chartData.bitrates.push(bitrate / 1000); // kbps로 변환
    screenShareConfig.chartData.bitrates.shift();
    
    // 차트 다시 그리기
    const canvas = document.getElementById('chartCanvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        drawPerformanceChart(ctx);
    }
}

// 컨트롤 패널 토글
function toggleScreenShareControls() {
    const controls = document.getElementById('screenShareControls');
    const stats = document.getElementById('screenShareStats');
    const chart = document.getElementById('performanceChart');
    const buttons = controls.querySelector('div:last-child');
    
    if (stats.style.display === 'none') {
        // 확장
        stats.style.display = 'grid';
        chart.style.display = 'block';
        buttons.style.display = 'flex';
        controls.querySelector('button').textContent = '−';
    } else {
        // 축소
        stats.style.display = 'none';
        chart.style.display = 'none';
        buttons.style.display = 'none';
        controls.querySelector('button').textContent = '+';
    }
}

// 상세 통계 모달 표시
function showDetailedStats() {
    const stats = screenShareConfig.stats;
    const deviceStats = devicePerformance.metrics;
    
    const modalHTML = `
        <div id="detailedStatsModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10001;
        ">
            <div style="
                background: white;
                padding: 20px;
                border-radius: 10px;
                max-width: 600px;
                width: 90%;
                max-height: 80%;
                overflow-y: auto;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0;">📊 상세 성능 통계</h3>
                    <button onclick="closeDetailedStats()" style="
                        background: none;
                        border: none;
                        font-size: 20px;
                        cursor: pointer;
                    ">×</button>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <!-- 네트워크 통계 -->
                    <div>
                        <h4>🌐 네트워크 성능</h4>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td>비트레이트</td><td><strong>${Math.round(stats.bitrate)} kbps</strong></td></tr>
                            <tr><td>프레임률</td><td><strong>${Math.round(stats.frameRate)} fps</strong></td></tr>
                            <tr><td>패킷 손실</td><td><strong>${stats.packetsLost}</strong></td></tr>
                            <tr><td>전송된 프레임</td><td><strong>${stats.framesSent || 0}</strong></td></tr>
                            <tr><td>인코딩된 프레임</td><td><strong>${stats.framesEncoded || 0}</strong></td></tr>
                        </table>
                    </div>
                    
                    <!-- 디바이스 통계 -->
                    <div>
                        <h4>💻 디바이스 성능</h4>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td>성능 등급</td><td><strong>${deviceStats.grade || 'medium'}</strong></td></tr>
                            <tr><td>프레임 드롭률</td><td><strong>${Math.round(deviceStats.frameDropRate)}%</strong></td></tr>
                            <tr><td>평균 인코딩 시간</td><td><strong>${Math.round(deviceStats.encodeTime)}ms</strong></td></tr>
                            <tr><td>화질 제한 원인</td><td><strong>${stats.qualityLimitationReason || 'none'}</strong></td></tr>
                        </table>
                    </div>
                </div>
                
                <!-- 히스토리 차트 -->
                <div style="margin-top: 20px;">
                    <h4>📈 성능 히스토리</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center;">
                        <div>
                            <strong>평균 프레임률</strong><br>
                            ${getAverageFromHistory('frameRates')} fps
                        </div>
                        <div>
                            <strong>평균 인코딩 시간</strong><br>
                            ${getAverageFromHistory('encodeTimes')} ms
                        </div>
                        <div>
                            <strong>평균 비트레이트</strong><br>
                            ${getAverageFromHistory('bitrates')} kbps
                        </div>
                    </div>
                </div>
                
                <!-- 최적화 제안 -->
                <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <h4>💡 최적화 제안</h4>
                    <div id="optimizationSuggestions">
                        ${generateOptimizationSuggestions()}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// 히스토리 평균값 계산
function getAverageFromHistory(type) {
    const history = devicePerformance.history[type];
    if (!history || history.length === 0) return 0;
    
    const sum = history.reduce((a, b) => a + b, 0);
    return Math.round(sum / history.length);
}

// 최적화 제안 생성
function generateOptimizationSuggestions() {
    const suggestions = [];
    const stats = screenShareConfig.stats;
    const deviceStats = devicePerformance.metrics;
    
    // 프레임 드롭률 체크
    if (deviceStats.frameDropRate > 10) {
        suggestions.push('⚠️ 프레임 드롭률이 높습니다. CPU 사용량을 줄이거나 화질을 낮춰보세요.');
    }
    
    // 인코딩 시간 체크
    if (deviceStats.encodeTime > 30) {
        suggestions.push('⚠️ 인코딩 시간이 깁니다. 해상도를 낮추거나 다른 프로그램을 종료해보세요.');
    }
    
    // 패킷 손실 체크
    if (stats.packetsLost > 100) {
        suggestions.push('⚠️ 네트워크 패킷 손실이 발생했습니다. 네트워크 연결을 확인해보세요.');
    }
    
    // 프레임률 체크
    if (stats.frameRate < 10) {
        suggestions.push('⚠️ 프레임률이 낮습니다. 자동 최적화를 활성화하거나 화질을 낮춰보세요.');
    }
    
    // 비트레이트 체크
    if (stats.bitrate < 500) {
        suggestions.push('ℹ️ 낮은 비트레이트로 전송 중입니다. 네트워크 대역폭이 제한될 수 있습니다.');
    }
    
    if (suggestions.length === 0) {
        suggestions.push('✅ 현재 화면 공유가 최적 상태로 동작하고 있습니다.');
    }
    
    return suggestions.map(suggestion => `<div style="margin: 5px 0;">${suggestion}</div>`).join('');
}

// 상세 통계 모달 닫기
function closeDetailedStats() {
    const modal = document.getElementById('detailedStatsModal');
    if (modal) {
        modal.remove();
    }
}

// 성능 경고 시스템
function checkPerformanceWarnings() {
    const stats = screenShareConfig.stats;
    const deviceStats = devicePerformance.metrics;
    const warnings = [];
    
    // 심각한 성능 문제 감지
    if (deviceStats.frameDropRate > 20) {
        warnings.push({
            type: 'critical',
            message: '심각한 프레임 드롭 발생',
            suggestion: '화질을 낮추거나 다른 프로그램을 종료하세요.'
        });
    }
    
    if (stats.frameRate < 5) {
        warnings.push({
            type: 'critical',
            message: '매우 낮은 프레임률',
            suggestion: '네트워크 연결을 확인하고 화질을 낮춰보세요.'
        });
    }
    
    if (stats.packetsLost > 500) {
        warnings.push({
            type: 'warning',
            message: '네트워크 불안정',
            suggestion: '네트워크 연결을 확인해보세요.'
        });
    }
    
    // 경고 표시
    if (warnings.length > 0) {
        showPerformanceWarning(warnings[0]);
    }
}

// 성능 경고 표시
function showPerformanceWarning(warning) {
    // 기존 경고가 있으면 제거
    const existingWarning = document.getElementById('performanceWarning');
    if (existingWarning) {
        existingWarning.remove();
    }
    
    const warningColor = warning.type === 'critical' ? '#dc3545' : '#ffc107';
    const warningIcon = warning.type === 'critical' ? '🚨' : '⚠️';
    
    const warningHTML = `
        <div id="performanceWarning" style="
            position: fixed;
            top: 80px;
            right: 10px;
            background: ${warningColor};
            color: white;
            padding: 10px;
            border-radius: 6px;
            font-size: 12px;
            z-index: 10000;
            max-width: 250px;
            animation: slideIn 0.3s ease;
        ">
            <div style="font-weight: bold; margin-bottom: 4px;">
                ${warningIcon} ${warning.message}
            </div>
            <div style="font-size: 11px; opacity: 0.9;">
                ${warning.suggestion}
            </div>
            <button onclick="this.parentElement.remove()" style="
                position: absolute;
                top: 2px;
                right: 4px;
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 14px;
            ">×</button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', warningHTML);
    
    // 10초 후 자동 제거
    setTimeout(() => {
        const warning = document.getElementById('performanceWarning');
        if (warning) {
            warning.remove();
        }
    }, 10000);
}

// ========== 화면 공유 UI 개선 시스템 ==========

// UI 상태 관리
const screenShareUI = {
    isDragging: false,
    dragOffset: { x: 0, y: 0 },
    isMinimalMode: false,
    keyboardShortcutsEnabled: true,
    currentTheme: 'dark' // 'dark', 'light', 'auto'
};

// CSS 스타일 주입
function injectAdvancedStyles() {
    const styleId = 'screenShareAdvancedStyles';
    if (document.getElementById(styleId)) return;
    
    const styles = `
        <style id="${styleId}">
            /* 키프레임 애니메이션 */
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            
            @keyframes glow {
                0%, 100% { box-shadow: 0 0 5px rgba(255, 255, 255, 0.5); }
                50% { box-shadow: 0 0 20px rgba(255, 255, 255, 0.8), 0 0 30px rgba(0, 123, 255, 0.6); }
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-5px); }
                75% { transform: translateX(5px); }
            }
            
            /* 화면 공유 컨트롤 기본 스타일 */
            .screen-share-controls {
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                user-select: none;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .screen-share-controls:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
            }
            
            .screen-share-controls.dragging {
                transform: rotate(3deg) scale(1.05);
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);
                z-index: 10001 !important;
            }
            
            .screen-share-controls.minimal {
                min-width: 120px !important;
                padding: 8px !important;
            }
            
            /* 빠른 품질 버튼 */
            .quality-btn {
                background: linear-gradient(45deg, #333, #555);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 6px 10px;
                border-radius: 20px;
                font-size: 10px;
                cursor: pointer;
                transition: all 0.2s ease;
                position: relative;
                overflow: hidden;
            }
            
            .quality-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            }
            
            .quality-btn.active {
                background: linear-gradient(45deg, #28a745, #20c997);
                animation: glow 2s infinite;
            }
            
            .quality-btn:before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 0.5s;
            }
            
            .quality-btn:hover:before {
                left: 100%;
            }
            
            /* 화면 공유 상태 오버레이 */
            .screen-share-overlay {
                position: absolute;
                top: 10px;
                left: 10px;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                z-index: 1000;
                animation: slideIn 0.5s ease;
                border-left: 4px solid #007bff;
            }
            
            .screen-share-overlay.recording {
                border-left-color: #dc3545;
                animation: pulse 1.5s infinite;
            }
            
            /* 드래그 핸들 */
            .drag-handle {
                cursor: move;
                padding: 4px;
                text-align: center;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                margin-bottom: 6px;
                transition: background 0.2s ease;
            }
            
            .drag-handle:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            
            .drag-handle:active {
                background: rgba(255, 255, 255, 0.3);
            }
            
            /* 키보드 단축키 힌트 */
            .keyboard-hint {
                position: fixed;
                bottom: 10px;
                right: 10px;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-size: 11px;
                z-index: 9998;
                opacity: 0;
                transition: opacity 0.3s ease;
                max-width: 200px;
            }
            
            .keyboard-hint.show {
                opacity: 1;
            }
            
            /* 토스트 알림 개선 */
            .toast-notification {
                position: fixed;
                top: 50px;
                right: 10px;
                background: linear-gradient(45deg, #007bff, #0056b3);
                color: white;
                padding: 12px 16px;
                border-radius: 8px;
                font-size: 13px;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
                animation: slideIn 0.3s ease;
                max-width: 300px;
                border-left: 4px solid #ffc107;
            }
            
            .toast-notification.success {
                background: linear-gradient(45deg, #28a745, #20c997);
                border-left-color: #17a2b8;
            }
            
            .toast-notification.warning {
                background: linear-gradient(45deg, #ffc107, #e0a800);
                border-left-color: #dc3545;
            }
            
            .toast-notification.error {
                background: linear-gradient(45deg, #dc3545, #c82333);
                border-left-color: #6f42c1;
            }
            
            /* 테마 관련 스타일 */
            .theme-light .screen-share-controls {
                background: rgba(255, 255, 255, 0.95) !important;
                color: #333 !important;
                border-color: rgba(0, 0, 0, 0.2) !important;
            }
            
            .theme-light .quality-btn {
                background: linear-gradient(45deg, #f8f9fa, #e9ecef);
                color: #333;
                border-color: rgba(0, 0, 0, 0.2);
            }
        </style>
    `;
    
    document.head.insertAdjacentHTML('beforeend', styles);
}

// 향상된 화면 공유 컨트롤 UI 표시
function showScreenShareControls() {
    // 스타일 주입
    injectAdvancedStyles();
    
    // 컨트롤 패널이 없으면 생성
    if (!document.getElementById('screenShareControls')) {
        const controlsHTML = `
            <div id="screenShareControls" class="screen-share-controls" style="
                position: fixed;
                top: 10px;
                right: 10px;
                background: rgba(0,0,0,0.95);
                color: white;
                padding: 14px;
                border-radius: 12px;
                font-size: 12px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                min-width: 300px;
                max-width: 350px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.4);
                backdrop-filter: blur(15px);
            ">
                <!-- 드래그 핸들 -->
                <div class="drag-handle" title="드래그하여 이동">
                    <span style="color: #888;">⋮⋮⋮</span>
                </div>
                
                <!-- 헤더 -->
                <div style="
                    font-weight: bold; 
                    text-align: center; 
                    padding-bottom: 10px; 
                    border-bottom: 1px solid rgba(255,255,255,0.2);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <span>🖥️ 화면 공유 컨트롤</span>
                    <div style="display: flex; gap: 4px;">
                        <button onclick="toggleMinimalMode()" title="미니멀 모드" style="
                            background: none;
                            border: none;
                            color: white;
                            cursor: pointer;
                            font-size: 14px;
                            padding: 2px;
                            opacity: 0.7;
                            border-radius: 3px;
                        ">📱</button>
                        <button onclick="showKeyboardShortcuts()" title="단축키 보기" style="
                            background: none;
                            border: none;
                            color: white;
                            cursor: pointer;
                            font-size: 14px;
                            padding: 2px;
                            opacity: 0.7;
                            border-radius: 3px;
                        ">⌨️</button>
                        <button onclick="toggleScreenShareControls()" style="
                            background: none;
                            border: none;
                            color: white;
                            cursor: pointer;
                            font-size: 16px;
                            padding: 0;
                            opacity: 0.7;
                        ">−</button>
                    </div>
                </div>
                
                <!-- 빠른 품질 변경 버튼 -->
                <div id="quickQualityButtons" style="
                    display: flex;
                    gap: 6px;
                    justify-content: center;
                    margin: 4px 0;
                ">
                    <button onclick="quickQualityChange('high')" class="quality-btn" id="qualityBtnHigh">
                        🟢 고화질
                    </button>
                    <button onclick="quickQualityChange('medium')" class="quality-btn active" id="qualityBtnMedium">
                        🟡 중화질
                    </button>
                    <button onclick="quickQualityChange('low')" class="quality-btn" id="qualityBtnLow">
                        🔴 저화질
                    </button>
                </div>
                
                <!-- 현재 상태 -->
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>현재 화질:</span>
                    <span id="screenShareQuality" style="font-weight: bold;">🔄 자동</span>
                </div>
                
                <!-- 실시간 통계 -->
                <div id="screenShareStats" style="
                    background: rgba(255,255,255,0.1);
                    padding: 10px;
                    border-radius: 8px;
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 6px;
                    font-size: 11px;
                ">
                    <div class="stats-item">📊 0 kbps</div>
                    <div class="stats-item">🎞️ 0 fps</div>
                    <div class="stats-item">📉 0 lost</div>
                    <div class="stats-item">⚡ 0ms</div>
                </div>
                
                <!-- 성능 차트 -->
                <div id="performanceChart" style="
                    height: 70px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 8px;
                    position: relative;
                    overflow: hidden;
                ">
                    <canvas id="chartCanvas" width="280" height="70" style="display: block;"></canvas>
                </div>
                
                <!-- 네트워크 및 디바이스 상태 -->
                <div style="display: flex; justify-content: space-between; font-size: 11px;">
                    <div>
                        <span style="opacity: 0.8;">네트워크:</span>
                        <span id="networkStatus">🟡 중간</span>
                    </div>
                    <div>
                        <span style="opacity: 0.8;">디바이스:</span>
                        <span id="deviceStatus">🟡 중간</span>
                    </div>
                </div>
                
                <!-- 컨트롤 버튼 -->
                <div style="display: flex; gap: 6px; margin-top: 6px;">
                    <button onclick="toggleAutoOptimize()" id="autoOptimizeBtn" style="
                        background: #28a745;
                        color: white;
                        border: none;
                        padding: 6px 10px;
                        border-radius: 6px;
                        font-size: 10px;
                        cursor: pointer;
                        flex: 1;
                        transition: all 0.2s ease;
                    ">자동 최적화</button>
                    <button onclick="oneClickOptimize()" style="
                        background: #007bff;
                        color: white;
                        border: none;
                        padding: 6px 10px;
                        border-radius: 6px;
                        font-size: 10px;
                        cursor: pointer;
                        flex: 1;
                        transition: all 0.2s ease;
                    ">⚡ 원클릭 최적화</button>
                    <button onclick="showDetailedStats()" style="
                        background: #6f42c1;
                        color: white;
                        border: none;
                        padding: 6px 10px;
                        border-radius: 6px;
                        font-size: 10px;
                        cursor: pointer;
                        transition: all 0.2s ease;
                    ">📊</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', controlsHTML);
        
        // 차트 초기화
        initPerformanceChart();
        
        // 드래그 기능 초기화
        makePanelDraggable();
        
        // 키보드 단축키 초기화
        initKeyboardShortcuts();
        
        // 화면 공유 상태 오버레이 표시
        showScreenShareOverlay();
    }
    
    document.getElementById('screenShareControls').style.display = 'flex';
    resumeScreenShareMonitoring();
}

// 패널을 드래그 가능하게 만들기
function makePanelDraggable() {
    const panel = document.getElementById('screenShareControls');
    const dragHandle = panel.querySelector('.drag-handle');
    
    if (!panel || !dragHandle) return;
    
    dragHandle.addEventListener('mousedown', startDrag);
    
    function startDrag(e) {
        e.preventDefault();
        screenShareUI.isDragging = true;
        
        const rect = panel.getBoundingClientRect();
        screenShareUI.dragOffset.x = e.clientX - rect.left;
        screenShareUI.dragOffset.y = e.clientY - rect.top;
        
        panel.classList.add('dragging');
        
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', stopDrag);
        
        // 드래그 시작 시 선택 방지
        document.body.style.userSelect = 'none';
    }
    
    function drag(e) {
        if (!screenShareUI.isDragging) return;
        
        e.preventDefault();
        
        let newX = e.clientX - screenShareUI.dragOffset.x;
        let newY = e.clientY - screenShareUI.dragOffset.y;
        
        // 화면 경계 제한
        const maxX = window.innerWidth - panel.offsetWidth;
        const maxY = window.innerHeight - panel.offsetHeight;
        
        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));
        
        panel.style.left = newX + 'px';
        panel.style.top = newY + 'px';
        panel.style.right = 'auto';
    }
    
    function stopDrag() {
        screenShareUI.isDragging = false;
        panel.classList.remove('dragging');
        
        document.removeEventListener('mousemove', drag);
        document.removeEventListener('mouseup', stopDrag);
        
        // 선택 복원
        document.body.style.userSelect = '';
        
        // 위치 저장 (로컬 스토리지)
        localStorage.setItem('screenShareControlsPosition', JSON.stringify({
            left: panel.style.left,
            top: panel.style.top
        }));
    }
    
    // 저장된 위치 복원
    const savedPosition = localStorage.getItem('screenShareControlsPosition');
    if (savedPosition) {
        try {
            const position = JSON.parse(savedPosition);
            if (position.left && position.top) {
                panel.style.left = position.left;
                panel.style.top = position.top;
                panel.style.right = 'auto';
            }
        } catch (e) {
            console.warn('화면 공유 컨트롤 위치 복원 실패:', e);
        }
    }
}

// 빠른 품질 변경
function quickQualityChange(quality) {
    // 기존 활성 버튼 비활성화
    document.querySelectorAll('.quality-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 새 버튼 활성화
    const targetBtn = document.getElementById(`qualityBtn${quality.charAt(0).toUpperCase() + quality.slice(1)}`);
    if (targetBtn) {
        targetBtn.classList.add('active');
    }
    
    // 품질 변경 실행
    changeScreenShareQuality(quality);
    
    // 피드백 토스트
    showToast(`화질을 ${getQualityLabel(quality)}로 변경했습니다.`, 'success');
}

// 품질 라벨 가져오기
function getQualityLabel(quality) {
    const labels = {
        'high': '고화질',
        'medium': '중화질',
        'low': '저화질',
        'auto': '자동'
    };
    return labels[quality] || quality;
}

// 키보드 단축키 초기화
function initKeyboardShortcuts() {
    if (!screenShareUI.keyboardShortcutsEnabled) return;
    
    document.addEventListener('keydown', handleKeyboardShortcut);
}

// 키보드 단축키 처리
function handleKeyboardShortcut(e) {
    if (!shareView) return; // 화면 공유 중이 아니면 무시
    
    // Ctrl + Shift 조합 확인
    if (e.ctrlKey && e.shiftKey) {
        switch (e.key.toLowerCase()) {
            case 'q': // 품질 변경 사이클
                e.preventDefault();
                cycleQuality();
                break;
            case 's': // 통계 토글
                e.preventDefault();
                showDetailedStats();
                break;
            case 'm': // 미니멀 모드 토글
                e.preventDefault();
                toggleMinimalMode();
                break;
            case 'o': // 원클릭 최적화
                e.preventDefault();
                oneClickOptimize();
                break;
            case 'h': // 도움말 표시
                e.preventDefault();
                showKeyboardShortcuts();
                break;
        }
    }
}

// 품질 순환 변경
function cycleQuality() {
    const qualities = ['low', 'medium', 'high'];
    const currentIndex = qualities.indexOf(screenShareConfig.currentQuality);
    const nextIndex = (currentIndex + 1) % qualities.length;
    const nextQuality = qualities[nextIndex];
    
    quickQualityChange(nextQuality);
}

// 키보드 단축키 도움말 표시
function showKeyboardShortcuts() {
    const existingHint = document.getElementById('keyboardHint');
    if (existingHint) {
        existingHint.remove();
        return;
    }
    
    const hintHTML = `
        <div id="keyboardHint" class="keyboard-hint show">
            <div style="font-weight: bold; margin-bottom: 8px;">⌨️ 키보드 단축키</div>
            <div style="line-height: 1.4;">
                <div><kbd>Ctrl+Shift+Q</kbd> 품질 변경</div>
                <div><kbd>Ctrl+Shift+S</kbd> 상세 통계</div>
                <div><kbd>Ctrl+Shift+M</kbd> 미니멀 모드</div>
                <div><kbd>Ctrl+Shift+O</kbd> 원클릭 최적화</div>
                <div><kbd>Ctrl+Shift+H</kbd> 이 도움말</div>
            </div>
            <div style="text-align: center; margin-top: 8px;">
                <button onclick="this.closest('#keyboardHint').remove()" style="
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    cursor: pointer;
                ">닫기</button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', hintHTML);
    
    // 10초 후 자동 제거
    setTimeout(() => {
        const hint = document.getElementById('keyboardHint');
        if (hint) {
            hint.classList.remove('show');
            setTimeout(() => hint.remove(), 300);
        }
    }, 10000);
}

// 화면 공유 상태 오버레이 표시
function showScreenShareOverlay() {
    // 사용자의 비디오 엘리먼트 찾기
    const userVideo = document.querySelector(`video[id*="${userId}"]`);
    if (!userVideo) return;
    
    const container = userVideo.parentElement;
    if (!container) return;
    
    // 기존 오버레이 제거
    const existingOverlay = container.querySelector('.screen-share-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }
    
    // 새 오버레이 생성
    const overlayHTML = `
        <div class="screen-share-overlay recording">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="animation: pulse 1s infinite;">🔴</span>
                <span style="font-weight: bold;">화면 공유 중</span>
            </div>
            <div style="font-size: 10px; opacity: 0.9; margin-top: 2px;">
                <span id="shareTime">00:00</span> | 
                <span id="shareQuality">${getQualityLabel(screenShareConfig.currentQuality)}</span>
            </div>
        </div>
    `;
    
    container.style.position = 'relative';
    container.insertAdjacentHTML('beforeend', overlayHTML);
    
    // 시간 업데이트 시작
    startShareTimeCounter();
}

// 화면 공유 시간 카운터
let shareStartTime = null;
let shareTimeInterval = null;

function startShareTimeCounter() {
    shareStartTime = Date.now();
    
    if (shareTimeInterval) {
        clearInterval(shareTimeInterval);
    }
    
    shareTimeInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - shareStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        const timeElement = document.getElementById('shareTime');
        if (timeElement) {
            timeElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

// 미니멀 모드 토글
function toggleMinimalMode() {
    const controls = document.getElementById('screenShareControls');
    if (!controls) return;
    
    screenShareUI.isMinimalMode = !screenShareUI.isMinimalMode;
    
    if (screenShareUI.isMinimalMode) {
        // 미니멀 모드 활성화
        controls.classList.add('minimal');
        
        // 불필요한 요소들 숨기기
        const hideElements = [
            '#screenShareStats',
            '#performanceChart',
            '#quickQualityButtons div:last-child',
            '.drag-handle'
        ];
        
        hideElements.forEach(selector => {
            const element = controls.querySelector(selector);
            if (element) {
                element.style.display = 'none';
            }
        });
        
        // 헤더 텍스트 변경
        const header = controls.querySelector('div:nth-child(2) span');
        if (header) {
            header.textContent = '🖥️ 화면공유';
        }
        
        showToast('미니멀 모드가 활성화되었습니다.', 'info');
    } else {
        // 미니멀 모드 비활성화
        controls.classList.remove('minimal');
        
        // 요소들 다시 표시
        const showElements = [
            '#screenShareStats',
            '#performanceChart',
            '#quickQualityButtons div:last-child',
            '.drag-handle'
        ];
        
        showElements.forEach(selector => {
            const element = controls.querySelector(selector);
            if (element) {
                element.style.display = '';
            }
        });
        
        // 헤더 텍스트 복원
        const header = controls.querySelector('div:nth-child(2) span');
        if (header) {
            header.textContent = '🖥️ 화면 공유 컨트롤';
        }
        
        showToast('미니멀 모드가 비활성화되었습니다.', 'info');
    }
}

// 원클릭 최적화
function oneClickOptimize() {
    showToast('최적화를 진행하고 있습니다...', 'info');

    return collectScreenShareStatsSnapshot().then(function (snapshot) {
        const networkQuality = calculateNetworkQualityFromSnapshot(snapshot);
        const deviceQuality = updateDevicePerformanceFromSnapshot(snapshot);
        const optimalQuality = selectOptimalQuality(networkQuality, deviceQuality);

        console.log(`품질 결정: 네트워크(${networkQuality}) + 디바이스(${deviceQuality}) = ${optimalQuality}`);
        return {
            networkQuality,
            deviceQuality,
            optimalQuality
        };
    }).then(function (qualities) {
        const networkQuality = qualities.networkQuality;
        const deviceQuality = qualities.deviceQuality;
        const optimalQuality = qualities.optimalQuality;

        const applyQualityChange = optimalQuality !== screenShareConfig.currentQuality
            ? changeScreenShareQuality(optimalQuality).then(function () {
                quickQualityChange(optimalQuality);
            })
            : Promise.resolve();

        return applyQualityChange.then(function () {
            if (!screenShareConfig.autoOptimize) {
                toggleAutoOptimize();
            }

            const resultMessage = `최적화 완료!\n네트워크: ${getQualityLabel(networkQuality)}\n디바이스: ${getQualityLabel(deviceQuality)}\n적용된 화질: ${getQualityLabel(optimalQuality)}`;
            showToast(resultMessage, 'success');

            console.log('원클릭 최적화 완료:', {
                networkQuality,
                deviceQuality,
                optimalQuality
            });
        });
    }).catch(function (error) {
        console.error('원클릭 최적화 실패:', error);
        showToast('최적화 중 오류가 발생했습니다.', 'error');
    });
}

// 향상된 토스트 알림
function showToast(message, type = 'info', duration = 3000) {
    // 기존 토스트 제거
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toastHTML = `
        <div class="toast-notification ${type}">
            <div style="font-weight: bold; margin-bottom: 4px;">
                ${getToastIcon(type)} ${getToastTitle(type)}
            </div>
            <div style="font-size: 12px; opacity: 0.95; line-height: 1.3;">
                ${message.replace(/\n/g, '<br>')}
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', toastHTML);
    
    const toast = document.querySelector('.toast-notification');
    
    // 자동 제거
    setTimeout(() => {
        if (toast && toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }, duration);
    
    // 클릭으로 닫기
    toast.addEventListener('click', () => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    });
}

// 토스트 아이콘 및 제목
function getToastIcon(type) {
    const icons = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌'
    };
    return icons[type] || 'ℹ️';
}

function getToastTitle(type) {
    const titles = {
        'info': '정보',
        'success': '성공',
        'warning': '주의',
        'error': '오류'
    };
    return titles[type] || '알림';
}

// 화면 공유 컨트롤 UI 숨기기 (오버라이드)
function hideScreenShareControls() {
    pauseScreenShareMonitoring();

    const controls = document.getElementById('screenShareControls');
    if (controls) {
        controls.style.display = 'none';
    }
    
    // 키보드 단축키 제거
    document.removeEventListener('keydown', handleKeyboardShortcut);
    
    // 시간 카운터 정리
    if (shareTimeInterval) {
        clearInterval(shareTimeInterval);
        shareTimeInterval = null;
    }
    
    // 화면 공유 오버레이 제거
    document.querySelectorAll('.screen-share-overlay').forEach(overlay => {
        overlay.remove();
    });
}
