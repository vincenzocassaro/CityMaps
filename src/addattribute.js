const config = window.CITYMAPS_CONFIG || {};
const animationDuration = config.animationDurationMs || 15000;
const drawDelay = config.drawDelayMs ?? 0;
const finalFrameHold = config.finalFrameHoldMs || 500;
const staggerSpan = 0.7;
const drawingWindow = animationDuration - drawDelay;
const pathDuration = drawingWindow * (1 - staggerSpan);

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
        path.classList.add("citymaps-animated-path");
        path.style.animationName = "citymaps-draw";
        path.style.animationDuration = `${pathDuration}ms`;
        path.style.animationDelay = `${drawDelay + stagger * drawingWindow}ms`;
        path.style.animationTimingFunction = "cubic-bezier(0, 0, 0.58, 1)";
        path.style.animationFillMode = "forwards";

        return { path, original };
    });
}

function restoreFinalStyle(paths) {
    for (const { path, original } of paths) {
        path.style.animation = "none";
        path.style.fill = original.fill;
        path.style.stroke = original.stroke;
        path.style.strokeWidth = original.strokeWidth;
        path.style.strokeDasharray = "none";
        path.style.strokeDashoffset = "0";
    }
}

window.addEventListener("load", () => {
    const svg = document.querySelector("svg");
    const paths = preparePaths(svg);
    svg.style.visibility = "visible";

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            svg.classList.add("citymaps-drawing");
            setTimeout(() => {
                restoreFinalStyle(paths);
                setTimeout(() => {
                    document.body.dataset.renderState = "complete";
                }, finalFrameHold);
            }, animationDuration);
        });
    });
});
