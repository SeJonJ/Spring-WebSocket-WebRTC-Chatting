const model = await handpose.load();
const webcam = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const startButton = document.getElementById('start-button');
const stopButton = document.getElementById('stop-button');

startButton.addEventListener('click', async () => {
    // Start webcam
    webcam.srcObject = await navigator.mediaDevices.getUserMedia({video: true});
    webcam.onloadedmetadata = () => {
        webcam.play();
    };

    // Start tracking finger point
    setInterval(async () => {
        const predictions = await model.estimateHands(webcam);
        if (predictions.length > 0) {
            const fingerPoint = predictions[0].landmarks[0];
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.beginPath();
            ctx.arc(fingerPoint[0], fingerPoint[1], 10, 0, 2 * Math.PI);
            ctx.fillStyle = 'red';
            ctx.fill();
        }
    }, 100);
});

stopButton.addEventListener('click', () => {
    // Stop webcam
    webcam.srcObject.getVideoTracks().forEach((track) => {
        track.stop();
    });

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
});
