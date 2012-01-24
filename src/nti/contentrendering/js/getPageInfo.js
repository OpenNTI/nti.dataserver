if(phantom.args.length < 1){
	console.log('Usage: phantomjs getPageInfo.js page.html');
}

var page = require('webpage').create();
//page.viewportSize =  {width: 760, height: 964}; //height is 1024 - 60
page.onConsoleMessage = function (msg) {
    console.log(' Message from page: ' + msg);
};


var getPageInfo = function(){
	var pageInfo = {};
	//Grab some data about the scroll dimensions
	pageInfo['scrollHeight'] = document.documentElement.scrollHeight;
	pageInfo['scrollWidth'] = document.documentElement.scrollWidth;
	pageInfo['ntiid'] = $('meta[name=NTIID]').attr('content');

	//Grab data about outbound links
	var myPageURL = document.URL;
	var myPage = myPageURL.substr(myPageURL.lastIndexOf('/')+1);
	var outgoingLinks = $('a:visible[href]:not([href*="'+myPage+'"])');

	//We abuse a map here so we don't get duplicates.  Can we do this another way?
	var outgoingPages = {};

	for( var i = 0; i < outgoingLinks.length; i++ ){
		var outgoingLink = $(outgoingLinks[i]).attr('href');

		if(outgoingLink && outgoingLink != '#'){
			outgoingPages[outgoingLink]=true;
		}
							  
	}

	var opArray = [];

	for( key in outgoingPages ){
		opArray.push(key);
	}

	pageInfo['OutgoingLinks'] = opArray;
	return pageInfo;
};

var onPageOpen = function(status){
	if(status !== 'success'){
		console.log('Unable to open page');
	}
	else{
		var pageinfo = page.evaluate(getPageInfo);

		console.log(JSON.stringify(pageinfo));
	}
	phantom.exit();
};

page.open(phantom.args[0], onPageOpen);
