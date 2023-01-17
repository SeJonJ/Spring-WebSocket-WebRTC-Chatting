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
 */

// var script = document.createElement('script');
// script.src = "https://code.jquery.com/jquery-3.6.1.min.js";
// document.head.appendChild(script);

// websocket 연결 확인 후 register() 실행
var ws = new WebSocket('wss://' + location.host + '/signal');
ws.onopen = () => {
    register();
}

// console.log("location.host : "+location.host)
var participants = {};

let name = null;
let roomId = null;

// 웹 종료 시 실행
window.onbeforeunload = function () {
    ws.close();
};

ws.onmessage = function (message) {
    var parsedMessage = JSON.parse(message.data);
    console.info('Received message: ' + message.data);

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

    document.getElementById('room-header').innerText = 'ROOM ' + roomId;
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

function onExistingParticipants(msg) {
    var constraints = {
        audio: {
            echoCancellation: true,
            noiseSuppression: true,
            sampleRate: 44100
        },
        video: {
            mandatory: {
                maxWidth: 600,
                maxHeight: 600,
                maxFrameRate: 30,
                minFrameRate: 30
            }
        }
    };
    console.log(name + " registered in room " + roomId);
    var participant = new Participant(name);
    participants[name] = participant;
    var video = participant.getVideoElement();

    var options = {
        localVideo: video,
        mediaConstraints: constraints,
        onicecandidate: participant.onIceCandidate.bind(participant)
    }
    participant.rtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerSendonly(options,
        function (error) {
            if (error) {
                return console.error(error);
            }
            this.generateOffer(participant.offerToReceiveVideo.bind(participant));
        });

    msg.data.forEach(receiveVideo);
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

function receiveVideo(sender) {
    var participant = new Participant(sender);
    participants[sender] = participant;
    var video = participant.getVideoElement();

    var options = {
        remoteVideo: video,
        onicecandidate: participant.onIceCandidate.bind(participant)
    }

    participant.rtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerRecvonly(options,
        function (error) {
            if (error) {
                return console.error(error);
            }
            this.generateOffer(participant.offerToReceiveVideo.bind(participant));
        });
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
 * 이렇듯 Track 에서 steam 을 교체 - replace - 하기 위해서는 아래와 같은 과정을 거친다.
 * 1. myPeerConnection 에서 sender 를 가져온다. sender 란 나와 연결된 다른 peer 로 생각하면 된다.
 * 2. sender 객체에서 replaceTrack 함수를 활용해서 stream 을 교체한다.
 * 3. shareView 의 Track[0] 에는 videoStream 이 들어있다. 따라서 replaceTrack 의 파라미터에 shareView.getTrack[0] 을 넣는다.
 * 4. 화면 공유 취소 시 원래 화상 화면으로 되돌리기 위해서는 다시 Track 를 localstream 으로 교체해주면 된다!
 *      이때 localStream 에는 audio 와 video 모두 들어가 있음으로 video 에 해당하는 Track[1] 만 꺼내서 교체해준다.
 * **/

/*  화면 공유를 위한 변수 선언 */
const screenHandler = new ScreenHandler();
let shareView = null;

/**
 * ScreenHandler
 * @constructor
 */
function ScreenHandler() {
    // let localStream = null;

    console.log('Loaded ScreenHandler', arguments);

    // REF https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints#Properties_of_shared_screen_tracks
    const constraints = {
        audio: true,
        video: {
            maxWidth: 600,
            maxHeight: 600,
            frameRate: 50, // 최대 프레임
        },
    };

    /**
     * 스크린캡쳐 API를 브라우저 호환성 맞게 리턴합니다.
     * navigator.mediaDevices.getDisplayMedia 호출 (크롬 72 이상 지원)
     * navigator.getDisplayMedia 호출 (크롬 70 ~ 71 실험실기능 활성화 or Edge)
     */
    function getCrossBrowserScreenCapture() {
        if (navigator.getDisplayMedia) {
            return navigator.getDisplayMedia(constraints);
        } else if (navigator.mediaDevices.getDisplayMedia) {
            return navigator.mediaDevices.getDisplayMedia(constraints);
        }
    }

    /**
     * 스크린캡쳐 API를 호출합니다.
     * @returns shareView
     */
    async function start() {

        try {
            shareView = await getCrossBrowserScreenCapture();
        } catch (err) {
            console.log('Error getDisplayMedia', err);
        }

        return shareView;
    }

    /**
     * 스트림의 트렉을 stop()시켜 스트림이 전송을 중지합니다.
     */
    function end() {

        shareView.getTracks().forEach((track) => {
            // log("화면 공유 중지")
            track.stop();
        });

        // // 전송 중단 시 share-video 부분 hide
        // $("#share-video").hide();
    }

    /**
     * extends
     */
    this.start = start;
    this.end = end;

}

/**
 * screenHandler를 통해 스크린 API를 호출합니다
 * 원격 화면을 화면 공유 화면으로 교체
 */
async function startScreenShare() {

    // 스크린 API 호출 & 시작
    await screenHandler.start();

    // let participant = participants[name];
    // let localVideo = participant.getVideoElement();
    //
    // let options = {
    //     localVideo: localVideo,
    //     videoStream: shareView,
    //     mediaConstraints: constraints,
    //     onicecandidate: participant.onIceCandidate.bind(participant),
    //     sendSource: 'desktop'
    // };
    //
    // participant.rtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerSendrecv(options,
    //     function (error) {
    //         if (error) {
    //             return console.error(error);
    //         }
    //
    //         var message = {
    //             id: 'screenShare',
    //             name: name,
    //             room: roomId,
    //         }
    //         sendMessage(message)
    //
    //         this.generateOffer(participant.offerToReceiveVideo.bind(participant));
    //
    // });

    let participant = participants[name]
    let video = participant.getVideoElement();

    let constraints = {
        audio: true,
        video: {
            maxWidth: 600,
            maxHeight: 600,
            frameRate: 50, // 최대 프레임
        },
    };

    // var message = {
    //     id: 'screenShare',
    //     name: name,
    //     room: roomId,
    // }
    // sendMessage(message)

    // let options = {
    //     localVideo: video,
    //     mediaConstraints: constraints,
    //     videoStream: shareView,
    //     onicecandidate: participant.onIceCandidate.bind(participant)
    // }
    //
    //
    //
    // participant.rtcPeer = new kurentoUtils.WebRtcPeer.WebRtcPeerSendrecv(options,
    //     function (error) {
    //         if (error) {
    //             return console.error(error);
    //         }
    //         this.generateOffer(participant.offerToReceiveVideo.bind(participant));
    //     });

    // 본인
    // await video.getTracks().replaceTrack(shareView.getTracks()[0])

    // 상대
    await participant.rtcPeer.peerConnection.getSenders().forEach((sender) => {
        sender.replaceTrack(shareView.getTracks()[0]);
    })

}


