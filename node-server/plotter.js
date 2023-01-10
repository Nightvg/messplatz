const MAX_N = 300;
//Zu langsam? oder Laptop?


var ws = new WebSocket("ws://" + document.location.host + ":3000");
var charts = []
var clamp = (num, min, max) => Math.min(Math.max(num, min), max);
var lIndex = 0, 
    rIndex = 0;

ws.onmessage = function(message) {
    let data = JSON.parse(message.data);
    lIndex = clamp(lIndex--,0,MAX_N - 1);
    rIndex = clamp(rIndex--,0,MAX_N - 1);
    for(let i = 0; i < data.data.length; i++) {
        let graph = charts.find(elem => elem.config.options.plugins.title.text === data.names[i]);
        if (typeof graph === "undefined") {
            let node = document.createElement('canvas');
            node.id = data.names[i];
            node.with = 900;
            node.height = 200;
            document.body.appendChild(node); //TODO: den richtigen container finden
            let graph = new Chart(node.id, {
                type: "line",
                data: {
                    labels: [...Array(MAX_N).keys()],
                    datasets:[{
                        data: [data.data[i]],
                        spanGaps: true,
                        pointRadius: 0,
                        borderColor: "rgba(120,120,120,1)"
                    }]
                },
                options :{
                    normalized: true,
                    animation: false,
                    legend: {display: false},
                    plugins:{
                        title: {display:true, text: data.names[i]},
                        decimation: {
                            algorithm: 'lttb',
                            enabled: true,
                            samples: 100
                        }
                    },
                    scales: {
                        x: {
                            type: 'linear',
                            ticks: {
                                source: 'auto',
                                maxRotation: 0,
                                autoSkip: true
                            }
                        }
                    },
                    onClick: (e) => {
                        let pos = Chart.helpers.getRelativePosition(e, graph);
                        if (lIndex === 0) {
                            lIndex = Math.floor(pos.x)
                        } else {
                            rIndex = Math.floor(pos.x);
                            let c = document.querySelector(this).parentNode.closest('div.controle');
                            let dnode = document.createElement('canvas');
                            dnode.with = 400;
                            dnode.height = 200;
                            dnode.id = node.id + 'controle';
                            new Chart(dnode.id, {
                                type: 'line',
                                data: {
                                    datasets: [{
                                        labels: [...Array(rIndex - lIndex).keys()].map(i => i + lIndex),
                                        data: graph.data.datasets[0].data.slice(lIndex, rIndex),
                                        options: {legend: {display: false}}
                                    }]
                                }
                            });
                        }
                        
                    }
                }
            });
            charts.push(graph)
            graph.update()
        } else {
            if (graph.data.datasets[0].data.length > MAX_N - 1) {
                graph.data.datasets[0].data.shift()
            }
            graph.data.datasets[0].data.push(data.data[i])
            graph.update()
        }
    }
    //console.log(tmp);
        
};

ws.onclose = function(event) {
    console.log('Client disconnected');
};
