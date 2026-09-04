const config = window.CITYMAPS_CONFIG || {};
const animationDuration = config.animationDurationMs || 15000;
const drawDelay = config.drawDelayMs || 1000;

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

function drawFrame(paths, time) {
    const progress = Math.min(
        1,
        Math.max(0, (time - drawDelay) / (animationDuration - drawDelay)),
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

window.addEventListener("load", () => {
    const paths = preparePaths(document.querySelector("svg"));
    let startTime;

    function render(timestamp) {
        if (!startTime) {
            startTime = timestamp;
        }

        const elapsed = Math.min(timestamp - startTime, animationDuration);
        drawFrame(paths, elapsed);

        if (elapsed === animationDuration) {
            document.body.dataset.renderState = "complete";
            return;
        }

        requestAnimationFrame(render);
    }

    requestAnimationFrame(render);
});
