let handpose;
let video;
let predictions = [];
let canvas2;
let prevtop = null;
let prevleft = null;
let leftArr = [];
let topArr = [];
let leftAvg, topAvg;
let colr = 0;
let colb = 255;
let colg = 0;
let pointerX, pointerY, thumb, pinky;

function setup() {
    createCanvas(640, 480);
    canvas2 = createGraphics(width, height);
    // makesquares();
    video = createCapture(VIDEO);
    video.size(width, height);

    handpose = ml5.handpose(video, modelReady);

    // This sets up an event that fills the global variable "predictions"
    // with an array every time new hand poses are detected
    handpose.on("predict", (results) => {
        predictions = results;
    });

    // Hide the video element, and just show the canvas
    video.hide();
}

function modelReady() {
    console.log("Model ready!");
}

function draw() {
    //  background(0);

    image(video, 0, 0, width, height);
    image(canvas2, 0, 0);

    // We can call both functions to draw all keypoints and the skeletons
    drawKeypoints();
}

// A function to draw ellipses over the detected keypoints
function drawKeypoints() {
    for (let i = 0; i < predictions.length; i += 1) {
        const prediction = predictions[i];
        canvas2.strokeWeight(10);
        for (let j = 0; j < prediction.landmarks.length; j += 1) {
            const keypoint = prediction.landmarks[j];
            fill(0, 255, 0);
            noStroke();
            //   ellipse(keypoint[0], keypoint[1], 10, 10);
            if (j == 0) {
                thumb = keypoint[1];
            } else if (j == 4) {
                pinky = keypoint[1];
            } else if (j == 9) {
                pointerX = width - keypoint[0]; // flip the x-coordinate
                pointerY = keypoint[1];
            }
        }
        //If the hand is closed, then draw a line or pick a color
        if (thumb > pinky) {
            fill(0);
            ellipse(pointerX, pointerY, 20, 20);
            if (prevtop != null) {
                leftArr.push(pointerX);
                topArr.push(pointerY);
                if (leftArr.length > 10) {
                    leftArr.shift();
                    topArr.shift();
                }
                leftAvg = 0;
                topAvg = 0;
                for (let k = 0; k < leftArr.length; k += 1) {
                    leftAvg += leftArr[k];
                    topAvg += topArr[k];
                }
                leftAvg /= leftArr.length;
                topAvg /= topArr.length;
                canvas2.stroke(colr, colg, colb);
                canvas2.line(prevleft, prevtop, leftAvg, topAvg);
                prevleft = leftAvg;
                prevtop = topAvg;
            } else {
                prevleft = pointerX;
                prevtop = pointerY;
                colr = random(255);
                colg = random(255);
                colb = random(255);
            }
        } else {
            prevtop = null;
        }
    }
}
