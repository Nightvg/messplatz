const express = require("express");

const PORT = process.env.PORT || 80;

const app = express();
var data;

//SCRIPTS
app.use(express.json());
app.use(express.static('scripts'));

//ROUTING

//VIEW - ROOT
app.get('/view', (req, res) => {
    res.sendFile(__dirname + '/view.html');
});

//HTTP API - RECEIVE DATA
app.post('/data', (req, res) => {
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