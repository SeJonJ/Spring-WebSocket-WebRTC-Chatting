/**
 * DataChannel 을 다루기 위한 js
 */
let chanId = 0;

const dataChannel = {
    user : null,
    init: function() {
        // 핸들러들을 바인딩하여 'this'가 항상 dataChannel 객체를 참조하도록 보장하기 위함
        this.handleDataChannelOpen = this.handleDataChannelOpen.bind(this);
        this.handleDataChannelClose = this.handleDataChannelClose.bind(this);
        this.handleDataChannelMessageReceived = this.handleDataChannelMessageReceived.bind(this);
        this.handleDataChannelError = this.handleDataChannelError.bind(this);
    },
    initDataChannelUser : function(user) {
        this.user = user;
    },
    isNullOrUndefined : function(value) {
        return value === null || value === undefined;
    },
    getChannelName : function() {
        return chanId++;
    },
    handleDataChannelOpen: function(event)  {
        if (this.isNullOrUndefined(event)) return;
        // console.log("dataChannel.OnOpen", event);
        this.sendMessage("등장!!")
    },
    handleDataChannelMessageReceived: function(event) {
        if (this.isNullOrUndefined(event)) return;
        // console.log("dataChannel.OnMessage:", event);
        let recvMessage = JSON.parse(event.data);

        if (recvMessage.type === "file") {
            // 파일 메시지 처리
            console.log("Received file:", recvMessage.fileName);

            // 전송 후 받아온 파일 데이터를 Blob 객체로 변환
            const blob = new Blob([recvMessage.fileData], {type: recvMessage.fileType});

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = recvMessage.fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            // 굳이...데이터 채널로 보낼 필요가 있어...?
            // 1. server ajax 통신 -> 파일 업로드
            // 2. server ajax 통신 -> 파일 다운로드 링크 생성
            // 3. 해당 링크 누르면 다운로드 되도록 하면 끝 아님??
        } else {
            // 일반 메시지 처리
            let message = recvMessage.userName + " : " + recvMessage.message;
            this.showNewMessage(message, "other");
        }
    },
    handleDataChannelError: function(error) {
        if (this.isNullOrUndefined(error)) return;
        console.error("dataChannel.OnError:", error);
    },
    handleDataChannelClose: function(leaveEvent, event) {
        if (this.isNullOrUndefined(event)) return;
        // console.log("dataChannel.OnClose", event);
    },
    sendMessage: function(message) {
        if (this.isNullOrUndefined(message)) return;
        this.user.rtcPeer.send(this.user.name + " : " + message);
    },
    showNewMessage: function(recvMessage, type) { // 이거는 datachannelChatting 으로 넘어가야하는거...?
        // 기본은 '나'가 보낸것
        type = type === undefined ? 'self' : type;

        if (type === 'self') {
            if (!recvMessage) return;

            dataChannelChatting.messagesContainer.append([
                '<li class="self">',
                recvMessage,
                '</li>'
            ].join(''));

            this.sendMessage(recvMessage);

            // clean out old message
            dataChannelChatting.userTextInput.html('');

            // focus on input
            dataChannelChatting.userTextInput.focus();

            dataChannelChatting.messagesContainer.finish().animate({
                scrollTop: dataChannelChatting.messagesContainer.prop("scrollHeight")
            }, 250);

        } else {
            dataChannelChatting.messagesContainer.append([
                '<li class="other">',
                recvMessage,
                '</li>'
            ].join(''));
        }
    }
}