const config = window.CITYMAPS_CONFIG || {};
const animationDuration = config.animationDurationMs || 15000;
const drawDelay = config.drawDelayMs ?? 0;
const finalFrameHold = config.finalFrameHoldMs || 500;
const staggerSpan = 0.7;

function easeOut(progress) {
    return 1 - (1 - progress) * (1 - progress);
}

function preparePaths(svg) {
    const paths = Array.from(svg.querySelectorAll("path"));

    return paths.slice(3, -2).map((path, index) => {
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

        const stagger = ((index * 0.61803398875) % 1) * staggerSpan;
        return { path, length, original, stagger };
    });
}

function drawFrame(paths, time) {
    const progress = Math.min(
        1,
        Math.max(0, (time - drawDelay) / (animationDuration - drawDelay)),
    );
    for (const { path, length, original, stagger } of paths) {
        const pathProgress = Math.min(
            1,
            Math.max(0, (progress - stagger) / (1 - staggerSpan)),
        );
        const offsetScale = 1 - easeOut(pathProgress);
        path.style.strokeDashoffset = `${length * offsetScale}`;

        if (progress === 1) {
            path.style.fill = original.fill;
            path.style.stroke = original.stroke;
            path.style.strokeWidth = original.strokeWidth;
            path.style.strokeDasharray = "none";
        }
    }
}

window.addEventListener("load", () => {
    const paths = preparePaths(document.querySelector("svg"));
    let startTime;
    let finishScheduled = false;

    function render(timestamp) {
        if (!startTime) {
            startTime = timestamp;
        }

        const elapsed = Math.min(timestamp - startTime, animationDuration);
        drawFrame(paths, elapsed);

        if (elapsed === animationDuration) {
            if (!finishScheduled) {
                finishScheduled = true;
                setTimeout(() => {
                    document.body.dataset.renderState = "complete";
                }, finalFrameHold);
            }
            return;
        }

        requestAnimationFrame(render);
    }

    requestAnimationFrame(render);
});
