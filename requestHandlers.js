var process = require("child_process").exec;
var querystring = require("querystring");
var fs = require("fs");

function start(response, postData, getData){
	console.log("Request handler 'start' was called.");
 
	process('cat ./webApp/index.html', function(error, stdout){
		response.writeHead(200, {"Content-Type": "text/html"});
		response.write(stdout);
		response.end();
	});
}// start

function helloWorld(response, postData, getData){
    console.log("Request handler 'helloWorld' was called.");
    
    process('./testCode/helloWorld ' + getData['name'], function(error, stdout){
        console.log('stdout: ' + stdout);

        response.writeHead(200, {'Content-Type': 'text/plain'});
        response.end(stdout);
    });
}// helloWorld

function image(response, postData, getData){
	console.log("Request handler 'image' was called.");

	var img = fs.readFileSync('./webApp/' + getData['name']);

	response.writeHead(200, {'Content-Type': 'image/png'});
	response.end(img, 'binary');
}// image

function recipes(response, postData, getData){
    console.log("Request handler 'recipes' was called.");
    
    process('cat ./webApp/recipes.html', function(error, stdout){
        //console.log('stdout: ' + stdout);

        response.writeHead(200, {'Content-Type': 'text/plain'});
        response.end(stdout);
    });// process
}// recipes

exports.start = start;
exports.helloWorld = helloWorld;
exports.image = image;
exports.recipes = recipes;