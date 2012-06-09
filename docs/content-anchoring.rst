===========
 Anchoring
===========

This document describes the method in which anchorable content is
modeled, and the methods used to convert ``NTIAnchorable`` content to and
from DOM selections/ranges.

Considerations
==============

We have the requirement to anchor various types of user data (at this
point the requirement is for notes, highlights, and redactions) to
specific ranges of content within a container. Beyond the basic
explicit requirement made above, two implicit requirements need to be
made explicit.

First, it is desired that anchors are as robust as possible to content
changes such as the addition, removal or reordering of paragraphs,
graphics, embedded media, etc. Preferably, even intra-paragraph
changes would have minimal effect. This means that anchors need to
store redundant information to be used as backup, and they also need
to store enough information to know whether or not they have
successfully located their target (assumed: highlighting/noting/redacting the
wrong thing is worse than displaying a "missing highlight" indicator).
(As a corollary, it also means that document-global information, such
as a DOM range or XPath is not sufficient by itself.)

.. note::
	When representing anchored contents as a range, content changes can be
	broken down into two classes, *inside* and *outside*. *Inside* changes
	are those changes in the content that occur in between a range's endpoints.
	*Outside* changes are those changes which occur outside, or surrounding,
	the range's endpoints.

Second, it is desired that anchors are as "local" as possible, to
support "mashups," embedding, and reuse of content. A concrete,
customer use-case of this the ability to recombine MathCounts problems
from their own worksheets into custom worksheets ("I want to search
for all problems about circles and make that a worksheet"). When this
happens, notes/discussions attached to the questions should be able to
come along. This ties in to the corollary of the first point.

To best support these two requirements we want to anchor objects to
authored content (authored content is that which came from the source
document, not that which is an artifact of rendering to a specific
format) whenever possible. For example, anchors should be tied to
authored paragraphs, questions, or images rather than their containing
``div`` s used for layouts. Not only does this allow for robustness and
mashups as described above, doing this should also make anchors robust
to layout changes (e.g., a portion of text originally in the
main body of a page moving to a callout in the sidebar.)

Assuming clients can perform any rendering or calculations required to
show NTIAnchored content using objects conforming to the `Dom Range Specification's Range object <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#ranges>`_,
, clients need only be concerned with the
conversion of our modeled anchorable objects to/from ``Range`` objects.

Modeling Anchorable Content
===========================

Taking inspiration from the `Dom Range Specification
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#ranges>`_,
we can use the following object model to represent anchored content:

.. code-block:: cpp

	// An object associated with some portion of a content unit
	mixin NTIAnchored : NTIContained {
		NTIContentRangeSpec content_range; //AKA anchor
	}

	class NTIContentRangeSpec {
		NTIContentAnchor start; //must not be nil
		NTIContentAnchor end; //must not be nil
		NTIContentAnchor ancestor; //must not be nil
	}

	abstract class NTIContentAnchor {
		string anchor_dom_id;    //dom id of the anchoring node
		string anchor_tag_name; //tagname of the anchoring node
		string type; //The type/kind of anchor this is being used for
	}

.. note::
  In the future, we may want to add supplementary information (such as
  an XPath) given an absolute or relative location to a selected Node to make it
  faster to reconstruct ranges. Any such supplementary information is
  not in this version of the specification, which focuses on simplicity.


Anchorable content *MUST* implement the abstract class ``NTIAnchored`` to
specify the ``content_range`` it is anchored to. ``NTIContentRangeSpec``
objects must have well formed ``NTIContentAnchor`` objects for start, end,
and ancestor. It *SHOULD* be considered an error if the start, end or
ancestor of a NTIContentRangeSpec object is undefined. A well formed
NTIContentRangeSpec with valid start, end, and ancestor values should
be used to create well formed DOM Range objects.

Objects of type ``NTIContentAnchor`` provide the information required to
identify a location in the content for use as the start or end of a
range or to identify a node that contains the start and end (common
ancestor). The abstract base class ``NTIContentAnchor`` contains the
minimum amount of information required to identify an anchor in NTI
content.

* ``anchor_dom_id`` is the DOM ID of an arbitrary node in the content.
* ``anchor_tag_name`` is the tag name for the node identified by
  ``anchor_dom_id``. Both these properties *MUST NOT* be nil.
* ``type`` specifies how this anchor is to be used.  It *MUST*
  take one of the following three values: ``"start"``, ``"end"``,
  ``"ancestor"``

Concrete subclasses of ``NTIContentAnchor`` should provide the
remaining information required to identify content location relative
to the anchor provided by the abstract base class.

NTIContentAnchor implementations
--------------------------------

The class ``NTIContentAnchor`` is abstract. A few subclasses are
specified which provide concrete storage and rules for resolution. In
the future, more subclasses may be added.

NTIContentAbsoluteAnchor
~~~~~~~~~~~~~~~~~~~~~~~~

An ``NTIContentAbsoluteAnchor`` adds no information to the abstract base
class. Its purpose is to identify a node that things can be anchored
relative to. This type of anchor is most often seen as the ``ancestor``
portion of an ``NTIContentRangeSpec``.

NTIContentTextAnchor
~~~~~~~~~~~~~~~~~~~~

When specifying context information for a `NTIContentTextAnchor` the
following `NTITextContext` will be used.

.. code-block:: cpp

	//Provide a snippet of text context
	class NTITextContext {
		string context_text; //A chunk of text that can be used as context
		int context_offset; //offset of context_text into context_offset's
							//containing text node
	}

* ``context_text`` is a string contained in the `textContent or nodeValue
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-node-textcontent>`_
  of a ``Text`` node near the ``NTIContentTextAnchor`` this object is
  providing context for.
* ``context_offset`` is the index of ``context_text`` from the start or end of ``textContent``.
  ``content_offset`` *MUST* be an integer greater than or equal to zero.  Negative values are reserved for future use.
  If this object is providing context for an anchor with a type *EQUAL TO* ``"start"``, ``content_offset``
  represents the character index from the end (right) of ``textContent``.
  If this object is providing context for an anchor with a type *EQUAL TO* ``"end"``,
  ``content_offset`` represents the index from the start (left) of
  ``textContent``.  This keeps keeps indexes closest to the selected
  range stable.

.. code-block:: cpp

	//Adds redundant information about text content
	class NTITextContentAnchor : NTIContentAnchor {
		NTITextContext[] contexts; //An array of NTITextContext
		                          //objects providing context for this anchor
		int edge_offset; //The offset from the start or end of content_text of the edge
	}


This class should be used to reference portions of DOM `Text nodes
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#interface-text>`_
as ``NTIContentAnchor`` objects, and is useful when a range begins or
ends inside of ``Text`` content.


* ``contexts`` is an array of ``NTITextContext`` objects that provide
  contextual information for the ``range`` endpoint represented by this
  anchor.  The length of ``contexts`` *MUST* be >= 1.  The first
  ``NTITextContext`` object in the array provides the ``primary
  context`` for this anchor, and represents a snippet of text enclosing
  the ``range`` endpoint identified by this anchor.  Subsequent
  ``NTITextContext`` objects in the array, provide additional context.
  Those objects closest to the beggining of the array provide the most
  specific context while those towards the end provide less specific
  context. If this anchor has a ``type`` *EQUAL TO* ``start``
  the additional context objects mirror the ``Text`` nodes returned by
  repeateadly asking `TreeWalker <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_
  for ``nextNode`` starting from the node used to generate
  the ``primary context`` object.  Similarily, if this anchor has a
  ``type`` *EQUAL TO* ``end`` the additional context objects mirror the ``Text`` nodes returned by
  repeateadly asking `TreeWalker <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_
  for ``previousNode`` starting from the node used to generate
  the ``primary context`` object.  See ``Converting a Text Node to
  NTIContentTextAnchor`` for more information.
* ``edge_offset`` is the character offset from the start of the
  ``primary context`` object's ``context_text`` string to the location
  of the edge thie anchor represents.

NTIContentRangeSpec subclasses
------------------------------

For special types of content ranges NTIContentRangeSpec may be subclassed to provide additional
information. The only supported subclass of NTIContentRangeSpec is
``NTIContentSimpleTextRangeSpec``.

NTIContentSimpleTextRangeSpec
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: cpp

	//Adds extra information for ranges contained in one textNode
	class NTIContentSimpleTextRangeSpec : NTIContentRangeSpec {
		string selected_text; //The selected text
		int offset; //The offset from the start of the Text node to selected_text
	}

This class can be used to help optimize ``NTIContentRangeSpec`` conversion when
the start and end anchors represent the same ``Text`` node.  ``NTIContentSimpleTextRangeSpec``
objects *MUST* have NTIContentTextAnchors for both ``start`` and ``end`` that represent
the same dom node.

* ``selected_text`` is the subsection of the ``Text`` node's ``textContent`` that falls
  within the ``start`` and ``end`` of the range spec.
* ``offset`` is the character index into the ``Text`` node's
  ``textContent`` of ``selected_text`` from the left.


NTIContentRangeSpec conversion
==============================

To maintain parity between clients it is important the same algorithm
be used for converting ``NTIContentRangeSpec`` objects to and from DOM
ranges. The algorithm to use is detailed here.

We begin with some definitions:

*referenceable* (or *representable*) DOM ``Node``
	A ``Node`` which can supply the information
	necessary to completely create a ``NTIContentAnchor.``

	This Node is either an ``Element`` (because it must have the  `id
	<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-id>`_,
	and `tag_name
	<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-tagname>`_
	properties) with a *referenceable ID*, or a ``Text`` node that is a
	descendent (not necessarily a direct child) of such an ``Element.``

*referenceable ID*
	The value of an ``id`` property of an ``Element`` which is not null,
	not the empty string, and does not begin with one of the following
	excluded prefixes: ``MathJax``.

DOM Range to NTIContentRangeSpec
--------------------------------

Given a DOM ``Range``, ``range``, clients can only generate
``NTIContentRangeSpec`` objects if they are able to represent the
start and end of the ``range`` object using ``NTIContentAnchor``
objects. If asked to create an ``NTIContentRangeSpec`` for a range
whose start or end cannot be represented using an
``NTIContentAnchor``, clients should walk the end(s) that are not
representable inward (i.e., narrowing the range) [#]_ until the
range's start and end fall on nodes that can be represented as
``NTIContentAnchors.``

.. [#] Because this usually takes place in the context of a user
  selecting a chunk of text, in the event we can't anchor the start or
  the end, we assume we want the largest representable range contained by the original
  range. That is, we shrink the range inward from the necessary edges.

Given a ``range`` whose edges can by represented by NTIContentAnchors,
the generation of an NTIContentRangeSpec is straightforward. As a
first step the DOM is walked upwards from the range's `commonAncestorComponent
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-commonancestorcontainer>`_
until a node that can be represented as a ``NTIContentAbsoluteAnchor``
is found. This node is then converted to an
``NTIContentAbsoluteAnchor`` as described below and the result becomes
the ``ancestor`` of the ``NTIContentRangeSpec``. With the ancestor
conversion complete the client then converts both the range's `startContainer
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-startcontainer>`_
and `endContainer
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-endcontainer>`_
(at this point both of which we know can be represented by an
``NTIContentAnchor``), and stores the result in the
``NTIContentRangeSpec`` as ``start`` and ``end``, respectively.

A start or end that is a representable ``Text`` Node will be represented with an
``NTContentTextAnchor;`` all other endpoints will be represented with
an ``NTIContentAbsoluteAnchor.``

In the special case where ``start`` and ``end`` are
``NTIContentTextAnchor`` objects that represent the same ``Text``
node, the subclass ``NTIContentSimpleTextRangeSpec`` should be
produced. In this case ``selected_text`` should be populated from the
``start`` anchor's ``textContent`` from the range's ``startOffset`` to
``endOffset``. ``offset`` should be populated with the range's
``startOffset``.

Converting an Element to NTIContentAbsoluteAnchor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Elements represented as an ``NTIContentAbsoluteAnchor`` *MUST* have both
an ``id`` and ``tagname``. The ``NTIContentAnchor``'s ``anchor_dom_id``
*SHOULD* be set to the node's `id
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-id>`_,
and ``anchor_tag_name`` should be set to the nodes `tag_name
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-tagname>`_.


Converting a Text Node to NTIContentTextAnchor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the ``startContainer`` or ``endContainer`` in a ``Range`` is a ``Text`` node, the
result of conversion will be an ``NTIContentTextAnchor`` (the "text
anchor"). Because ``Text`` nodes do not have tag names or IDs, a text
anchor describes a node that does have those properties (a containing
``Element``) plus a set of context objects that define the location of
the text within (beneath) that element.

The first step in generating a text anchor is to identify the
containing element (reference point). From the text node, walk up the
DOM until a refrenceable node is found. This node's ID and tag name
become the ``anchor_dom_id`` and ``anchor_tag_name`` respectively.

The anchor's ``primary context`` and ``edge_offset``
can be populated given the ``NTIContentTextAnchor`` and the Range object. The
generation of ``primary`` and ``subsequent`` ``NTITextContext`` objects may change from anchor to anchor based
on some set of heuristics. In additon the method for generating the
``primary context`` object may differ from the method used to generate
``subsequent`` ``NTITextContext`` objects. In order to populate a ``Range`` object's
endpoints from ``NTIContentTextAnchors``, ``contexts`` should contain
enough ``NTITextContent`` objects to uniquely identfiy this anchor
point beneath the reference node.

The generation of ``NTITextContext`` objects should be designed in such a way
that the heuristics can be easily tweaked. As a first pass we will
take a word based approach to extracting context from a ``Text`` node.
Given an anchor and a ``Text`` node to extract context from, the following procedure
should be used to generate the ``primary context`` object.

.. code-block:: javascript

	//Extract first word from string
	function firstWordFromString(str){
		var word = '';
		var readingWord = false;
		for(var i=0; i < str.length; i++){
			var char = str.charAt(i);
			if(/\s/.test(char)){
				if(readingWord){
					break;
				}
				word += char;
			}
			else{
				readingWord = true;
				word += char;
			}
		}
		return word;
	}

	//Extract first word from string
	function lastWordFromString(str){
		var word = '';
		var readingWord = false;
		for(var i=str.length - 1; i >= 0; i--){
			var char = str.charAt(i);
			if(/\s/.test(char)){
				if(readingWord){
					break;
				}
				word += char;
			}
			else{
				readingWord = true;
				word += char;
			}
		}
		return word.split("").reverse().join("");
	}

	//Generates the primary context for the given anchor
	//to model one end of the given range
	function generatePrimaryContext(anchor, range){
		var container = anchor.type === 'start' ? range.startContainer: range.endOffset
		var offset = anchor.type === 'start' ? range.startOffset : range.endOffset

		//For the primary context we want a word on each side of the
		//range
		var textContent = container.textContent;

		var prefix = lastWordFromString(textContent.substring(0, offset))
		var suffix = firstWordFromString(textContent.substring(offset, textContent.length);

		var context_text = prefix+suffix;
		var context_offset = textContent.indexOf(context_text);
		if( anchor.type === 'start' ){
			context_offset = textContent.length - context_offset;
		}

		NTITextContext ctx = {'context_text': context_text,
							  'context_offset': context_offset};
		return ctx;
}

Given a ``Text`` node and an anchor, ``subsequent``
``NTITextContext`` objects can be generated as follows

.. code-block:: javascript

	//Given an anchor and a relative node (next or previous sibling)
	//depending on the value of anchor.type, generates an
	//NTITextContext suitable for use as subsequent context
	function generateSubsequentContext(anchor, relative_node)
	{
		var context_text = null;
		if(anchor.type === 'start'){
			context_text = lastWordFromString(relative_node.textContent);
		}
		else{
			context_text = firstWordFromString(relative_node.textContent);
		}

		var offset = relative_node.textContent.indexOf(context_text);
		if(anchor.type === 'start'){
			offset = relative_node.textContent.length - offset;
		}

		NTITextContext ctx = {'context_text': context_text,
							  'context_offset': offset};
		return ctx;
	}

The generation of both ``primary`` and ``subsequent``
``NTITextContext`` objects are subject to change.  In addition
the huersitics governing the number of ``subsequent`` context nodes
to be generated may change.  For this version of the spec,
subsequent context nodes should be generated until 15 characters or
5 context nodes have been collected.  Putting this, together with the
above methods for generating context nodes, turn
a range endpoint in to a complete ``NTIContentTextAnchor`` object as follows:

.. code-block:: javascript

	//Complete an anchor given a range
	function populateAnchorWithRange(anchor, range)
	{
		var container = anchor.type === 'start' ? range.startContainer: range.endOffset
		var offset = anchor.type === 'start' ? range.startOffset : range.endOffset

		var contexts = [];

		//First construct the primary context
		var primaryContext = generatePrimaryContext(anchor, range);
		contexts.push(primaryContext);

		//Generate the edge offset
		var normalizedOffset = primaryContext.context_offset;
		if(anchor.type === 'start'){
			normalizedOffset = container.textContent.length - normalizedOffset;
		}

		anchor.edge_offset = offset - normalizedOffset;

		//Now we want to collect subsequent context
		var collectedCharacters = 0;
		var maxSubsequentContextObjects = 5;
		var maxCollectedChars = 15;

		var tree_walker = document.createTreeWalker( container, NodeFilter.SHOW_TEXT );
		//TODO do we need to stay within the reference node here?

		var nextSiblingFunction = anchor.type === 'start' ? tree_walker.previousNode : tree_walker.nextNode;

		while( sibling = nextSiblingFunction() ) {

			if(   collectedChars >= maxCollectedChars
			   || contexts.length - 1 >= maxSubsequentContextObjects ){
			   break;
			}

			NTITextContext subsequentContext = generateSubsequentContext(anchor, sibling)
			collectedCharacters += subsequentContext.context_text.length;
			contexts.push(subsequentContext);
		}

		anchor.contexts = contexts;
	}

.. note::
  In the past, when walking ``Text`` nodes, we have encountered nodes
  whose textContent is only whitespace.  Should we skip those when
  walking siblings with the TreeWalker?

.. note::
  The Range's offsets are specified in terms of the DOM object's node
  length. For a Text node, its length is defined as unicode code
  points or characters.

.. note::
  If it was necessary to traverse upward many nodes in order to find
  one that is referenceable, then, because we are only storing a text
  node's content and the offset, not any sort of path information,
  the process of reconstructing the matching range could be fairly
  inefficient and require much traversal. The performance
  ramifications of this are unclear.

NTIContentRangeSpec to DOM Range
--------------------------------

When creating a DOM Range, ``range``, object from ano
``NTIContentRangeSpec`` object, clients should keep in mind that from
a user perspective it is much worse to anchor something to the wrong
content than to not anchor it at all. If, when reconstructing the range
from the ``NTIContentRangeSpec``, a client is unable to confidently
locate the ``startContainer``, ``endContainer``, ``startOffset``, or
``endOffset`` using all the ``NTIContentAnchor`` information provided,
the client *should* abort anchoring the content to a specific
location.

For each type of anchor, clients should implement two functions for
resolving anchors ``locateRangeStartForAnchor(NTIContentAnchor
startAnchor, Element ancestor)`` and
locateRangeEndForAnchor(NTIContentAnchor endAnchor, Element ancestor,
NTIAnchorResolution startResult)``.  Both these functions should
return a ``NTIAnchorResolutionResult`` object.

.. code-block:: javascript

	//Encapsulates the result or an anchor resolution
	//and a confidence value
	class NTIAnchorResolutionResult{
		id node; //The node contained in the range
		int offset; //The offset into containingNode of the edeg
		float confidence; //A confidence value about the result
	}

* ``node`` is a ``DOM`` node suitable for inclusion within
  a range object.  If confidence is > 0 this value *MUST* not be null
* ``offset`` is the offset into ``node`` where the range
  should start or end.  If defined ``offset`` must be >=0.  Negative
  values are reserved for future use.  If undefined the resulting
  range will start just before, or after, ``node``.
* ``confidence`` should be a number ``0 <= confidence <= 1`` that can
  be used as an indication of how confident the algorithm that this
  result is correct for the given ``NTIContentAnchor``.  A value of
  ``1`` indicates 100% confidence.  Conversley, a value of `0`
  indicates 0% confidence.

.. note::

	Although future version of the spec will likely support continous
	values for confidence.  The current spec expect discrete values of
	``1`` or ``0``.  Values < 1 will be interpreted as 0, 0% confidence.

Anchor resolution starts by resolving the ancestor
``NTIContentAnchor`` to a DOM node (which *must* be an ``Element``).
This provides a starting point when searching for the start and end
``NTIContentAnchors``. The ancestor can also be used to validate parts of
the ``NTIContentRangeSpec``. For example, the start and end should be
contained in the ancestor. If the ancestor can't be resolved it should
default to the DOM's `documentElement <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#document-element>`_.

Given an ancestor the DOM can then be traversed for the start and end
container ``Nodes`` and offsets needed to construct a range. If a start
and end ``Node`` cannot be located beneath the ancestor, and the ancestor
is not already the ``documentElement,`` resolution should be tried
again given an ancestor of the ``documentElement.`` If the start does
not come before end (as computed using `compareDocumentPosition
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-node-comparedocumentposition>`_),
the ``NTIContentRangeSpec`` is invalid and clients *should* abort
range creation and anchoring. Given an ``NTIContentRangeSpec`` the
following procedure should be used to resolve a dom range.

.. code-block:: javascript

	//Given an NTIContentRangeSpec produce a dom
	//range search beneath ancestor.  Returns nil if the
	//range spec can't be resolved
	function resolveSpecBeneathAncestor( rangeSpec, ancestor )
	{
		//Resolve the start anchor.
		//see below for details no resolving various
		//anchor types
		var startResult = locateRangeStartForAnchor(rangeSpec.start, ancestor);

		//If we can't even resolve the start anchor there
		//is no point in resolving the end
		if(    !startResult.node
			|| !startResult.hasOwnProperty('confidence')
			|| startResult.confidence != 1){
			return nil;
		}

		//Resolve the end anchor.
		//see below for details no resolving various
		//anchor types
		var endResult = locateRangeEndForAnchor(rangeSpec.end, ancestor, startResult);

		if(    !endResult.node
			|| !endResult.hasOwnProperty('confidence')
			|| endResult.confidence != 1){
			return nil;


		var range = document.createRange();
		if(startResult.hasOwnProperty('confidence')){
			document.setStart(startResult.node, startResult.offset);
		}
		else{
			document.setStartBefore(startResult.node);
		}

		if(endResult.hasOwnProperty('confidence')){
			document.setEnd(endResult.node, endResult.offset);
		}
		else{
			document.setEndAfter(endResult.node);
		}
	}


	function rangeFromRangeSpect( rangeSpec )
	{
		var ancestorNode = resolveAnchor(rangeSpec.ancestor) || document.body;

		var range;
		if( rangeSpec is NTIContentSimpleTextRangeSpec ){
			//See NTIContentSimpleTextRangeSpec to DOM Range
			range = rangeFromTextRangeSpec(rangeSpec, ancestorNode);
			if(range){
				return range;
			}
		}

		range = resolveSpecBeneathAncestor(rangeSpec, ancestorNode);

		if( !range && ancestorNode !== document.body ){
			range = resolveSpecBeneathAncestor( rangeSpec, document.body );
		}

		return rangeSpec;
	}

.. note::
	Although this version of the spec's ``rangeFromRangeSpec``
	function returns a range if it could successfully recreate the
	range, or null.  For UI purposes, future versions may return a
	confidence value and some information about why the confidence
	value is what it is.

NTIContentSimpleTextRangeSpec to DOM Range
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the unlikely event a range spec is actually an
``NTIContentSimpleTextRangeSpec`` a fast first pass can be attempted
to generate the ``range``. As above, anchor resolution begins by
resolving the ``ancestor`` component of the ``spec``. Given the
resolved ``ancestor`` as a reference node, clients should search for a
``Text`` node *beneath* it whose ``textContent`` contains
``selected_text`` at ``offset``. This is conveniently done with a
`TreeWalker
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_:

.. code-block:: javascript

	var simpleTextSpec = ...
	var ref_node = ...

	var tree_walker = document.createTreeWalker( ref_node, NodeFilter.SHOW_TEXT );
	var test_node = null;
	var matchingNodes = [];
	while( test_node = tree_walker.nextNode() ) {
	    if( test_node.textContent.indexOf(simpleTextSpec.selected_text) == simpleTextSpec.offset ) {
	       matchingNodes.push(text_node);
	    }
	}

If no ``Text`` nodes are found containing ``selected_text`` at ``offset``, or if more than one
``Text`` node is found satisfying the condition, ``NTIContentSimpleTextRangeSpec`` resolution
fails.  In this case clients should fallback to standard ``NTIContentRangeSpec`` resolution by
constructing a ``range`` object via resolution of the ``start`` and ``end`` anchors.

In the event that a single ``Text`` node satisfying the above conditions is found, a range can be
constructed from the ``Text`` node and ``NTIContentSimpleTextRangeSpec`` as follows.

.. code-block:: javascript

	var foundNode = ...
	var simpleTextSpec = ...

	var resolvedRange = document.createRange();
	resolvedRange.setStart(foundNode, simpleTextSpec.offset);
	resolvedRange.setEnd(foundNode, simpleTextSpec.offset + simpleTextSpec.selected_text.length);

Converting NTIContentAbsoluteAnchor to a Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Given an NTIContentAbsoluteAnchor find the DOM ``Element`` whose ID is
``anchor_dom_id`` within the ancestor. If an ``Element`` with that ID
can't be found or the tagname of the ``Element`` does not match
``anchor_tag_name``, conversion fails and the result is null.  Sample
code for resolving NTIContentAbsoluteAnchor as a start anchor follows:

.. code-block:: javascript

	function locateRangeStartForAnchor(absoluteAnchor, ancestorNode){
		var tree_walker = document.createTreeWalker( ancestorNode, NodeFilter.SHOW_ELEMENT );

		while( test_node = tree_walker.nextNode() ) {
	    	if(    test_node.id === absoulteAnchor.anchor_dom_id
			    && test_node.tagName === absoluteAnchor.anchor_tag_name ) {
	       		return {node: test_node, confidence: 1};
	    	}
		}
		return {confidence: 0};
	}

An example of updating the range for an NTIContentAbsoluteAnchor with
type === ``end`` is as follows.

.. code-block:: javascript

	function locateRangeEndForAnchor(absoluteAnchor, ancestorNode, startResult){
		var tree_walker = document.createTreeWalker(ancestorNode, NodeFilter.SHOW_ELEMENT );

		//We want to look after the start node so we reposition the walker
		tree_walker.currentNode =  startResult.node;

		while( test_node = tree_walker.nextNode() ) {
	    	if(    test_node.id === absoulteAnchor.anchor_dom_id
			    && test_node.tagName === absoluteAnchor.anchor_tag_name ) {
				return {node: test_node, confidence: 1};
	    	}
		}
		return {confidence: 0};
	}


Converting NTIContentTextAnchor to a Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The general algorithm for resolving a ``NTIContentTextAnchor`` is a
follows.  Begin by resolving the ``reference node`` using
``anchor_dom_id`` and ``anchor_tag_name``.  If the ``reference node``
can't be resolved, use the ``ancestor`` as the ``reference node``.  Using
the ``refernce node`` as the root, create a ``Tree Walker`` to
interate each ``Text`` node, ``textNode``, using the ``nextNode`` method.

For each ``textNode`` check if the ``primary context`` object matches
``textNode``.  If it does, using a ``Tree Walker`` rootted at
``reference_node``, compare each ``subsequent context`` object by
walking the tree using the ``previousNode`` method, if anchor
``type`` is ``start``, or forward using the ``nextNode`` method, if the anchor ``type`` is
``end``.  If all context objects match, ``textNode`` will become the range`s
``startContainer`` if the anchor ``type`` is ``start``, or ``endContainer``
if the anchor ``type`` is ``end``.  If not all the context objects
match continue the outter loop by comparing context objects for the
next ``textNode``.

If a ``textNode`` has been identified as the start or end container, a
range can be constructed as follows.  If anchor ``type`` is ``start``,
set the ``ranges`` ``startContainer`` to ``textNode``.  If anchor ``type`` is ``end``,
set the ``ranges`` ``endContainer`` to ``textNode``.  Calculate the
text offset by identifying the index of the ``primary context``
object's ``context_text`` in the container. Adjust the offset by
anchor's ``edge_offset`` property, and set the range's ``startOffset``,
if anchor ``type`` == ``start``, or ``endOffset``, if anchor ``type``
== `end`, to the computed value.

One such intial implemenation is shown in detail below:

.. code-block:: javascript

	function locateRangeStarForAnchor(textAnchor, ancestorNode){
		return locateRanageEdgeForAnchor(textAnchor, ancestorNode, null);
	}

	function locateRangeEndForAnchor(textAnchor, ancestorNode, startResult){
		return locateRanageEdgeForAnchor(textAnchor, ancestorNode, startResult);
	}

	function locateRanageEdgeForAnchor(textAnchor, ancestorNode, startResult){
		//Resolution starts by locating the reference node
		//for this text anchor.  If it can't be found ancestor is used
		var referenceNode = resolveAnchor(textAnchor.anchor_dom_id, textAnchor.anchor_tag_name);
 		if(!referenceNode){
			referenceNode = ancestorNode;
		}

		//A value between 0 and 1 indicating the confidence we
		//require to match a textNode to an NTITextContext.  A
		//value of 1 indicates 100% confidence, while a value of 0
		//indicates 0% confidence
		var requiredConfidence = 1;

		//We use a tree walker to search beneath the reference node
		//for textContent matching our primary context with confidence
		// >= requiredConfidence

		var tree_walker = document.createTreeWalker( referenceNode, NodeFilter.SHOW_TEXT );

		//If we are looking for the end node.  we want to start
		//looking where the start node ended
		if( textAnchor.type === 'end' ){
			tree_walker.currentNode = startResult.node;
		}

		var textNode;

		if(tree_walker.current_node.nodeType == Node.TEXT_NODE){
			textNode = tree_walker.current_node;
		}
		else{
			textNode = tree_walker.next_node;
		}


		//If we are working on the start anchor, when checking context
		//we look back at previous nodes.  if we are looking at end we
		//look forward to next nodes
		var siblingFunction = textAnchor.type === 'start' ? tree_walker.previousNode : tree_walker.nextNode;
		while( textNode ) {
			//Do all our contexts match this textNode
			var nextNodeToCheck = textNode;
			var match = true;
			for( var contextObj in textAnchor.contexts ){
				//Right now, if we don't have all the nodes we need to have
				//for the contexts, we fail.  In the future this
				//probably changes but that requires looking ahead to
				//see if there is another node that makes us ambiguous
				//if we don't apply all the context
				if(!nextNodeToCheck){
				    match = false;
					break;
				}
				//If we don't match this context with high enough confidence
				//we fail
				if( confidenceForContextMatch(contextObj, textNode, textAnchor.type) < requiredConfidence){
					match = false;
					break;
				}

				//That context matched so we continue verifying.
				nextNodeToCheck = siblingFunction();
			}

			//We matched as much context is we could,
			//this is our node
			if(match){
				break;
			}
			else{
				//That wasn't it.  Continue searching
				tree_walker.currentNode = textNode;
			}

			//Start the context search over in the next textnode
			textNode = tree_walker.nextNode();
		}

		//If we made it through the tree without finding
		//a node we failed
		if(!textNode){
			return {confidence: 0};
		}


		//We found what we need.  Set the context
		var primaryContext = textAnchor.contexts[0];

		var container = textNode;
		var indexOfContext = container.textContent.indexOf(primaryContext.context_text);
		indexOfContext += textAnchor.edge_offset;
		return {node:container, offset: indexOfContext, confidence: 1};
	}


The huersistics involved in calculating a confidence value for a
particular context may change, current spec requires exact matches.
Clients should implement `confidenceForContextMatch` as follows:

.. code-block:: javascript

	//Returns a confidence value of 0 or 1 indicating the confidence we
	//are in the fact that context matches node.  A
	//value of 1 indicates 100% confidencee. A value of 0
	//indicates 0% confidence
	function confidenceForContextMatch(context, node, anchorType)
	{
		var adjustedOffset = context.context_offset;
		if(anchorType === 'start'){
			adjustedOffset = node.textContent.length - adjustedOffset;
		}

		if( node.textContent.indexOf(context.context_text) == adjustedOffset){
			return 1;
		}
		return 0;
	}

Examples
--------

This section will provide example HTML documents with a selection, a representation of
their DOM, and the resulting ``NTIContentRangeSpec`` created (in JSON
notation). Within the HTML, individual ``Text`` nodes are surrounded
with square brackets; the selection is demarcated with the vertical
pipe ``|``.

A NTIContentSimpleTextRangeSpec
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: html

	<p id="id">
		[|A single selected text node|]
	</p>

.. code-block:: javascript

	// The content range
	{
		ancestor: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
		},
		start: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
			contexts: [{ context_text: 'A', context_offset: 26 }]
			edge_offset: 0
		},
		end: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
			contexts: [{ context_text: 'node', context_offset: 22 }],
			edge_offset: 4
		},
		selected_text: 'A single selected text node',
		offset: 0
	}


Example 2
~~~~~~~~~

This example spans from one text node to the next.

.. code-block:: html

	<p id="id">
		[|An] <i>[italic]</i> [word.]|
	</p>


.. code-block:: javascript

	// The content range
	{
		ancestor: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
		},
		start: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
			contexts: [{ context_text: 'An', context_offset: 2 }]
			edge_offset: 0
		},
		end: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
			contexts: [{ context_text: 'word.', context_offset: 0 }],
			edge_offset: 5
		}
	}



Example 3
~~~~~~~~~

This example has multiple text nodes that match. Notice that
the offsets within a text node are the same. How does it resolve?

.. code-block:: html

	<p id="id">
		[This is the] <i>[first]</i> [sentence.]
		<span> [This is |the] <i>second</i> [sentence.|]</span>
	</p>


.. code-block:: javascript

	// The content range
	{
		ancestor: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
		},
		start: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
			contexts: [{ context_text: 'is the', context_offset: 3 },
					   {context_text: 'sentence.', context_offset: 9},
					   {context_text: 'first', context_offset: 5},
					   {context_text: 'the'}, context_offset: 3]
			edge_offset: 8
		},
		end: {
			anchor_dom_id: 'id',
			anchor_tag_name: 'p',
			contexts: [{ context_text: 'sentence.', context_offset: 0 }],
			edge_offset: 9
		}
	}


Anchor Migration
================

As time goes on and content around anchored items changes, we may need
some system for migrating/updating/correcting ``NTIContentRangeSpecs``.
This likely has to happen on the client side and depending on the
severity of the change, in the worst case, we may want some kind of
input from the user. Does your highlight or note still make sense here
even though the content has changed? We should think about if and how
this sort of thing can happen.
