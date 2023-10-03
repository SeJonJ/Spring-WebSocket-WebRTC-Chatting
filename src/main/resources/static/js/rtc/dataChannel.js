/**
 * DataChannel 을 다루기 위한 js
 */
let chanId = 0;

const dataChannel = {
    init: function () {
        user = null; // dataChannel 유저
        this.handleDataChannelOpen();
        this.handleDataChannelClose();
        this.handleDataChannelMessageReceived();
        this.handleDataChannelError();
    },
    initDataChannelUser(user){
        dataChannel.user = user;
    },
    isNullOrUndefined(value) {
        return value === null || value === undefined;
    },
    getChannelName() {
        return chanId++;
    },
    handleDataChannelOpen: (event) => {
        if (dataChannel.isNullOrUndefined(event)) return;
        console.log("dataChannel.OnOpen", event);
        dataChannel.sendMessage("등장!!")
    },
    handleDataChannelMessageReceived: (event) => {
        if (dataChannel.isNullOrUndefined(event)) return;
        console.log("dataChannel.OnMessage:", event);
    },
    handleDataChannelError: (error) => {
        if (dataChannel.isNullOrUndefined(error)) return;
        console.error("dataChannel.OnError:", error);
    },
    handleDataChannelClose: (leaveEvent, event) => {
        if (dataChannel.isNullOrUndefined(event)) return;
        console.log("dataChannel.OnClose", event);
    },
    sendMessage: (message) => {
        if (dataChannel.isNullOrUndefined(message)) return;
        dataChannel.user.rtcPeer.send(dataChannel.user.name+" : "+message);
    }
}