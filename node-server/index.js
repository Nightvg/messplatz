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
    res.status(200).sendFile(__dirname + '/view_am.html');
});

//HTTP API - RECEIVE DATA
app.post('/data', (req, res) => {
    tmp = req.body;
    tmp.names.forEach((element, index) => {
        //TODO -> Change Structure of data from: obj[key:list[values], key:list[values]] to: list[obj[key:value, key:value]]
        //check whether named value already exists in 'data'
        if(Object.hasOwn(data, element))
        {
            //Concat values if so, max length of MAXLENGTH
            data[element].data = data[element].data.concat(tmp.data[index]);
            if(data[element].data.length >= MAXLENGTH)
            {
                to_shift = data[element].data.length - MAXLENGTH;
                data[element].data.shift(to_shift);
                data[element].shift += MAXLENGTH - to_shift;
            }
        }
        else
        {
            //Set values if not
            data[element] = {
                data:Array.of(tmp.data[index]).flat(),
                ind:0,
                shift:0,
            }
        }
    });
    res.status(201).send('Successfully inserted data');
});

//HTTP API - POLLING REQ DATA
app.get('/data', (req, res) => {
    if(data && Object.keys(data).length === 0 && Object.getPrototypeOf(data) === Object.prototype)
    {
        //DATA NOT AVAILABLE
        res.status(503).send('Data not available');
    }
    else
    {
        //DATA AVAILABLE
        tmpObj = {};
        Object.entries(data).forEach(([key, obj]) => {
            tmpObj[key] = obj.data.slice(obj.ind - obj.shift, obj.data.length - 1);
            data[key].shift = 0;
            data[key].ind = data[key].data.length - 1;
        });
        res.status(200).json(tmpObj);
    }
});

app.listen(PORT, () => {
  console.log(`Server listening on ${PORT}`);
});