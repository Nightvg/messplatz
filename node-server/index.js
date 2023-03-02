const express = require("express");

const PORT = process.env.PORT || 80;

const app = express();
var graphs = [];

//SCRIPTS
app.use(express.json());
app.use(express.static('scripts'));

//ROUTING

//VIEW - ROOT
app.get('/view', (req, res) => {
    res.sendFile(__dirname + '/view.html');
});

//VIEW - INIT GRAPHS
app.get('/init', (req, res) => {
    res.json({
        graphs: graphs
    })
});

//HTTP API - GET FILTER COEFF
app.get('/filter', (req, res) => {
    //TODO args richtig machen
    let options = {
        mode: 'json',
        args: [ '--wp '+req.query.wp, 
                '--wp '+req.query.ws, 
                '--gpass '+req.query.gpass, 
                '--gstop '+req.query.gstop,
                '--analog '+req.query.analog,
                '--fs '+req.query.fs
        ]
    };
    let graph = req.query.graph;
    
});

//HTTP API - RECEIVE DATA
app.put('/data', (req, res) => {
    data = req.body
    console.log(data)
    /*TODO -> 
        1. add data
        2. apply filter (if there is one)
        3. stream chunk of redrawn chart
    */


});

app.listen(PORT, () => {
  console.log(`Server listening on ${PORT}`);
});