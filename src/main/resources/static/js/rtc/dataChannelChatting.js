/*
* dataChannel 을 사용한 채팅을 위한 js
* */
const dataChannelChatting = {
    element: $('.floating-chat'),
    $sendMessageBtn : $("#sendMessageBtn"),
    userTextInput :  $('.text-box'),
    messagesContainer : $('.messages'),
    init: function() {
        const self = this; // 'self' 변수에 'this' 값을 할당
        var myStorage = localStorage;

        if (!myStorage.getItem('chatID')) {
            myStorage.setItem('chatID', self.createUUID());
        }

        setTimeout(function() {
            self.element.addClass('enter');
        }, 1000);

        self.element.click(self.openElement);

        self.userTextInput.on('keydown', function(event) {
            if (event.shiftKey && event.which === 13) {
                // shift + enter 사용 시 한줄 띄우기
            } else if (event.which === 13) {
                event.preventDefault(); // 기본 동작(한줄 띄우기)을 방지
                dataChannel.showNewMessage(self.parseMessage(self.userTextInput), "self");
            }
        });

        this.$sendMessageBtn.on("click", function(){
            dataChannel.showNewMessage(self.parseMessage(self.userTextInput), "self");
        });

    },
    openElement: function() {
        const self = dataChannelChatting; // 여기서 'this'는 클릭된 DOM 요소를 가리킵니다.
        var messages = self.element.find('.messages');
        self.element.find('>i').hide();
        self.element.addClass('expand');
        self.element.find('.chat').addClass('enter');
        self.element.off('click', self.openElement);
        self.element.find('.header button').click(self.closeElement);
        messages.scrollTop(messages.prop("scrollHeight"));
    },
    closeElement: function() {
        const self = dataChannelChatting;
        self.element.find('.chat').removeClass('enter').hide();
        self.element.find('>i').show();
        self.element.removeClass('expand');
        self.element.find('.header button').off('click', self.closeElement);
        setTimeout(function() {
            self.element.find('.chat').removeClass('enter').show();
            self.element.click(self.openElement);
        }, 500);
    },
    createUUID : function() {
        var s = [];
        var hexDigits = "0123456789abcdef";
        for (var i = 0; i < 36; i++) {
            s[i] = hexDigits.substr(Math.floor(Math.random() * 0x10), 1);
        }
        s[14] = "4"; // bits 12-15 of the time_hi_and_version field to 0010
        s[19] = hexDigits.substr((s[19] & 0x3) | 0x8, 1); // bits 6-7 of the clock_seq_hi_and_reserved to 01
        s[8] = s[13] = s[18] = s[23] = "-";

        var uuid = s.join("");
        return uuid;
    },
    parseMessage: function(userTextInput){
        return userTextInput.html()
            .replace(/\<div\>|\<br.*?\>/ig, '\n').replace(/\<\/div\>/g, '')
            .trim()
            .replace(/\n/g, '<br>');
    }
}