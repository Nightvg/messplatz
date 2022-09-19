const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');

let sockets = [];
const wss = new WebSocket.WebSocketServer({port: 3000});

wss.on('connection', function(socket) {
  sockets.push(socket);
  console.log("Client connected");
  // When you receive a message, send that message to every socket.
  socket.on('message', function(msg) {
    //console.log(JSON.parse(msg));
    sockets.forEach(s => s.send(JSON.stringify(JSON.parse(msg))));
  });

  // When a socket closes, or disconnects, remove it from the array.
  socket.on('close', function() {
    sockets = sockets.filter(s => s !== socket);
    console.log('Client disconnected');
  });
});

var server = http.createServer(function (request, response) {
  fs.readFile('./' + request.url, function(err, data) {
    if (!err) {
      var dotoffset = request.url.lastIndexOf('.');
      var mimetype = dotoffset == -1
        ? 'text/plain'
        : {
            '.html' : 'text/html',
            '.ico' : 'image/x-icon',
            '.jpg' : 'image/jpeg',
            '.png' : 'image/png',
            '.gif' : 'image/gif',
            '.css' : 'text/css',
            '.js' : 'text/javascript'
            }[ request.url.substr(dotoffset) ];
      response.setHeader('Content-type' , mimetype);
      response.end(data);
      console.log( request.url, mimetype );
    } else {
      console.log('file not found: ' + request.url);
      response.writeHead(404, "Not Found");
      response.end();
    }
  });
})  

server.listen(80);
console.log("Webserver running")