/**
 * $Revision: 1514 $
 **/

function togglehint(event) {
	var elem = $(event.target.nextSibling);
	if( elem.hasClass( "hidden" ) ) {
		elem.toggleClass("hidden");
	}
	else {
		//Must take more care because
		//the height/width don't transform
		event.target.nextSibling.style.opacity = 0;
		window.setTimeout( function() { elem.toggleClass( "hidden" ); event.target.nextSibling.style.opacity = null; }, 1000 );
	}
	return false;
}



window.addEventListener("message", onMessage, false);

function onMessage(e) {
	var resp = null;
	switch(e.data){
		default: break;
		case "size?":
		resp = [e.data, document.body.scrollWidth, document.body.scrollHeight].join(':');
		break;
	}

	if(resp) {
		e.source.postMessage(resp,"*");
	}
}
