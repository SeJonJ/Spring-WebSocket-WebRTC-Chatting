/*
    media device 를 변경하기 위한 코드
 */

const mediaDevice = {
    myDevice: null,
    audioInputs: null,
    audioOutputs: null,
    getMediaDevices: navigator.mediaDevices.enumerateDevices(),
    init: function () {
        const self = this;

        self.getMediaDevices
            .then(devices => {
                // 'devices' is the array of MediaDeviceInfo objects
                // console.log(devices);
                self.getDeviceLiet(devices);
                // Dynamically add devices to dropdown
                devices.forEach(function (device) {

                    if (device.kind === 'audioinput') {
                        if (device.deviceId === 'default') {
                            self.setDisplayText('input', self.myDevice !== null ? self.myDevice.label : self.defaultDevice(device));
                        }

                        $('#input_dropDown').append(
                            $('<div></div>')
                                .addClass('dropDownItem')
                                .text(device.label)
                                .click(function (event) {
                                    self.setInputAudioDevice(device, event);
                                })
                        );
                    } else if (device.kind === 'audiooutput') {
                        if (device.deviceId === 'default') {
                            self.setDisplayText('output', self.myDevice !== null ? self.myDevice.label : self.defaultDevice(device));
                        }

                        $('#output_dropDown').append(
                            $('<div></div>')
                                .addClass('dropDownItem')
                                .text(device.label)
                                .click(function (event) {
                                    self.setOutputAudioDevice(device, event);
                                })
                        );
                    }
                });
            })
            .catch(error => {
                console.error('Error occurred:', error);
            });

        self.initClickEvent();
    },
    initClickEvent : function(){
        const self = this;
        $('#input_dropDownContainer').click(function(){
            self.dropDown('input');
        });

        $('#output_dropDownContainer').click(function(){
            self.dropDown('output');
        });
    },
    getDeviceLiet : function () {
        this.getMediaDevices.then(devices => {
            self.audioInputs = devices.filter(device => device.kind === 'audioinput');
            self.audioOutputs = devices.filter(device => device.kind === 'audiooutput');

            console.log(self.audioInputs);
            console.log(self.audioOutputs);
        })
            .catch(error => {
                console.log(error, "error getting devices");
                if (onError && typeof onError === 'function') {
                    onError(error);
                }
            });
    },
    defaultDevice: function (device) {
        // Implement your default device logic here
        this.myDevice = device;
        return device.label;
    },
    setDisplayText: function (type, label) {
        $('#' + type + '_displayText').text(label);
    },
    setOutputAudioDevice: function (device, event) {
        const self = this;
        Object.entries(participants).forEach(([key, value]) => {
            if (key !== name) {
                console.log("change device :: " + JSON.stringify(value));
                value.getAudioElement().setSinkId(device.deviceId);
                self.setDisplayText('output', device.label);
            }
        });
    },
    setInputAudioDevice : function(device, event) {
        const self = this;

        origGetUserMedia({
            audio : {
                deviceId : device.deviceId }
        }).then(newStream => {
                // 새 스트림에서 오디오 트랙 추출
                const newAudioTrack = newStream.getAudioTracks()[0];

                // 참가자의 RTCPeerConnection에서 모든 전송기를 가져옴
                const senders = participants[name].rtcPeer.peerConnection.getSenders();

                // 오디오 트랙을 가진 전송기 찾기
                const audioSender = senders.find(sender => sender.track && sender.track.kind === 'audio');

                // 새 오디오 트랙으로 교체
                if (audioSender) {
                    audioSender.replaceTrack(newAudioTrack).then(() => {
                        console.log('sucess to replace audio track');
                    }).catch(error => {
                        console.error('fail to replace audio track', error);
                    });
                } else {
                    console.log('cant find audio track');
                }
            }
        );

        self.setDisplayText('input', device.label);

    },
    dropDown : function(type) {
        const displayTextWidth = $('#'+type+'_displayText').width();
        if (type === 'output') {
            // 너비를 dropDownPosition 에 맞게 설정
            $('#output_dropDownPosition').width(displayTextWidth).toggle();
        } else {
            // 너비를 dropDownPosition 에 맞게 설정
            $('#input_dropDownPosition').width(displayTextWidth).toggle();
        }
    }
}