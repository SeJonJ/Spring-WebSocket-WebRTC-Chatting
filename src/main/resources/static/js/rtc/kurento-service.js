/*
 * (C) Copyright 2014 Kurento (http://kurento.org/)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Modified By : SeJonJnag <wkdtpwhs@gmail.com>
 *
 */

// var script = document.createElement('script');
// script.src = "https://code.jquery.com/jquery-3.6.1.min.js";
// document.head.appendChild(script);

// websocket 연결 확인 후 register() 실행
var ws = new WebSocket('wss://' + location.host + '/signal');
ws.onopen = () => {
    register();
}

console.log("location.host : "+location.host)
var participants = {};

let name = null;
let roomId = null;
let roomName = null;

let sendButton = null;
let dataChannelSend = null;
let dataChannelReceive = null;

const constraints = {
    // 'volume', 'channelCount', 'echoCancellation', 'autoGainControl', 'noiseSuppression', 'latency', 'sampleSize', 'sampleRate'
    audio: {
        autoGainControl: false,
        channelCount: 2,
        echoCancellation: false,
        latency: 0,
        noiseSuppression: false,
        sampleRate: 48000,
        sampleSize: 16,
        volume: 1.0
    },
    video: {
        width: 1200,
        height: 1000,
        maxFrameRate: 50,
        minFrameRate: 40
    }
};

// 웹 종료 시 실행
window.onbeforeunload = function () {
    ws.close();
};

$(function () {

    sendButton = $('#sendButton');
    dataChannelSend = $('#dataChannelSend');
    dataChannelReceive = $('#dataChannelReceive');


});

ws.onmessage = function (message) {
    var parsedMessage = JSON.parse(message.data);
    // console.info('Received message: ' + message.data);

    switch (parsedMessage.id) {
        case 'existingParticipants':
            onExistingParticipants(parsedMessage);
            break;
        case 'newParticipantArrived':
            onNewParticipant(parsedMessage);
            break;
        case 'participantLeft':
            onParticipantLeft(parsedMessage);
            break;
        case 'receiveVideoAnswer':
            receiveVideoResponse(parsedMessage);
            break;
        case 'iceCandidate':
            participants[parsedMessage.name].rtcPeer.addIceCandidate(parsedMessage.candidate, function (error) {
                if (error) {
                    console.error("Error adding candidate: " + error);
                    return;
                }
            });
            break;
        default:
            console.error('Unrecognized message', parsedMessage);
    }
}

function register() {

    name = $("#uuid").val();
    roomId = $("#roomId").val();
    roomName = $("#roomName").val();

    document.getElementById('room-header').innerText = 'ROOM ' + roomName;
    document.getElementById('room').style.display = 'block';


    var message = {
        id: 'joinRoom',
        name: $("#uuid").val(),
        room: roomId,
    }
    sendMessage(message);
}

function onNewParticipant(request) {
    receiveVideo(request.name);
}

function receiveVideoResponse(result) {
    participants[result.name].rtcPeer.processAnswer(result.sdpAnswer, function (error) {
        if (error) return console.error(error);
    });
}

function callResponse(message) {
    if (message.response != 'accepted') {
        console.info('Call not accepted by peer. Closing call');
        stop();
    } else {
        webRtcPeer.processAnswer(message.sdpAnswer, function (error) {
            if (error) return console.error(error);
        });
    }
}
const onMessage = (event) => {
    console.log('Received message: ' + event.data);

    // for (var participantName in participants) {
    //     if (participants.hasOwnProperty(participantName) && participantName !== name) {
    //         participants[participantName].rtcPeer.dataChannel.send(event.data);
    //     }
    // }
};

const onOpen = (participant) => {
    console.log('Data channel opened');

};

const onClosed = () => {
    console.log('Data channel closed');
};

const onbufferedamountlow = () => {
    console.log('Data channel buffered amount low');
};

const onError = (error) => {
    console.error("Data channel error: ",error);
};

// TODO: 여기도 수정해야함
function onExistingParticipants(msg) {
    console.log(name + " registered in room " + roomId);
    var participant = new Participant(name);
    participants[name] = participant;
    var video = participant.getVideoElement();

    var options = {
        localVideo: video,
        mediaConstraints: constraints,
        onicecandidate: participant.onIceCandidate.bind(participant),
        dataChannels : true,
        dataChannelConfig: {
            onmessage : onMessage,
            onopen : () => onOpen(participant),
            onclose : onClosed,
            onbufferedamountlow : onbufferedamountlow,
            onerror : onError
        }
    }

    participant.rtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerSendrecv(options,
        function (error) {
            if (error) {
                return console.error(error);
            }

            this.generateOffer(participant.offerToReceiveVideo.bind(participant));

        });


    msg.data.forEach(sender => receiveVideo(sender));
}

function receiveVideo(sender) {
    var participant = new Participant(sender);
    participants[sender] = participant;
    var video = participant.getVideoElement();

    var options = {
        remoteVideo: video,
        onicecandidate: participant.onIceCandidate.bind(participant)
    }

    participant.rtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerSendrecv(options,
        function (error) {
            if (error) {
                return console.error(error);
            }

            this.generateOffer(participant.offerToReceiveVideo.bind(participant));

        });
}

function leaveRoom() {
    sendMessage({
        id: 'leaveRoom'
    });

    for (var key in participants) {
        participants[key].dispose();
    }

    ws.close();

    location.replace("/");
}


function onParticipantLeft(request) {
    console.log('Participant ' + request.name + ' left');
    var participant = participants[request.name];
    participant.dispose();
    delete participants[request.name];
}

function sendMessage(message) {
    var jsonMessage = JSON.stringify(message);
    console.log('Sending message: ' + jsonMessage);
    ws.send(jsonMessage);
}


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
        if (navigator.mediaDevices.getDisplayMedia) {
            return navigator.mediaDevices.getDisplayMedia({video: true});
        } else if (navigator.getDisplayMedia) {
            return navigator.getDisplayMedia({video: true});
        } else {
            throw new Error('Screen sharing not supported in this browser');
        }
    }

    /**
     * 화면 공유를 시작합니다.
     * @returns {Promise<MediaStream>} 화면 공유에 사용되는 미디어 스트림을 반환합니다.
     */
    async function start() {
        try {
            shareView = await getCrossBrowserScreenCapture();
        } catch (err) {
            // console.log('Error getDisplayMedia', err);
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
        }
    }

    // 생성자로 반환할 public 변수 선언
    this.start = start;
    this.end = end;
}

/**
 * 스크린 API를 호출하여 원격 화면을 화면 공유 화면으로 교체합니다.
 * @returns {Promise<void>}
 */
async function startScreenShare() {
    await screenHandler.start(); // 화면 공유를 위해 ScreenHandler.start() 함수 호출

    let participant = participants[name];
    let video = participant.getVideoElement();
    participant.setLocalSteam(video.srcObject);
    video.srcObject = shareView; // 본인의 화면에 화면 공유 화면 표시

    await participant.rtcPeer.peerConnection.getSenders().forEach(sender => {
        // 원격 참가자에게도 화면 공유 화면을 전송하도록 RTCRtpSender.replaceTrack() 함수 호출
        if (sender.track.kind === 'video') {
            sender.replaceTrack(shareView.getVideoTracks()[0]);
        }
    });

    // 원격 화면의 화면 공유가 종료되는 경우
    shareView.getVideoTracks()[0].addEventListener("ended", () => {
        stopScreenShare();
    })
}

/**
 * 화면 공유를 중지하고 기존 화상채팅으로 복원합니다.
 * @returns {Promise<void>}
 */
async function stopScreenShare() {
    await screenHandler.end(); // 화면 공유를 중지하기 위해 ScreenHandler.end() 함수 호출
    let participant = participants[name];
    let video = participant.getVideoElement();
    video.srcObject = participant.getLocalStream(); // 본인의 화면을 원래의 원격 화면으로 복원

    await participant.rtcPeer.peerConnection.getSenders().forEach(sender => {
        // 원격 참가자에게도 화면 공유를 중지하도록 RTCRtpSender.replaceTrack() 함수 호출
        if (sender.track.kind === 'video') {
            sender.replaceTrack(participant.getLocalStream().getVideoTracks()[0]);
        }
    });

// 화면 공유 버튼을 초기화
    let screenShareBtn = $("#screenShareBtn");
    screenShareBtn.val("Share Screen");
    screenShareBtn.data("flag", false);
}

/**

 화면 공유 버튼을 누르면 화면 공유를 시작하거나 중지합니다.

 @returns {Promise<void>}
 */
async function screenShare() {
    let screenShareBtn = $("#screenShareBtn");
    let isScreenShare = screenShareBtn.data("flag");

    if (isScreenShare) { // 이미 화면 공유 중인 경우
        await stopScreenShare(); // 화면 공유 중지
        screenShareBtn.val("Share Screen"); // 버튼 텍스트 초기화
        screenShareBtn.data("flag", false);
    } else { // 화면 공유 중이 아닌 경우
        await startScreenShare(); // 화면 공유 시작
        screenShareBtn.val("Stop Sharing"); // 버튼 텍스트 변경
        screenShareBtn.data("flag", true);
    }
}