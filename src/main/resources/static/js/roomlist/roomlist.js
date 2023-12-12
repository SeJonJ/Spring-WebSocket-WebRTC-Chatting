let roomId;
const locationHost = location.host;

$(function () {
    let $maxUserCnt = $("#maxUserCnt");
    let $msgType = $("#msgType");

    // 모달창 열릴 때 이벤트 처리 => roomId 가져오기
    $("#enterRoomModal").on("show.bs.modal", function (event) {
        roomId = $(event.relatedTarget).data('id');
        // console.log("roomId: " + roomId);
    });

    $("#confirmPwdModal").on("show.bs.modal", function (e) {
        roomId = $(e.relatedTarget).data('id');
        // console.log("roomId: " + roomId);
    });

    // 채팅방 설정 시 비밀번호 확인
    confirmPWD();

    // 문자 채팅 누를 시 disabled 풀림
    $msgType.change(function () {
        if ($msgType.is(':checked')) {
            $maxUserCnt.attr('disabled', false);
        }
    })


    function checkVisitor() {
        let url = "https://" + location.host + "/visitor";
        let data = {
            "isVisitedToday": sessionStorage.getItem("isVisitedToday")
        };

        let successCallback = function(data){
            dailyVisitor = data;
            $('#visitorCount').text('방문자 수 : ' + dailyVisitor);
        };

        let errorCallback = function(error){
            console.error("Error ajax data: ", error);
        };

        let completeCallback = function (result) {
            // 일일 방문자 check
            if (!sessionStorage.getItem('isVisitedToday') || sessionStorage.getItem('isVisitedToday') === false) {
                sessionStorage.setItem('isVisitedToday', 'true');
            }
        };

        ajax(url, 'POST', '', data, successCallback, errorCallback, completeCallback);
    }
    checkVisitor();


    // hideAnnouncement 값이 없거나 false 라면 show 아니면 hide
    if (!sessionStorage.getItem('hideAnnouncement') || sessionStorage.getItem('hideAnnouncement') === 'false') {
        $('#announcementModal').modal('show');
    } else {
        $('#announcementModal').modal('hide');
    }

    // "오늘 하루 안보기" 버튼 누르면 sessionStorage 에 item 생성
    $('#announcementModal').on('hide.bs.modal', function (event) {
        if (document.getElementById('dontShowAgain').checked) {
            sessionStorage.setItem('hideAnnouncement', 'true');
        }
    });

    $("#agreeBtn").click(function(){
        fetch("https://"+locationHost+"/user_agree", {
            method: 'GET'
        })
            .then(response => {
                console.info("user agree!!")
            })
            .catch(error => {
                console.error('Error:', error);
            });
    })
})

// 채팅방 설정 시 비밀번호 확인 - keyup 펑션 활용
function confirmPWD() {
    $("#confirmPwd").on("keyup", function () {
        let $confirmPwd = $("#confirmPwd").val();
        const $configRoomBtn = $("#configRoomBtn");
        let $confirmLabel = $("#confirmLabel");

        let url = '/chat/confirmPwd/' + roomId
        let data = {
                "roomPwd": $confirmPwd
        };
        let successCallback = function(result){
            // console.log("동작완료")

            // result 의 결과에 따라서 아래 내용 실행
            if (result) { // true 일때는
                // $configRoomBtn 를 활성화 상태로 만들고 비밀번호 확인 완료를 출력
                $configRoomBtn.attr("class", "btn btn-primary");
                $configRoomBtn.attr("aria-disabled", false);

                $confirmLabel.html("<span id='confirm'>비밀번호 확인 완료</span>");
                $("#confirm").css({
                    "color": "#0D6EFD",
                    "font-weight": "bold",
                });

            } else { // false 일때는
                // $configRoomBtn 를 비활성화 상태로 만들고 비밀번호가 틀립니다 문구를 출력
                $configRoomBtn.attr("class", "btn btn-primary disabled");
                $configRoomBtn.attr("aria-disabled", true);

                $confirmLabel.html("<span id='confirm'>비밀번호가 틀립니다</span>");
                $("#confirm").css({
                    "color": "#FA3E3E",
                    "font-weight": "bold",
                });

            }
        };

        let errorCallback = function (error) {
          console.error(error)
        };

        ajax(url, 'POST', '', data, successCallback, errorCallback);
    });
}

// 채팅 인원 숫자만 정규식 체크
function numberChk() {
    let check = /^[0-9]+$/;
    if (!check.test($("#maxUserCnt").val())) {
        alert("채팅 인원에는 숫자만 입력 가능합니다!!")
        return false;
    }
    return true;
}

// 채팅방 생성
function createRoom() {

    let name = $("#roomName").val();
    let pwd = $("#roomPwd").val();
    let secret = $("#secret").is(':checked');
    let secretChk = $("#secretChk");
    let $rtcType = $("#rtcType");
    let $msgType = $("#msgType");

    if (name === "") {
        alert("방 이름은 필수입니다")
        return false;
    }
    if ($("#" + name).length > 0) {
        alert("이미 존재하는 방입니다")
        return false;
    }
    if (pwd === "") {
        alert("비밀번호는 필수입니다")
        return false;
    }

    if ($rtcType.is(':checked')) {
        if ($("#maxUserCnt").val() <= 1) {
            alert("채팅은 최소 2명 이상!!");
            return false;
        } else if ($("#maxUserCnt").val() > 4) {
            alert("4명 이상은 서버가 아파요ㅠ.ㅠ");
            return false;
        }
    } else if ($msgType.is(':checked')) {
        // 일반채팅 : 최소 방 인원 수는 2, 최대 100명
        if ($("#maxUserCnt").val() <= 1) {
            alert("채팅은 최소 2명 이상!!");
            return false;
        } else if ($("#maxUserCnt").val() > 100) {
            alert("100명 이상은 서버가 못 버텨요ㅠ.ㅠ");
            return false;
        }
    }

    // 채팅 타입 필수
    if ($('input[name=chatType]:checked').val() == null) {
        alert("채팅 타입은 필수입니다")
        return false;
    }

    if (secret) {
        secretChk.attr('value', true);
    } else {
        secretChk.attr('value', false);
    }

    if (!numberChk()) {
        return false;
    }

    return true;
}

// 채팅방 입장 시 비밀번호 확인
function enterRoom() {
    let $enterPwd = $('#enterPwd').val();

    let url = '/chat/confirmPwd/' + roomId;
    let data = {
        'roomPwd': $enterPwd
    };
    let successCallback = function (result) {
        // console.log("동작완료")
        // console.log("확인 : "+chkRoomUserCnt(roomId))

        if (result) {
            let enterRoomFnc = function(){
                location.href = '/chat/room?roomId=' + roomId;
            }
            chkRoomUserCnt(roomId, enterRoomFnc);

        } else {
            alert("비밀번호가 틀립니다. \n 비밀번호를 확인해주세요");
        }
    };
    let errorCallback = function (error) {
        console.error(error);
    }

    ajax(url, 'POST', false, data, successCallback, errorCallback);
}

// 채팅방 삭제
function delRoom() {
    location.href = "/chat/delRoom/" + roomId;
}

// 채팅방 입장 시 인원 수에 따라서 입장 여부 결정
function chkRoomUserCnt(roomId, enterRoom) {
    let url = '/chat/chkUserCnt/' + roomId;
    let successCallback = function (result) {
        // console.log("여기가 먼저")
        if (!result) {
            alert("채팅방이 꽉 차서 입장 할 수 없습니다");
            return;
        }

        enterRoom();
    };
    let errorCallback = function (error) {
        console.error(error);
    }

    // 비동기 처리 false 인 경우에는 ajax 통신이 완료된 후 return 문 실행
    // 기본설정 async = true 인 경우에는 ajax 통신 후 결과가 나올 때까지 기다리지 않고 먼저 return 문이 실행되서
    // 제대로된 값 - 원하는 값 - 이 return 되지 않아서 문제가 발생한다.
    ajax(url, 'GET', 'false', '', successCallback, errorCallback);

}
