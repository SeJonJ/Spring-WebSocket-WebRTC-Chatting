/**
 * 파일 관련 js
 * fileUpload, fileDownload
 */

const fileUtil = {
    isinit: false,
    init: function () {
        self = this;
        if (!self.isinit) {
            $('#uploadFile').on('click', function () {
                self.uploadFile();
            });

            self.isinit = true;
        }
    },
    uploadFile: function () { /// 파일 업로드 부분 ////

        var file = $('#file')[0].files[0];
        var formData = new FormData();
        formData.append('file', file);
        formData.append('roomId', roomId);

        // 확장자 추출
        var fileDot = file.name.lastIndexOf('.');

        // 확장자 검사
        var fileType = file.name.substring(fileDot + 1, file.name.length);
        // console.log('type : ' + fileType);

        if (!(fileType == 'png' || fileType == 'jpg' || fileType == 'jpeg' || fileType == 'gif')) {
            alert('파일 업로드는 png, jpg, gif, jpeg 만 가능합니다');
            return;
        }

        let successCallback = function (data) {

            // console.log('업로드 성공')
            if (data.status === 'FAIL') {
                alert('서버와의 연결 문제로 파일 업로드에 실패했습니다 \n 잠시 후 다시 시도해주세요')
                return;
            }

            var chatMessage = {
                'roomId': roomId,
                sender: username,
                message: username + '님의 파일 업로드',
                type: 'TALK',
                file: data
            };

            // 해당 내용을 발신한다.
            stompClient.send('/pub/chat/sendMessage', {}, JSON.stringify(chatMessage));
        };

        let errorCallback = function (error) {

        };

        // ajax 로 multipart/form-data 를 넘겨줄 때는
        //         processData: false,
        //         contentType: false
        // 처럼 설정해주어야 한다.
        // 동작 순서
        // post 로 rest 요청한다.
        // 1. 먼저 upload 로 파일 업로드를 요청한다.
        // 2. upload 가 성공적으로 완료되면 data 에 upload 객체를 받고,
        // 이를 이용해 chatMessage 를 작성한다.
        fileUploadAjax('/file/upload', 'POST', true, formData, successCallback, errorCallback);

    },
    downloadFile: function (name, dir) { // 파일 다운로드
        // console.log("파일 이름 : "+name);
        // console.log("파일 경로 : " + dir);

        let url = "/file/download/" + name;
        let data = {
            "fileName": name,
            "filePath": dir // 파일의 경로를 파라미터로 넣는다.
        };

        let successCallback = function (data) {
            var link = document.createElement('a');
            link.href = URL.createObjectURL(data);
            link.download = name;
            link.click();
        };

        let errorCallback = function (error) {

        };

        fileDownloadAjax(url, 'POST', '', data, successCallback, errorCallback);
    }
}