console.log("ciao")

// function addAnimate(path) {

//     var length = path.getTotalLength();

//     path.setAttribute("stroke-dasharray", length + ' ' + length);
//     path.setAttribute("stroke-dashoffset", length);
//     path.style.animation = "strokeoffset 9500ms ease-in-out 0ms forwards";

//     // const a = document.createElement('animate');

//     // a.setAttribute("attributeName", "stroke-dashoffset");
//     // a.setAttribute("attributeType", "XML");
//     // a.setAttribute("dur", "10s");
//     // a.setAttribute("values", length + ";0;" + length);

//     // path.appendChild(a);
// }

// function simulatePathDrawing(path) {
//     // var path = document.querySelector('.squiggle-animated path');
//     var length = path.getTotalLength();
//     // Clear any previous transition
//     path.style.transition = path.style.WebkitTransition = 'none';
//     // Set up the starting positions
//     path.style.strokeDasharray = length + ' ' + length;
//     path.style.strokeDashoffset = length;

//     // Trigger a layout so styles are calculated & the browser
//     // picks up the starting position before animating
//     path.getBoundingClientRect();
//     // Define our transition
//     path.style.transition = path.style.WebkitTransition = 'stroke-dashoffset 9.5s ease-in-out';
//     // Go!
//     //path.style.transitionProperty = 'stroke-dashoffset';
//     //path.style.transitionDuration = '9.5s';
//     //path.style.transitionTimingFunction = "ease-in-out";
//     //path.style.transitionDelay = '0';

//     path.style.strokeDashoffset = '0';
//     path.style.strokeWidth = '1px';
//     path.style.fill = 'rgba(255,255,0,.12)';
// }




/* Utils */

function svg2canvas(svg, ctx, callback) {
    const serialized = new XMLSerializer().serializeToString(svg),
        url = URL.createObjectURL(new Blob([serialized], { type: "image/svg+xml" }));

    const img = new Image();
    img.onload = function () {
        ctx.drawImage(img, 0, 0);
        callback();
    };
    img.src = url;
}


class CanvasRecorder {
    constructor(options) {
        const canvas = options.canvas,
            callback = options.callback;

        let framerate = options.framerate || 0;
        //Setting the framerate to 0 lets us render each frame manually through requestFrame(),
        //but only if the browser supports it (2018: Only Chrome, Firefox behind a flag):
        //https://developer.mozilla.org/en-US/docs/Web/API/CanvasCaptureMediaStreamTrack#Methods
        this.hasRequestFrame = (typeof CanvasCaptureMediaStreamTrack !== 'undefined') &&
            ('requestFrame' in CanvasCaptureMediaStreamTrack.prototype);
        console.log('requestFrame() support', this.hasRequestFrame);
        if ((framerate === 0) && !this.hasRequestFrame) {
            //Without the manual control over framerate, just use a suitable default:
            framerate = 24;
        }

        //https://developer.mozilla.org/en-US/docs/Web/API/CanvasCaptureMediaStreamTrack/requestFrame#Example
        const stream = canvas.captureStream(framerate),
            track = stream.getVideoTracks && stream.getVideoTracks()[0];

        const chunks = [],
            recorder = new MediaRecorder(stream, { mimeType: "video/webm" });

        recorder.ondataavailable = function (e) {
            const blob = e.data;
            if (blob && blob.size) { chunks.push(blob); }
        };

        recorder.onstop = (e) => {
            //console.log('stop', e);
            const url = URL.createObjectURL(new Blob(chunks, { type: "video/webm" }));
            callback(url);
        };

        this.recorder = recorder;
        this.track = track;
    }

    start() {
        this.recorder.start();
    }

    stop() {
        this.recorder.stop();
    }

    requestFrame() {
        if (!this.hasRequestFrame) { return; }
        this.track.requestFrame();
    }
}

function downloadURI(uri, name) {
    var link = document.createElement("a");
    link.download = name;
    link.href = uri;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    delete link;
}

window.addEventListener('load', (event) => {
    console.log('page is fully loaded');

    // var list = $('.squiggle-animated path')

    const svg = document.querySelector('#Content-R'),
        canv = document.querySelector('#rendered'),
        ctx = canv.getContext('2d');

    // for (let index = 0; index < list.length; index++) {
    //     const element = list[index];
    //     if (index != 0 && index != 1 && index != 2) {
    //         // simulatePathDrawing(element);
    //         addAnimate(element);
    //     }
    //     // simulatePathDrawing(element);
    // }


    //Prepare a canvas on which to render the frames for our video
    canv.width = svg.clientWidth;
    canv.height = svg.clientHeight;
    const recorder = new CanvasRecorder({
        canvas: canv,
        callback: url => {


            const video = document.body.appendChild(document.createElement('video'));
            video.src = url;
            video.controls = true;
            video.autoplay = true;

            downloadURI(url, "helloWorld.mov");
        },
    });


    // //Find all animated elements, and save their original animation-delay:
    var animed = Array.from(document.querySelectorAll('*')).filter(x => x.style.animationName);
    animed.forEach(x => {
        var css = x.style,
            anim = css.animationName,
            delay = css.animationDelay;

        console.log(x.id, anim, delay);
        x.__originalDelay = delay.match(/\d/) ? delay : '0s';
    });


    // //Loop through all animated elements, and update their animation-delay.
    // //Together with "animation-play-state: paused", this freezes the animation at the specified time.
    function freeze(time) {
        animed.forEach(x => {
            x.style.animationPlayState = 'paused';
            x.style.animationDelay = `calc(${x.__originalDelay} - ${time}ms)`;
        });
    }
    var animed = Array.from(document.querySelectorAll('*')).filter(x => x.style.transition);

    // function myfreeze() {
    //     console.log("myfreeze");

    //     animed.forEach(x => {
    //         var computedStyle = window.getComputedStyle(x);
    //         var strokeDashoffset = computedStyle.getPropertyValue('strokeDashoffset');

    //         x.style.strokeDashoffset = strokeDashoffset;
    //     });


    // }


    function render(time, frame, callback) {
        //20fps is more than enough..
        // if ((frame % 3) !== 1) { callback(); return; }

        console.log('rendering', frameNum, time);
        freeze(time);
        svg2canvas(svg, ctx, () => {
            //console.log('  ..requesting');
            recorder.requestFrame();
            callback();
        });
    }

    let startT, frameNum = 0;
    function renderLoop(t) {
        if (!t) { requestAnimationFrame(renderLoop); return; }

        if (!startT) {
            startT = t;
            recorder.start();
        }
        let animTime = (t - startT);

        //The complete animation lasts around 10 seconds:
        if (animTime > 10000) {
            recorder.stop();
            return;
        }

        frameNum++;
        render(animTime, frameNum, () => requestAnimationFrame(renderLoop));
    };

    renderLoop();

    //const freezer = document.querySelector('#freezer');
    //freezer.oninput = (e) => freeze(freezer.value * 1000);
    //freezer.oninput();

});
