const express = require("express");

const PORT = process.env.PORT || 80;

const app = express();
var graphs = 0;

//SCRIPTS

app.use(express.static('scripts'));

//ROUTING

app.get('/view', (res, req) => {
    res.sendFile(__dirname + '/view.html');
});

app.get('/plots', (res, req) => {
    res.json({
        graphs: null
    })
});

app.post('/plots', (res, req) => {
    req = JSON.parse(req.body)
});

app.listen(PORT, () => {
  console.log(`Server listening on ${PORT}`);
});