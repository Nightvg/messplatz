const n = 900; //30 Sekunden
var modules = 5;
var old_modules = 5;
var devices = [{name: 'microcontroller', start: 0}]
var deviceGet = (name) => {for(let elem of devices){if(elem.name == name){return elem}} return null};
var resetXAxis = () => {
    x.domain([0,n+100]);
    Array.from(document.querySelectorAll('.axis--x')).forEach(elem => {
        d3.select(elem).transition(500).call(d3.axisBottom(x));
    });
};
var idleTimeout;
function idled() { idleTimeout = null; };

var init_graph = null;
var margin = {top: 20, right: 20, bottom: 20, left: 40},
    height = document.querySelector('svg.data').height.baseVal.value,
    width = document.querySelector('svg.data').width.baseVal.value,
    _width = 400,
    ws = new WebSocket("ws://" + document.location.host + ":3000"),
    datas = new Array(),
    t_datas = new Array(),
    paths = new Array(),
    yscales = new Array(),
    pathnames = new Array(),
    t_data = new Array(),
    graphnames = ['EMG1','EMG2','ECG','BR','EDA'],
    brush = d3.brush()                   // Add the brush feature using the d3.brush function
        .on("end", brushed);    

var x = d3.scaleLinear()
    .domain([0, n + 100])
    .range([0, width]),
    x_global = d3.scaleLinear()
    .domain([0, n + 100])
    .range([0, width]),
    _x = d3.scaleLinear()
    .domain([0, 900])
    .range([0, _width]);

var y = d3.scaleLinear()
    .domain([0, 5000])
    .range([height, 0]);

function brushed({selection}) {
    if (selection) {
        let index = Array.from(document.querySelectorAll('.brush')).findIndex(node => node.isEqualNode(this));
        var [[x0, y0], [x1, y1]] = selection;
        x0 = Math.floor(x0);
        x1 = Math.floor(x1);
        y0 = Math.floor(y0);
        y1 = Math.floor(y1);
        t_datas[index] = datas[index].slice(x0, x1);
        _x.domain([x0,x1])
        let _y = d3.scaleLinear()
            .domain([y0-100, y1+100])
            .range([height, 0]);
        let div = document.querySelectorAll('div.controle')[index];
        if(div.children.length == 0) {
            let svg = d3.select(div).append("svg")
                .attr("height",height)
                .attr("width",_width)
                .attr("class","partly");
            let g1 = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");
            g1.append("defs").append("clipPath")
                .attr("id", "clip")
                .append("rect")
                .attr("width", _width)
                .attr("height", height);
        
            g1.append("g")
                .attr("class", "axis axis--x");
        
            g1.append("g")
                .attr("class", "axis axis--y");
        
            let line1 = g1.append("g")
                .attr("clip-path", "url(#clip)");
            line1.append("path")
                .data([t_datas[index]])
                .attr("class", "line");
            console.log('test')    
        } 
        d3.select(div.querySelector("svg")).style("visibility", "");
        d3.select(div.querySelector('.axis--x')).call(d3.axisBottom(_x));
        d3.select(div.querySelector('.axis--y')).call(d3.axisLeft(yscales[index]));    
        d3.select(div.querySelector('.line')).attr('d', d3.line()
            .x(function(d, i) { return _x(i); })
            .y(function(d, i) { return _y(d); })
        );
        
    } 
    else {
       // d3.select(this.closest('div.graph').closest('.partly')).style("visibility","hidden"); 
       // this.closest('svg').call(brush.move, null)
    }
}

window.onload = function(){
    for(let i = 0; i < modules; i++){
        datas.push(new Array(n).fill(0));
        t_datas.push(new Array(n).fill(0));
        let t_scale = d3.scaleLinear()
            .domain([0, 5000])
            .range([height, 0]);
        yscales.push(t_scale);
        if(i > 0){
            let copynode = document.querySelector('div.graph').cloneNode(true);
            document.body.appendChild(copynode);
        }
    }
    Array.from(document.querySelectorAll('svg.data')).forEach((svg, index) => {
        //console.log(svg);
        svg = d3.select(svg),
        svg.on("dblclick",function(){
            this.closest('div.graph').querySelector('div.controle>svg').style.visibility = 'hidden';
        });
        svg.attr("width") - margin.left - margin.right,
        svg.attr("height") - margin.top - margin.bottom,
        g = svg.append("g").attr("transform", "translate(" + margin.left + "," + 0 + ")");
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
    
        let line = g.append("g")
            .attr("clip-path", "url(#clip)");
        line.append("path")
            .data([datas[index]])
            .attr("class", "line line-main");
        line.append("g")
            .attr('class', 'brush')
            .call(brush);

        svg.append("text")
            .attr("class","headline")
            .attr("x", width/2)
            .attr("y", margin.top - 5)
            .attr("text-anchor", "middle")
            .style("font-size", "16px")
            .text(graphnames[index]);
    });
    init_graph = document.querySelector('div.graph').cloneNode(true);
    d3.selectAll('svg.detail');
    paths = document.querySelectorAll('.line-main');
    pathnames = document.querySelectorAll('.headline');
};

function updateGraphs() {
    for(let i = old_modules; i < modules; i++){
        datas.push(new Array(n).fill(0));
        t_datas.push(new Array(n).fill(0));
        let t_scale = d3.scaleLinear()
            .domain([0, 5000])
            .range([height, 0]);
        yscales.push(t_scale);
        let copynode = init_graph.cloneNode(true);
        d3.select(copynode.querySelector('svg')).on("dblclick",function(){
            x.domain(d3.extent(datas[i], function(d) { return d; }));
            d3.select(copynode.querySelector('.axis--x')).transition().call(d3.axisBottom(x));
            d3.select(copynode.querySelector('.line-main'))
                .transition()
                .attr("d", d3.line()
                    .x(function(d, i) { return x(i); })
                    .y(function(d, i) { return yscales[index](d); }));
        });
        document.body.appendChild(copynode);
        d3.select(copynode.querySelector('.healine')).text(graphnames[i]);
    }
    old_modules = modules;
    paths = document.querySelectorAll('.line-main');
    pathnames = document.querySelectorAll('.headline');
    Array.from(pathnames).forEach((elem,index) => {
        d3.select(elem).text(graphnames[index]);
    });
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
        .attr("transform", "translate("+x_global(-1)+",0)");
    datas[index].shift();
    yscales[index].domain([d3.min(datas[index]) - 300, d3.max(datas[index]) + 300]).range([height, 0]);
    d3.select(document.querySelectorAll('.axis--y')[index]).call(d3.axisLeft(yscales[index]));
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
        Array.from(tmp.names).forEach(elem => {
            graphnames.push(elem);
        });
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
