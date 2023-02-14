var charts = [];
var copynode;

window.onload = () => {
    copynode = document.getElementsByClassName('grid-container')[0];
    document.body.removeChild(copynode);
    init();
}

function init() {
    $.ajax({
        url: "http://localhost/init",
        type: "GET",
        dataType: "json",
        success: (data) => {
            for(let i of data) {
                let tmpNode = copynode;
                let canvas = document.createElement('canvas');
                canvas.id = i;
                tmpNode.appendChild(canvas);
                document.body.appendChild(canvas);
            }
        }
    })
}
