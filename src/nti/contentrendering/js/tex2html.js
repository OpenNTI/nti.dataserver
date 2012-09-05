if(phantom.args.length < 1){
	console.log('Usage: phantomjs tex2html.js page.html');
}

var page = require('webpage').create();
page.viewportSize =  {width: 730, height: 964}; //height is 1024 - 60

page.onConsoleMessage = function(msg){
	if (msg === 'Exit process'){
		phantom.exit();
	}
	console.log(msg);
};

var processPage = function(){
	MathJax.Hub.Queue(function()
	{
		jQuery.fn.outerhtml=function outerHTML()
		{
			return jQuery("&lt;p&gt;").append(this.eq(0).clone()).html();
		};


		$(".tex2jax_process").each(function()
		{
			var span = $(this);
    		span.children("script").remove();
			console.log( jQuery("<p>").append(span.eq(0).clone()).html());
		});
		console.log('Exit process');
	});
};

var onPageOpen = function(status){
	if(status !== 'success'){
		console.log('Unable to open page');
		phantom.exit();
	}
	else {
		page.injectJs( "jquery-1.7.2.min.js" );
		page.evaluate(processPage);
	}
};

page.open(phantom.args[0], onPageOpen);
