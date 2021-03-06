var p = require("child_process").exec;
var server = require("./server");
var router = require("./router");
var requestHandlers = require("./requestHandlers");

var handle = {}
handle["/"] = requestHandlers.start;
handle["/makeDrink"] = requestHandlers.makeDrink;
handle["/image"] = requestHandlers.image;
handle["/recipes"] = requestHandlers.recipes;
handle["/getIngredients"] = requestHandlers.getIngredients;
handle["/drinkQueue"] = requestHandlers.drinkQueue;
handle["/finishedQueue"] = requestHandlers.finishedQueue;
handle["/js"] = requestHandlers.js;
handle["/css"] = requestHandlers.css;
handle["/admin"] = requestHandlers.admin;

GLOBAL.orderNum = 0;

process.on('SIGINT', function(){
	console.log('\n\nCleaning up Server then shutting down.\n\n');

	p('rm -f ../controller/Orders/*.order; rm -f ../controller/Admin/*.command; rm -f ../controller/OrdersCompleted/*.order', function(){});

	process.exit();
});

server.start(router.route, handle, process.argv[2]);
