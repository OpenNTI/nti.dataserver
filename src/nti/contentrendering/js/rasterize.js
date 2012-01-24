//Copied from http://code.google.com/p/phantomjs/wiki/QuickStart
var page = require('webpage').create(),
    address, output, size;

if (phantom.args.length < 2 || phantom.args.length > 3) {
    console.log('Usage: rasterize.js URL filename');
    phantom.exit();
} else {
    address = phantom.args[0];
    output = phantom.args[1];
    page.viewportSize = { width: 720, height: 1004 };
	page.clipRect = { top: 0, left: 0, width: 720, height: 1004 };

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
