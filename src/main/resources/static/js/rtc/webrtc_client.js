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


document.querySelector('#view_on').addEventListener('click', startScreenShare);
document.querySelector('#view_off').addEventListener('click', stopScreenShare);


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
    video: true,
    audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 44100
    }
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

function log(message) {
     // console.log(message);
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

    myPeerConnection.oniceconnectionstatechange = handleICEConnectionStateChangeEvent;
    // myPeerConnection.onicegatheringstatechange = handleICEGatheringStateChangeEvent;
    // myPeerConnection.onsignalingstatechange = handleSignalingStateChangeEvent;
}

/** peerConnection 과 관련된 이벤트 처리
 * 다른 peer 와 연결되었을 때 remote_video show 상태로로, 끊졌을때는 remote_video 를 hide 상태로 변경
 * **/
function handleICEConnectionStateChangeEvent(){
    let status = myPeerConnection.iceConnectionState;

    if(status === "connected"){
        log("status : "+status)
        $("#remote_video").show();
    }else if(status === "disconnected"){
        log("status : "+status)

        $("#remote_video").hide();
    }
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

    log('Loaded ScreenHandler', arguments);

    // REF https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints#Properties_of_shared_screen_tracks
    const constraints = {
        audio: true,
        video: {
            width: 1980, // 최대 너비
            height: 1080, // 최대 높이
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
            log('Error getDisplayMedia', err);
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

    // 1. myPeerConnection 에 연결된 다른 sender 쪽으로 - 즉 다른 Peer 쪽으로 -
    // 2. shareView 의 Track 에서 0번째 인덱스에 들어있는 값 - 즉 videoStream 로 - 교체한다.
    await myPeerConnection.getSenders().forEach((sender)=>{ // 연결된 sender 로 보내기위한 반복문

        // 3. track 를 shareView 트랙으로 교체
        sender.replaceTrack(shareView.getTracks()[0])

    })

    // // Track 가 진짜 배열인지 확인하기
    // console.dir(shareView.getTracks());
    // console.dir(localStream.getTracks());

    /**
     * 화면 공유 중지 눌렀을 때 이벤트
     */
    shareView.getVideoTracks()[0].addEventListener('ended', () =>{
        // log('screensharing has ended')

        // 4. 화면 공유 중지 시 Track 를 localstream 의 videoStram 로 교체함
        myPeerConnection.getSenders().forEach((sender) =>{
            sender.replaceTrack(localStream.getTracks()[1]);
        })

        // $("#share-video").hide();

    });

}

/*
*  video off 버튼을 통해 스크린 API 종료
* */
async function stopScreenShare(){

    // screen share 종료
    await screenHandler.end();
    // myPeerConnection
    await myPeerConnection.getSenders().forEach((sender) =>{

        // 4. 화면 공유 중지 시 Track 를 localstream 의 videoStram 로 교체함
        sender.replaceTrack(localStream.getTracks()[1]);
    })
}