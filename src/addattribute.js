function addAttribbute(path) {

    var length = path.getTotalLength();

    path.setAttribute("stroke-dasharray", length + ' ' + length);
    path.setAttribute("stroke-dashoffset", length);
    path.setAttribute("fill-desired", path.style.fill)
    path.style.fill = "#00000000"
    path.style.animation = "strokeoffset 7000ms ease-in-out 1 1000ms normal forwards running"
}

window.addEventListener('load', (event) => {
    var list = $('path');

    for (let index = 0; index < list.length; index++) {
        const element = list[index];
        if (index != 0 && index != 1 && index != 2 && index != list.length && index != list.length - 1 && index != list.length - 2) {
            addAttribbute(element);
        }
    }

    console.log("finivu");
})