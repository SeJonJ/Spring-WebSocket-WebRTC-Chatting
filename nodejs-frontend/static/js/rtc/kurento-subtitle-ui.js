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

// ===== 자막 기능 관련 함수들 =====

/**
 * 자막 UI 초기화
 */
function initSubtitleUI() {
    // SpeechRecognitionManager 상태 변경 이벤트 리스너
    document.addEventListener('speechRecognitionStatusChanged', function(event) {
        updateSubtitleButtonUI(event.detail);
    });
    
    // 초기 상태 설정
    updateSubtitleButtonUI({
        status: 'stopped',
        isEnabled: false,
        isRecognizing: false,
        isElectronBlocked: false,
        canManualRetry: false
    });
}

/**
 * 자막 토글 함수
 */
function toggleSubtitle() {
    try {
        const isEnabled = toggleSpeechRecognition();
        console.log('자막 기능 토글:', isEnabled ? '켜짐' : '꺼짐');
        
        // 사용자에게 피드백 제공
        if (isEnabled) {
            showToast('실시간 자막이 시작되었습니다', 'success');
        } else {
            showToast('실시간 자막이 중지되었습니다', 'info');
        }
        
    } catch (error) {
        console.error('자막 토글 실패:', error);
        showToast('자막 기능을 사용할 수 없습니다', 'error');
    }
}

/**
 * 자막 버튼 UI 업데이트
 */
function updateSubtitleButtonUI(status) {
    const $subtitleBtn = $('#subtitleBtn')[0];
    if (!$subtitleBtn) return;
    
    const { isEnabled, isRecognizing, status: currentStatus, isElectronBlocked, canManualRetry } = status;
    
    // 버튼 상태 업데이트
    $subtitleBtn.setAttribute('data-flag', isEnabled.toString());
    
    // 아이콘 변경
    if (isEnabled) {
        $subtitleBtn.src = 'images/webrtc/subtitle-on.svg';
        $subtitleBtn.title = '실시간 자막 (켜짐)';
    } else {
        $subtitleBtn.src = 'images/webrtc/subtitle-off.svg';
        $subtitleBtn.title = '실시간 자막 (꺼짐)';
    }
    
    // 상태에 따른 시각적 피드백
    $subtitleBtn.style.opacity = isEnabled ? '1.0' : '0.6';
    
    // 인식 중일 때 애니메이션 효과
    if (isRecognizing) {
        $subtitleBtn.style.animation = 'pulse 1.5s infinite';
    } else {
        $subtitleBtn.style.animation = 'none';
    }
    
    // 에러 상태 처리
    if (currentStatus === 'error' || currentStatus === 'permission-denied') {
        $subtitleBtn.style.opacity = '0.4';
        $subtitleBtn.title = '자막 기능 오류';
    } else if (currentStatus === 'unsupported' || isElectronBlocked) {
        $subtitleBtn.style.opacity = canManualRetry === false ? '0.4' : '0.6';
        $subtitleBtn.title = 'Electron 음성 인식 불안정 - 수동 재시도 가능';
    }
}

/**
 * 브라우저 지원 여부 확인 및 사용자 알림
 */
function checkSubtitleSupport() {
    const status = getSpeechRecognitionStatus();
    
    if (!status.isSupported) {
        showToast('이 브라우저는 음성 인식을 지원하지 않습니다', 'warning');
        return false;
    }
    
    return true;
}
