const n = 900; //30 Sekunden
var datas = new Array()
var scales = Array.from([]) 
var svgs = Array.from(document.getElementsByTagName('svg'));
    margin = {top: 20, right: 20, bottom: 20, left: 40};
    height = document.getElementsByTagName('svg')[0].height.baseVal.value;
    width = document.getElementsByTagName('svg')[0].width.baseVal.value;

        
var x = d3.scaleLinear()
    .domain([0, n - 1])
    .range([0, width]);

var y = d3.scaleLinear()
    .domain([0, 5000])
    .range([height, 0]);

var line = d3.line()
    .x(function(d, i) { return x(i); })
    .y(function(d, i) { return y(d); });


window.onload = function(){
    document.querySelectorAll('div.controle').forEach(elem => {
        let controller = elem.querySelector('input');
        controller.addEventListener('input', function() {
            this.parentElement.querySelector('p').innerHTML = "Sekunden: " + this.value;
        });   
        controller.addEventListener('change', function(){
 
        });       
    });
    document.querySelectorAll('div.view').forEach(elem => {
        elem.id = elem.parentElement.id + "-view"; 
    });
};

for(let i = 0; i < 5; i++){
    datas.push(new Array(n).fill(0));
}


function tick(index, data) {
    datas[index].push(data);
    d3.select(paths[index])
        .attr("d", line)
        .attr("transform", null)
        .transition()
        .attr("transform", "translate(" + x(-1) + ",0)");
    datas[index].shift();

}

var yscales = new Array();
for(let i = 0; i < 5; i++){
    let t_scale = d3.scaleLinear()
        .domain(d3.min(datas[i]), d3.max(datas[i]))
        .range(height, 0);
    yscales.push(t_scale);
}

var xscales = new Array();
for(let i = 0; i < 5; i++){
    let t_scale = d3.scaleLinear()
        .domain(0, n - 1)
        .range(0, width);
    xscales.push(t_scale);
}

svgs.forEach((svg, index) => {
    svg = d3.select(svg),
    svg.attr("width") - margin.left - margin.right,
    svg.attr("height") - margin.top - margin.bottom,
    g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    g.append("defs").append("clipPath")
        .attr("id", "clip")
        .append("rect")
        .attr("width", width)
        .attr("height", height);

    g.append("g")
        .attr("class", "axis axis--x")
        .call(d3.axisBottom(x));

    g.append("g")
        .attr("class", "axis axis--y")
        .call(d3.axisLeft(y));

    g.append("g")
        .attr("clip-path", "url(#clip)")
        .append("path")
        .data([datas[index]])
        .attr("class", "line")
});

var paths = Array.from(document.getElementsByClassName('line'))
var ws = new WebSocket("ws://" + document.location.host + ":3000");

ws.onopen = function(e) {
    console.log("Client connected")
};

ws.onmessage = function(message) {
    //console.log(message.data);
    let tmp = JSON.parse(message.data);
    tmp.data.forEach((elem, index) => {
        tick(index, elem);
    });
    //console.log(tmp);
    // for(let i = 0; i < 5; i++){
    //     tick(i, tmp.data[i]);
    // };
};

ws.onclose = function(event) {
    
};
