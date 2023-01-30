async function startWebcam() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('video-canvas');
    const context = canvas.getContext('2d');

    // Load the handtrack model
    const model = await handTrack.load();

    // Access the webcam and start prediction
    const webcam = await handTrack.startVideo(video);

    let isDrawing = false;
    let x, y;

    while (true) {
        const predictions = await model.detect(video);

        if (predictions.length > 0 && predictions[0].bbox[2] > 50) {
            // If hand is detected and its width is larger than 50
            const handBox = predictions[0].bbox;
            x = handBox[0] + handBox[2] / 2;
            y = handBox[1] + handBox[3] / 2;

            // Start drawing if hand is detected for the first time
            if (!isDrawing) {
                context.beginPath();
                context.moveTo(x, y);
                isDrawing = true;
            } else {
                context.lineTo(x, y);
                context.stroke();
            }
        } else if (isDrawing) {
            // Stop drawing if hand is not detected
            isDrawing = false;
        }

    }
}

startWebcam();
