/**
 * ajax 사용 시 공통화를 위한 js
 */

function ajax(url, method, async, data, successCallback, errorCallback, completeCallback) {
    $.ajax({
        url: url,
        type: method,
        data: data,
        async: async !== undefined ? async : true,
        success: function (data) {
            successCallback(data);
        },
        error: function (error) {
            errorCallback(error)
        },
        complete : function(result){
            if (completeCallback !== undefined && typeof completeCallback === "function") {
                completeCallback(result);
            }
        }
    })
}

function fileUploadAjax(url, method, async, data, successCallback, errorCallback) {
    $.ajax({
        url: url,
        type: method,
        data: data,
        async: async !== undefined ? async : true,
        processData: false,
        contentType: false,
        success: function (data) {
            successCallback(data);
        },
        error: function (error) {
            errorCallback(error)
        },
    })
}

function fileDownloadAjax(url, method, async, data, successCallback, errorCallback){
    $.ajax({
        url: url,
        type: method,
        data: data,
        async: async !== '' ? async : true,
        dataType: 'binary', // 파일 다운로드를 위해서는 binary 타입으로 받아야한다.
        xhrFields: {
            'responseType': 'blob' // 여기도 마찬가지
        },
        success: function (data) {
            successCallback(data);
        },
        error: function (error) {
            errorCallback(error)
        },
    })
}