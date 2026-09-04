const ANIMATION_DURATION_MS = 15000;
const DRAW_DELAY_MS = 1000;

function easeInOut(progress) {
    return progress < 0.5
        ? 4 * progress * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 3) / 2;
}

function preparePaths(svg) {
    const paths = Array.from(svg.querySelectorAll("path"));

    return paths.slice(3, -2).map(path => {
        const computed = getComputedStyle(path);
        const length = path.getTotalLength();
        const original = {
            fill: path.style.fill || computed.fill,
            stroke: path.style.stroke || computed.stroke,
            strokeWidth: path.style.strokeWidth || computed.strokeWidth,
        };
        const hasStroke = original.stroke && original.stroke !== "none";
        const strokeWidth = Number.parseFloat(original.strokeWidth);

        path.style.fill = "transparent";
        path.style.stroke = hasStroke ? original.stroke : "#2f3737";
        path.style.strokeWidth = strokeWidth > 0 ? original.strokeWidth : "0.75";
        path.style.strokeDasharray = `${length} ${length}`;
        path.style.strokeDashoffset = `${length}`;

        return { path, length, original };
    });
}

function setFrame(paths, time) {
    const progress = Math.min(
        1,
        Math.max(0, (time - DRAW_DELAY_MS) / (ANIMATION_DURATION_MS - DRAW_DELAY_MS)),
    );
    const offsetScale = 1 - easeInOut(progress);

    for (const { path, length, original } of paths) {
        path.style.strokeDashoffset = `${length * offsetScale}`;

        if (progress === 1) {
            path.style.fill = original.fill;
            path.style.stroke = original.stroke;
            path.style.strokeWidth = original.strokeWidth;
            path.style.strokeDasharray = "none";
        }
    }
}

function svgToCanvas(svg, context, callback) {
    const serialized = new XMLSerializer().serializeToString(svg);
    const url = URL.createObjectURL(
        new Blob([serialized], { type: "image/svg+xml" }),
    );
    const image = new Image();

    image.onload = () => {
        context.clearRect(0, 0, context.canvas.width, context.canvas.height);
        context.drawImage(image, 0, 0);
        URL.revokeObjectURL(url);
        callback();
    };
    image.onerror = error => {
        URL.revokeObjectURL(url);
        console.error("Could not render SVG frame", error);
        callback();
    };
    image.src = url;
}

class CanvasRecorder {
    constructor(canvas, callback) {
        let framerate = 0;
        this.hasRequestFrame =
            typeof CanvasCaptureMediaStreamTrack !== "undefined" &&
            "requestFrame" in CanvasCaptureMediaStreamTrack.prototype;

        if (!this.hasRequestFrame) {
            framerate = 24;
        }

        const stream = canvas.captureStream(framerate);
        this.track = stream.getVideoTracks()[0];
        this.chunks = [];
        this.recorder = new MediaRecorder(stream, { mimeType: "video/webm" });
        this.recorder.ondataavailable = event => {
            if (event.data && event.data.size) {
                this.chunks.push(event.data);
            }
        };
        this.recorder.onstop = () => {
            callback(
                URL.createObjectURL(
                    new Blob(this.chunks, { type: "video/webm" }),
                ),
            );
        };
    }

    start() {
        this.recorder.start();
    }

    stop() {
        this.recorder.stop();
    }

    requestFrame() {
        if (this.hasRequestFrame) {
            this.track.requestFrame();
        }
    }
}

function download(uri, filename) {
    const link = document.createElement("a");
    link.download = filename;
    link.href = uri;
    link.click();
}

window.addEventListener("load", () => {
    const svg = document.querySelector("svg");
    const canvas = document.querySelector("#rendered");
    const context = canvas.getContext("2d");
    const paths = preparePaths(svg);
    const filename = decodeURIComponent(location.pathname.split("/").pop())
        .replace(/\.html$/, "") || "citymap";

    canvas.width = svg.clientWidth;
    canvas.height = svg.clientHeight;

    const recorder = new CanvasRecorder(canvas, url => {
        const video = document.body.appendChild(document.createElement("video"));
        video.src = url;
        video.controls = true;
        video.autoplay = true;
        download(url, `${filename}.webm`);
    });

    let startTime;
    let stopped = false;

    function renderLoop(timestamp) {
        if (!startTime) {
            startTime = timestamp;
            recorder.start();
        }

        const animationTime = timestamp - startTime;
        const frameTime = Math.min(animationTime, ANIMATION_DURATION_MS);
        setFrame(paths, frameTime);
        svgToCanvas(svg, context, () => {
            recorder.requestFrame();

            if (animationTime >= ANIMATION_DURATION_MS) {
                if (!stopped) {
                    stopped = true;
                    recorder.stop();
                }
                return;
            }

            requestAnimationFrame(renderLoop);
        });
    }

    requestAnimationFrame(renderLoop);
});
