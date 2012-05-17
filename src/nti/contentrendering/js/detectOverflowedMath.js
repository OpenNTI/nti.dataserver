if(phantom.args.length < 1){
	console.log('Usage: phantomjs getOverflowedMath.js page.html');
}

var page = require('webpage').create();
page.viewportSize =  {width: 730, height: 964}; //height is 1024 - 60
page.onConsoleMessage = function (msg) {
    console.log(' Message from page: ' + msg);
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
		page.injectJs( "jquery-1.7.2.min.js" );
		var overflowedMath = page.evaluate(findOverflowedMath);

		console.log(JSON.stringify(overflowedMath));
	}
	phantom.exit();
};

page.open(phantom.args[0], onPageOpen);
