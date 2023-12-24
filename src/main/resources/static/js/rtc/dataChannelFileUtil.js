/**
 * DataChannel 로 file 다루기 위한 util js
 */
const dataChannelFileUtil = {
    isinit: false,
    init : function(){
        let self = this;
        if (!self.isinit) {
            $('#uploadFile').on('click', function () {
                $('#file').click();
            });

            $('#file').on('change', function(){
                // 파일선택으로 change 되면 실행
                self.uploadFile();
            })

            self.isinit = true;
        }

    },
    uploadFile : function(){

        // 1. 다른 사용자에게 파일 전송
        var file = $('#file')[0].files[0];
        if (!file) {
            console.log('No file chosen');
        }

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

            var fileData = {
                type: 'file',
                'roomId': roomId,
                fileMeta: data
            };

            dataChannel.sendFileMessage(fileData);

        };

        let errorCallback = function (error) {

        };

        // 2. 서버에 파일 전송
        fileUploadAjax('/file/upload', 'POST', true, formData, successCallback, errorCallback);

    },
    downloadFile : function (name, dir) {
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