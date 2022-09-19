const n = 900; //30 Sekunden
var modules = 5;
var old_modules = 5;
var devices = [{name: 'microcontroller', start: 0}]
var deviceGet = (name) => {for(let elem of devices){if(elem.name == name){return elem}} return null};
var init_graph = document.querySelector('div.graph').cloneNode(true);
var margin = {top: 20, right: 20, bottom: 20, left: 40},
    height = document.querySelector('svg').height.baseVal.value,
    width = document.querySelector('svg').width.baseVal.value,
    ws = new WebSocket("ws://" + document.location.host + ":3000"),
    datas = new Array(),
    paths = new Array(),
    yscales = new Array();
        
var x = d3.scaleLinear()
    .domain([0, n + 100])
    .range([0, width]);

var y = d3.scaleLinear()
    .domain([0, 5000])
    .range([height, 0]);

window.onload = function(){
    for(let i = 0; i < modules; i++){
        datas.push(new Array(n).fill(0));
        let t_scale = d3.scaleLinear()
            .domain([0, 5000])
            .range([height, 0]);
        yscales.push(t_scale);
        if(i > 0){
            let copynode = document.querySelector('div.graph').cloneNode(true);
            document.body.appendChild(copynode);
        }
    }
    Array.from(document.querySelectorAll('svg')).forEach((svg, index) => {
        //console.log(svg);
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
    paths = document.querySelectorAll('.line');
    document.querySelectorAll('div.controle > div > input[type="range"]').forEach((controller, index) => {
        controller.addEventListener('input', function() {
            this.parentElement.querySelector('p').innerHTML = this.name + this.value;
        });   
        controller.addEventListener('change', function(){
            // yscales[Math.floor(index/2)].domain([])
            // d3.select(this.closest('div.graph').querySelector('div.view>svg>g>g.axis--y')).call(d3.axisLeft(yscales[Math.floor(index / 2)]))
        });       
    });
};

function updateGraphs() {
    for(let i = old_modules; i < modules; i++){
        datas.push(new Array(n).fill(0));
        let t_scale = d3.scaleLinear()
            .domain([0, 5000])
            .range([height, 0]);
        yscales.push(t_scale);
        let copynode = init_graph.cloneNode(true);
        document.body.appendChild(copynode);
        svg = d3.select(copynode.querySelector('svg')),
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
            .data([datas[i]])
            .attr("class", "line");
    }
    old_modules = modules;
    paths = document.querySelectorAll('.line');
}

function tick(index, data) {
    let line = d3.line()
        .x(function(d, i) { return x(i); })
        .y(function(d, i) { return yscales[index](d); });
    datas[index].push(data);
    d3.select(paths[index])
        .attr("d", line)
        .attr("transform", null)
        .transition()
        .attr("transform", "translate(" + x(-1) + ",0)");
    datas[index].shift();
    yscales[index].domain([d3.min(datas[index]) - 300, d3.max(datas[index]) + 300]).range([height, 0]);
    d3.select(document.querySelectorAll('.axis--y')[index]).call(d3.axisLeft(yscales[index]))
}

ws.onopen = function(e) {
    console.log("Connected to server")
};

ws.onmessage = function(message) {
    //console.log(message.data);
    let tmp = JSON.parse(message.data);
    let tmp_device = deviceGet(tmp.device)
    if(!tmp_device){
        devices.push({name: tmp.device, start: modules});
        modules += tmp.data.length;
        updateGraphs();
    }
    else{
        tmp.data.forEach((elem, index) => {
            tick(index + tmp_device.start, elem);
        });    
    }
};

ws.onclose = function(event) {
    console.log('Client disconnected');
};
