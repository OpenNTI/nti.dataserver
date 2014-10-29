var system = require('system')

if(system.args.length < 2){
	console.log('Usage: phantomjs getOverflowedMath.js page.html');
}

var page = require('webpage').create();
page.viewportSize =	 {width: 730, height: 964}; //height is 1024 - 60
page.onConsoleMessage = function (msg, line, source) {
	//console.warn('// CONSOLE : ' + msg + ' at ' + line + ' in ' + source);
	//Silent. We expect just the overflows on output
};

var findOverflowedMath = function(){
	var overflowed = [];

	var maths = $('div.math').each(function(){
		var math = this;
		if( math.scrollWidth > math.clientWidth ){
			overflowed.push(math.id);
		}
	});

	return overflowed;
};

var onPageOpen = function(status){
	if(status !== 'success'){
		console.log('Unable to open page');
	}
	else {
		page.injectJs( "jquery-1.9.1.min.js" );
		var overflowedMath = page.evaluate(findOverflowedMath);

		console.log(JSON.stringify(overflowedMath));
	}
	phantom.exit();
};

page.open(system.args[1], onPageOpen);
