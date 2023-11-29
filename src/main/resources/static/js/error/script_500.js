$('body').mousemove(function(event) {
    var e = $('.eye');
    var x = (e.offset().left) + (e.width() / 2);
    var y = (e.offset().top) + (e.height() / 2);
    var rad = Math.atan2(event.pageX - x, event.pageY - y);
    var rot = (rad * (180 / Math.PI) * -1) + 180;
    e.css({
        '-webkit-transform': 'rotate(' + rot + 'deg)',
        'transform': 'rotate(' + rot + 'deg)'
    });
});
