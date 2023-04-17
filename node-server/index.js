const { json } = require("express");
const express = require("express");

const PORT = process.env.PORT || 80;
const MAXLENGTH = 9e6;

const app = express();
var data = [];
var ind_start = 0;
var shifted = 0;

//SCRIPTS
app.use(express.json());
app.use('/scripts', express.static(__dirname + '/scripts'));
app.use('/amcharts', express.static(__dirname + '/amcharts'));

//ROUTING

//VIEW - ROOT
app.get('/view', (req, res) => {
    res.status(200).sendFile(__dirname + '/view.html');
});

app.get('/view_alt', (req, res) => {
    ind_start = 0;
    res.status(200).sendFile(__dirname + '/view_am.html');
});

//HTTP API - RECEIVE DATA
app.post('/data', (req, res) => {
    tmp = req.body;
    tmpData = Array(tmp.len).fill({});
    tmp.names.forEach((name, index) => {
        for(let i = 0; i < tmp.len; tmpData[i][name] = tmp.data[index][i++]);
    });
    console.log(tmpData);
    if(tmpData.length + data.length > 9e6)
    {
        data.shift(tmpData.length);
        shifted = tmpData.length;
    } 
    data = data.concat(tmpData);
    res.status(201).send('Successfully inserted data');
});

//HTTP API - POLLING REQ DATA
app.get('/data', (req, res) => {
    if(!data.length)
    {
        //DATA NOT AVAILABLE
        res.status(503).send('Data not available');
    }
    else
    {
        //DATA AVAILABLE
        res.status(200).json(data.slice(ind_start - shifted, data.length - 1));
        ind_start = data.length;
        shifted = 0;
    }
});

app.listen(PORT, () => {
  console.log(`Server listening on ${PORT}`);
});