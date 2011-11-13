var NextThought = NextThought || {};

$(document).ready(function() {
	var selectionLookup = new NextThought.SelectionLookup();
	$('body').mouseup(function(e){
		//must preserve the context, passing the function directly 
		//would make it run without the context of the object.
		selectionLookup.doMouseUp(e);
		
	});
});


NextThought.SelectionLookup = function(){};//constructor

NextThought.SelectionLookup.ID_BUTTON = 'tag';
NextThought.SelectionLookup.ID_CONTAINER = 'definition';

NextThought.SelectionLookup.HTML_BUTTON = ['<span id="',NextThought.SelectionLookup.ID_BUTTON,'"></span>'].join('');
NextThought.SelectionLookup.HTML_CONTAINER = ['<div id="',NextThought.SelectionLookup.ID_CONTAINER,'"></div>'].join('');

NextThought.SelectionLookup.MARGIN_CONTAINER = 50;
NextThought.SelectionLookup.SCROLL_BAR_GUTTER = 20;


NextThought.SelectionLookup.prototype.doMouseUp = function(e) {
	
	var target = e.target || e.srcElement;
	
	if(this.targetIsIn(
			target, 
			NextThought.SelectionLookup.ID_BUTTON, 
			NextThought.SelectionLookup.ID_CONTAINER)) {
		return false;
	}

	var sel = window.getSelection();
	this.removeObjects();
	
	if (!sel || !sel.toString()) {
		return false;
	}
	
	this.insertButton(
			this.getInsertionPoint(sel), 
			sel.toString());	
	
	return true;
};




NextThought.SelectionLookup.prototype.performQuery = function(container, data) {
	var context = this;
	$.ajax({
		url : "example.xml",
		context : context,
		success : function(xml, status, response) {
			this.renderResults(xml);
		}
	});
};



NextThought.SelectionLookup.prototype.renderResults = function(xml) {
	
	var $xml = $($.parseXML( xml ));
	console.log( xml );
    console.log( $.parseXML( xml ) ); 
	
};



NextThought.SelectionLookup.prototype.doButtonClick = function(e) {

	//create the container...
	$(NextThought.SelectionLookup.HTML_CONTAINER).appendTo(document.body).hide();
	var def = $(document.getElementById(NextThought.SelectionLookup.ID_CONTAINER));
	
	def.children().remove();//clear the container
	
	def.offset({
		left: NextThought.SelectionLookup.MARGIN_CONTAINER, 
		top: this.calculateContainerTop()
		});
	
	var width = $(document.body).width();
	def.width(	width
			-	(2 * NextThought.SelectionLookup.MARGIN_CONTAINER)
			-	NextThought.SelectionLookup.SCROLL_BAR_GUTTER
			);
	
	def.fadeIn(300);
	
	this.performQuery(def, e.data);
};


NextThought.SelectionLookup.prototype.insertButton = function(insertionPointEmptyRange, searchTerms) {
	
	//create and insert button into the dom,
	$(NextThought.SelectionLookup.HTML_BUTTON).appendTo(document.body);
	
	//get a reference to the button element...
	var tag = $(document.getElementById(NextThought.SelectionLookup.ID_BUTTON));
	//move it to the end of the selection...
	insertionPointEmptyRange.insertNode(tag[0]);
	//assign our click handler
	var ctx = this;
	
	tag.click({searchTerms: searchTerms}, function(e){
		//preserve context
		ctx.doButtonClick(e);
	});
	//show it
	tag.show();
};


NextThought.SelectionLookup.prototype.calculateContainerTop = function() {
	var tag = $(document.getElementById(NextThought.SelectionLookup.ID_BUTTON));
	return	 tag.offset().top
			+tag.outerHeight()
			-parseInt(tag.css('margin-top'),10);
};

NextThought.SelectionLookup.prototype.removeObjects = function() {
	$(document.getElementById(NextThought.SelectionLookup.ID_BUTTON)).fadeOut(300, function() { $(this).remove(); });
	$(document.getElementById(NextThought.SelectionLookup.ID_CONTAINER)).fadeOut(300, function() { $(this).remove(); });
};


NextThought.SelectionLookup.prototype.getInsertionPoint = function(s) {
	var range = document.createRange();
	var order = s.anchorNode.compareDocumentPosition(s.focusNode);
	
	// order is a bitmask, 000010 means that the order is reversed.
	var isForward = !((order & 2) === 2);
	
	try {
		range.setStart(
				isForward ? s.focusNode : s.anchorNode, 
				s.getRangeAt(0).endOffset);
	}
	catch (e) {
	}
	//this range's end point is irrelevant... return the start point.
	return range;
};


NextThought.SelectionLookup.prototype.targetIsIn = function (target /*elem1, elem2, ... elemN*/)
{
	for( var n=1; n<arguments.length; n++) {
		var arg = arguments[n];
		var node = document.getElementById(arg);
		if(!node) continue;

		if(node.contains(target) || node == target) {
			return true;
		}
	}
	return false;
};


//patch in .contains() for IE
//if (window.Node && Node.prototype && !Node.prototype.contains)
//{
//	Node.prototype.contains = function (arg) {
//		return !!(this.compareDocumentPosition(arg) & 16)
//	}
//}
