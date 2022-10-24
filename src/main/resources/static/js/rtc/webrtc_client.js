'use strict';
// create and run Web Socket connection
const socket = new WebSocket("ws://" + window.location.host + "/signal");

// UI elements
const videoButtonOff = document.querySelector('#video_off');
const videoButtonOn = document.querySelector('#video_on');
const audioButtonOff = document.querySelector('#audio_off');
const audioButtonOn = document.querySelector('#audio_on');
const exitButton = document.querySelector('#exit');
const localRoom = document.querySelector('input#id').value;
const localVideo = document.getElementById('local_video');
const remoteVideo = document.getElementById('remote_video');
const localUserName = localStorage.getItem("uuid");

// WebRTC STUN servers
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
    // add an event listener for a message being received
    socket.onmessage = function(msg) {
        let message = JSON.parse(msg.data);
        switch (message.type) {
            case "text":
                log('Text message from ' + message.from + ' received: ' + message.data);
                break;

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
                log('Client is starting to ' + (message.data === "true)" ? 'negotiate' : 'wait for a peer'));
                handlePeerConnection(message);
                break;

            default:
                handleErrorMessage('Wrong type message received from server');
        }
    };

    // add an event listener to get to know when a connection is open
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
    socket.onclose = function(message) {
        log('Socket has been closed');
    };

    // an event listener to handle socket errors
    socket.onerror = function(message) {
        handleErrorMessage("Error: " + message);
    };
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
        if (remoteVideo.srcObject) {
            remoteVideo.srcObject.getTracks().forEach(track => track.stop());
        }
        if (localVideo.srcObject) {
            localVideo.srcObject.getTracks().forEach(track => track.stop());
        }

        remoteVideo.src = null;
        localVideo.src = null;

        // close the peer connection
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
// 1. create a WebRTC offer
// 2. set local media description
// 3. send the description as an offer on media format, resolution, etc
function handleNegotiationNeededEvent() {
    myPeerConnection.createOffer().then(function(offer) {
        return myPeerConnection.setLocalDescription(offer);
    })
        .then(function() {
            sendToServer({
                from: localUserName,
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
