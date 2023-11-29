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
        this.showNewMessage(event.data, "other")
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