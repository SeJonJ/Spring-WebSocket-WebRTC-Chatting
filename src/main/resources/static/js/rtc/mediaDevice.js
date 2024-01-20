/*
    media device 를 변경하기 위한 코드
 */

const mediaDevice = {
    myDevice: null,
    audioInputs: null,
    audioOutputs: null,
    // getMediaDevices: navigator.mediaDevices.enumerateDevices(),
    init: function () {
        const self = this;

        // self.getDeviceLiet();
        self.setMediaDeviceArea(); // 장비 선택 영역 set
        self.initClickEvent(); // 장비 클릭 이벤트 set
        self.hideDropDownEvent(); // focusout 이벤트 set
    },
    initClickEvent : function(){
        const self = this;
        $('#input_dropDownContainer').click(function() {
            self.dropDown('input');
            $('#output_dropDownPosition').hide();
        });

        $('#output_dropDownContainer').click(function() {
            self.dropDown('output');
            $('#input_dropDownPosition').hide();
        });
    },
    getDeviceLiet : function () {
        const self = this;
        navigator.mediaDevices.enumerateDevices().then(devices => {
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
    setMediaDeviceArea : function(){
        const self = this;
        navigator.mediaDevices.enumerateDevices()
            .then(devices => {
                // 'devices' 는  MediaDeviceInfo 를 담은 array
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
                    audioSender.replaceTrack(newAudioTrack).catch(error => {
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
        const displayTextWidth = $('#' + type + '_displayText').width();
        $('#' + type + '_dropDownPosition').width(displayTextWidth).toggle();
    },
    hideDropDownEvent: function() {
        // // 드롭다운 메뉴 외부 클릭 감지
        // $(document).click(function(event) {
        //     // 클릭된 요소가 드롭다운 메뉴가 아니면 드롭다운을 숨깁니다.
        //     if (!$(event.target).closest('#input_dropDownPosition, #output_dropDownPosition').length) {
        //         // 드롭다운 메뉴 밖을 클릭했을 때
        //         $('#input_dropDownPosition').hide();
        //         $('#output_dropDownPosition').hide();
        //     }
        // });

        $(document).click(function(event) {
            // input 드롭다운 메뉴와 그 컨테이너가 클릭 대상이 아닌 경우, 드롭다운을 숨깁니다.
            if (!$(event.target).closest('#input_dropDownContainer, #input_dropDownPosition').length) {
                $('#input_dropDownPosition').hide();
            }

            // output 드롭다운 메뉴와 그 컨테이너가 클릭 대상이 아닌 경우, 드롭다운을 숨깁니다.
            if (!$(event.target).closest('#output_dropDownContainer, #output_dropDownPosition').length) {
                $('#output_dropDownPosition').hide();
            }
        });
    }
}