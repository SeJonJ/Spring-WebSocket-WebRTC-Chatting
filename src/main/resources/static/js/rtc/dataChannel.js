/**
 * DataChannel 을 다루기 위한 js
 */
let chanId = 0;

const dataChannel = {
    user : null,
    userTextInput :  $('.text-box'),
    messagesContainer : $('.messages'),
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
    showNewMessage: function(recvMessage, type) {
        // 기본은 '나'가 보낸것
        type = type === undefined ? 'self' : type;
        var newMessage = this.userTextInput.html()
            .replace(/\<div\>|\<br.*?\>/ig, '\n').replace(/\<\/div\>/g, '')
            .trim()
            .replace(/\n/g, '<br>');

        // var messagesContainer = $('.messages');

        if (type === 'self') {
            if (!newMessage) return;

            this.messagesContainer.append([
                '<li class="self">',
                newMessage,
                '</li>'
            ].join(''));

            this.sendMessage(newMessage);
        } else {
            this.messagesContainer.append([
                '<li class="other">',
                recvMessage,
                '</li>'
            ].join(''));
        }

        // clean out old message
        this.userTextInput.html('');
        // focus on input
        this.userTextInput.focus();

        this.messagesContainer.finish().animate({
            scrollTop: this.messagesContainer.prop("scrollHeight")
        }, 250);
    }
}