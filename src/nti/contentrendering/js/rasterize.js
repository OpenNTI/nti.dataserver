var system = require('system')

//Copied from http://code.google.com/p/phantomjs/wiki/QuickStart
var page = require('webpage').create(),
	address, output, size;
page.onConsoleMessage = function (msg, line, source) {
	// Silent. Our caller, contentthumbnails.py, expects no output
};

if( system.args.length < 3 ) {
	console.log('Usage: rasterize.js URL filename [width px] [height px] [zoom]');
	phantom.exit();
}
else {
	address = system.args[1];
	output = system.args[2];

	var the_height = 600;
	var the_width = 600;
	if( system.args.length > 3 ) {
		the_width = system.args[3];
	}
	if( system.args.length > 4 ) {
		the_height = system.args[4];
	}
	// The viewportSize is how the page is laid out
	page.viewportSize = { width: 600, height: 600 };
	// The clipRest is the visible portion of the window,
	// and also the pixel dimensions of the render image.
	// by making them the same, we let the zoom factor
	// directly controll the apparent scale
	page.clipRect = { top: 0, left: 0, width: the_width, height: the_height };

	if( system.args.length > 5 ) {
		// The zoomfactor is the percent of the viewport
		// that fits within the clip rest
		page.zoomFactor = system.args[5];
	}

	page.open(address, function (status) {
		if (status !== 'success') {
			console.log('Unable to load the address!');
		} else {
			//IF there is no background color specified phantomjs renders it transperant
			page.evaluate(function(){
				document.body.style.backgroundColor='white';
			});

			page.render(output);

		}
		phantom.exit();
	});
}
