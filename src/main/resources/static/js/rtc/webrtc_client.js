'use strict';
const addr = "localhost:8443"

// create and run Web Socket connection
// 웹 소켓 연결 정보
const socket = new WebSocket("wss://" + window.location.host + "/signal");

// UI elements
const videoButtonOff = document.querySelector('#video_off');
const videoButtonOn = document.querySelector('#video_on');
const audioButtonOff = document.querySelector('#audio_off');
const audioButtonOn = document.querySelector('#audio_on');
const exitButton = document.querySelector('#exit');
const localRoom = document.querySelector('input#id').value;
const localVideo = document.getElementById('local_video');
const remoteVideo = document.getElementById('remote_video');
// const localUserName = localStorage.getItem("uuid");
const localUserName = document.querySelector("#uuid").value

const viewOnBtn = document.querySelector('#view_on');
const viewOffBtn = document.querySelector('#view_off');

// WebRTC STUN servers
// WebRTC STUN 서버 정보
const peerConnectionConfig = {
    'iceServers': [
        {'urls': 'stun:stun.stunprotocol.org:3478'},
        {'urls': 'stun:stun.l.google.com:19302'},
    ]
};

// WebRTC media
const mediaConstraints = {
    audio: true,
    video: true
};

// WebRTC variables
let localStream;
let localVideoTracks;
let myPeerConnection;

// on page load runner
$(function(){
    start();
});

function start() {
    // 페이지 시작시 실행되는 메서드 -> socket 을 통해 server 와 통신한다
    socket.onmessage = function(msg) {
        let message = JSON.parse(msg.data);
        switch (message.type) {

            case "offer":
                log('Signal OFFER received');
                handleOfferMessage(message);
                break;

            case "answer":
                log('Signal ANSWER received');
                handleAnswerMessage(message);
                break;

            case "ice":
                log('Signal ICE Candidate received');
                handleNewICECandidateMessage(message);
                break;

            case "join":
                // ajax 요청을 보내서 userList 를 다시 확인함
                message.data = chatListCount();

                log('Client is starting to ' + (message.data === "true)" ? 'negotiate' : 'wait for a peer'));
                log("messageDATA : "+message.data)
                handlePeerConnection(message);
                break;

            case "leave":
                stop();
                break;

            default:
                handleErrorMessage('Wrong type message received from server');
        }
    };


    // ICE 를 위한 chatList 인원 확인
    function chatListCount(){

        let data;

        $.ajax({
            url : "/webrtc/usercount",
            type : "POST",
            async : false,
            data : {
                "from" : localUserName,
                "type" : "findCount",
                "data" : localRoom,
                "candidate" : null,
                "sdp" : null
            },
            success(result){
                data = result;
            },
            error(result){
                console.log("error : "+result);
            }
        });

        return data;
    }


    // add an event listener to get to know when a connection is open
    // 웹 소켓 연결 되었을 때 - open - 상태일때 이벤트 처리
    socket.onopen = function() {
        log('WebSocket connection opened to Room: #' + localRoom);
        // send a message to the server to join selected room with Web Socket
        sendToServer({
            from: localUserName,
            type: 'join',
            data: localRoom
        });
    };

    // a listener for the socket being closed event
    // 소켓이 끊겼을 때 이벤트처리
    socket.onclose = function(message) {
        log('Socket has been closed');

    };

    // an event listener to handle socket errors
    // 에러 발생 시 이벤트 처리
    socket.onerror = function(message) {
        handleErrorMessage("Error: " + message);
    };
}

// 브라우저 종료 시 이벤트
// 그냥...브라우저 종료 시 stop 함수를 부르면 된다ㅠㅠ
window.addEventListener('unload', stop);

// 브라우저 뒤로가기 시 이벤트
window.onhashchange = function(){
    stop();
}

function stop() {
    // send a message to the server to remove this client from the room clients list
    log("Send 'leave' message to server");
    sendToServer({
        from: localUserName,
        type: 'leave',
        data: localRoom
    });

    if (myPeerConnection) {
        log('Close the RTCPeerConnection');

        // disconnect all our event listeners
        myPeerConnection.onicecandidate = null;
        myPeerConnection.ontrack = null;
        myPeerConnection.onnegotiationneeded = null;
        myPeerConnection.oniceconnectionstatechange = null;
        myPeerConnection.onsignalingstatechange = null;
        myPeerConnection.onicegatheringstatechange = null;
        myPeerConnection.onnotificationneeded = null;
        myPeerConnection.onremovetrack = null;

        // Stop the videos
        // 비디오 정지
        if (remoteVideo.srcObject) {
            remoteVideo.srcObject.getTracks().forEach(track => track.stop());
        }
        if (localVideo.srcObject) {
            localVideo.srcObject.getTracks().forEach(track => track.stop());
        }

        remoteVideo.src = null;
        localVideo.src = null;

        // close the peer connection
        // myPeerConnection 초기화
        myPeerConnection.close();
        myPeerConnection = null;

        log('Close the socket');
        if (socket != null) {
            socket.close();
        }
    }
}

/*
 UI Handlers
  */
// mute video buttons handler
videoButtonOff.onclick = () => {
    localVideoTracks = localStream.getVideoTracks();
    localVideoTracks.forEach(track => localStream.removeTrack(track));
    $(localVideo).css('display', 'none');
    log('Video Off');
};
videoButtonOn.onclick = () => {
    localVideoTracks.forEach(track => localStream.addTrack(track));
    $(localVideo).css('display', 'inline');
    log('Video On');
};

// mute audio buttons handler
audioButtonOff.onclick = () => {
    localVideo.muted = true;
    log('Audio Off');
};
audioButtonOn.onclick = () => {
    localVideo.muted = false;
    log('Audio On');
};

// room exit button handler
exitButton.onclick = () => {
    stop();
};

// 화면 공유
viewOnBtn.onclick = () => {
    navigator.mediaDevices.getDisplayMedia({
        audio: true,
        video: true
    }).then(function(stream){
        //success
    }).catch(function(e){
        //error;
    });
}



function log(message) {
     console.log(message);
}

function handleErrorMessage(message) {
    console.error(message);
}

// use JSON format to send WebSocket message
function sendToServer(msg) {
    let msgJSON = JSON.stringify(msg);
    socket.send(msgJSON);
}

// initialize media stream
function getMedia(constraints) {
    if (localStream) {
        localStream.getTracks().forEach(track => {
            track.stop();
        });
    }
    navigator.mediaDevices.getUserMedia(constraints)
        .then(getLocalMediaStream).catch(handleGetUserMediaError);
}

// create peer connection, get media, start negotiating when second participant appears
// 두번째 클라이언트가 들어오면 피어 연결을 생성 + 미디어 생성
function handlePeerConnection(message) {
    createPeerConnection();

    getMedia(mediaConstraints);

    if (message.data === "true") {

        myPeerConnection.onnegotiationneeded = handleNegotiationNeededEvent;
    }
}

function createPeerConnection() {
    myPeerConnection = new RTCPeerConnection(peerConnectionConfig);

    // event handlers for the ICE negotiation process
    myPeerConnection.onicecandidate = handleICECandidateEvent;
    myPeerConnection.ontrack = handleTrackEvent;

    // the following events are optional and could be realized later if needed
    // myPeerConnection.onremovetrack = handleRemoveTrackEvent;
    // myPeerConnection.oniceconnectionstatechange = handleICEConnectionStateChangeEvent;
    // myPeerConnection.onicegatheringstatechange = handleICEGatheringStateChangeEvent;
    // myPeerConnection.onsignalingstatechange = handleSignalingStateChangeEvent;
}
// add MediaStream to local video element and to the Peer
function getLocalMediaStream(mediaStream) {
    localStream = mediaStream;
    localVideo.srcObject = mediaStream;
    localStream.getTracks().forEach(track => myPeerConnection.addTrack(track, localStream));
}

// handle get media error
function handleGetUserMediaError(error) {
    log('navigator.getUserMedia error: ', error);
    switch(error.name) {
        case "NotFoundError":
            alert("Unable to open your call because no camera and/or microphone were found.");
            break;
        case "SecurityError":
        case "PermissionDeniedError":
            // Do nothing; this is the same as the user canceling the call.
            break;
        default:
            alert("Error opening your camera and/or microphone: " + error.message);
            break;
    }

    stop();
}

// send ICE candidate to the peer through the server
function handleICECandidateEvent(event) {
    if (event.candidate) {
        sendToServer({
            from: localUserName,
            data: localRoom,
            type: 'ice',
            candidate: event.candidate
        });
        log('ICE Candidate Event: ICE candidate sent');
    }
}

function handleTrackEvent(event) {
    log('Track Event: set stream to remote video element');
    remoteVideo.srcObject = event.streams[0];
}

// WebRTC called handler to begin ICE negotiation
// WebRTC 의 ICE 통신 순서
// 1. WebRTC offer 생성
// 2. local media description 생성?
// 3. 미디어 형식, 해상도 등에 대한 내용을 서버에 전달
function handleNegotiationNeededEvent() {
    myPeerConnection.createOffer().then(function(offer) {
        return myPeerConnection.setLocalDescription(offer);
    })
        .then(function() {
            sendToServer({
                from: localUserName,
                data:localRoom,
                type: 'offer',
                sdp: myPeerConnection.localDescription
            });
            log('Negotiation Needed Event: SDP offer sent');
        })
        .catch(function(reason) {
            // an error occurred, so handle the failure to connect
            handleErrorMessage('failure to connect error: ', reason);
        });
}

function handleOfferMessage(message) {
    log('Accepting Offer Message');
    log(message);
    let desc = new RTCSessionDescription(message.sdp);
    //TODO test this
    if (desc != null && message.sdp != null) {
        log('RTC Signalling state: ' + myPeerConnection.signalingState);
        myPeerConnection.setRemoteDescription(desc).then(function () {
            log("Set up local media stream");
            return navigator.mediaDevices.getUserMedia(mediaConstraints);
        })
            .then(function (stream) {
                log("-- Local video stream obtained");
                localStream = stream;
                try {
                    localVideo.srcObject = localStream;
                } catch (error) {
                    localVideo.src = window.URL.createObjectURL(stream);
                }

                log("-- Adding stream to the RTCPeerConnection");
                localStream.getTracks().forEach(track => myPeerConnection.addTrack(track, localStream));
            })
            .then(function () {
                log("-- Creating answer");
                // Now that we've successfully set the remote description, we need to
                // start our stream up locally then create an SDP answer. This SDP
                // data describes the local end of our call, including the codec
                // information, options agreed upon, and so forth.
                return myPeerConnection.createAnswer();
            })
            .then(function (answer) {
                log("-- Setting local description after creating answer");
                // We now have our answer, so establish that as the local description.
                // This actually configures our end of the call to match the settings
                // specified in the SDP.
                return myPeerConnection.setLocalDescription(answer);
            })
            .then(function () {
                log("Sending answer packet back to other peer");
                sendToServer({
                    from: localUserName,
                    data: localRoom,
                    type: 'answer',
                    sdp: myPeerConnection.localDescription
                });

            })
            // .catch(handleGetUserMediaError);
            .catch(handleErrorMessage)
    }
}

function handleAnswerMessage(message) {
    log("The peer has accepted request");

    // Configure the remote description, which is the SDP payload
    // in our "video-answer" message.
    // myPeerConnection.setRemoteDescription(new RTCSessionDescription(message.sdp)).catch(handleErrorMessage);
    myPeerConnection.setRemoteDescription(message.sdp).catch(handleErrorMessage);
}

function handleNewICECandidateMessage(message) {
    let candidate = new RTCIceCandidate(message.candidate);
    log("Adding received ICE candidate: " + JSON.stringify(candidate));
    myPeerConnection.addIceCandidate(candidate).catch(handleErrorMessage);
}