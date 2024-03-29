===========
 Anchoring
===========

This document describes the method in which anchorable content is
modeled, and the methods used to convert ``Anchored`` content to and
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
show ``Anchored`` content using objects conforming to the `Dom Range Specification's Range object <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#ranges>`_,
clients need only be concerned with the
conversion of our modeled anchorable objects to/from ``Range`` objects.

Modeling Anchorable Content
===========================

Taking inspiration from the `Dom Range Specification
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#ranges>`_,
we can use the following object model to represent anchored content:

.. code-block:: cpp

	// An object associated with some portion of a content unit
	mixin Anchored<Contained> {
		ContentRangeDescription applicableRange; //AKA anchor
	}

	// Notice that these are not Dataserver object (e.g, no OID)

	class ContentRangeDescription {
		// By itself, this class serves to denote an 'empty' range
	}

	abstract class ContentPointer {}

	abstract class DomContentPointer : ContentPointer {
		string role; //The role this pointer is playing in the
		//anchoring process
	}

	class DomContentRangeDescription : ContentRangeDescription {
		DomContentPointer start; //must not be nil
		DomContentPointer end; //must not be nil
		DomContentPointer ancestor; //must not be nil
	}


.. note::
  In the future, we may want to add supplementary information (such as
  an XPath) given an absolute or relative location to a selected Node to make it
  faster to reconstruct ranges. Any such supplementary information is
  not in this version of the specification, which focuses on simplicity.

.. note::
  The definitive dataserver versions of all the datastructures defined in this document
  are described in :doc:`content-anchoring-interfaces`.

Anchorable content *MUST* implement the abstract class ``Anchored`` to
specify the ``applicableRange`` it is anchored to. ``ContentRangeDescription``
objects must have well formed ``ContentPointer`` objects for start, end,
and ancestor. It *SHOULD* be considered an error if the start, end or
ancestor of a ContentRangeDescription object is undefined. A well formed
ContentRangeDescription with valid start, end, and ancestor values should
be used to create well formed DOM Range objects.

Objects of type ``ContentPointer`` provide the information required to
identify a location in the content for use as the start or end of a
range, or to identify a node that contains the start and end (common
ancestor). The abstract base class ``DOMContentPointer`` contains the
minimum amount of information required to identify an anchor in NTI
html based content.

* ``role`` specifies how this anchor is to be used.  It *MUST*
  take one of the following three values: ``"start"``, ``"end"``,
  ``"ancestor"``

Concrete subclasses of ``DOMContentPointer`` should provide the
remaining information required to identify content location relative
to the anchor provided by the abstract base class.

DOMContentPointer implementations
---------------------------------

The class ``DOMContentPointer`` is abstract. A few subclasses are
specified which provide concrete storage and rules for resolution. In
the future, more subclasses may be added.

ElementDomContentPointer
~~~~~~~~~~~~~~~~~~~~~~~~

An ``ElementDomContentPointer`` adds the necessary information to the abstract base
class ``DOMContentPointer`` to represent a containiner element.
Its purpose is to identify a node that things can be anchored
relative to. This type of anchor is most often seen as the ``ancestor``
portion of an ``ContentRangeDescription`` or a ``TextDomContentPointer``.

.. code-block:: javascript

	class ElementDomContentPointer : DomContentPointer{
		string elementId;    //dom id of the anchoring node
		string elementTagName; //tagname of the anchoring node
	}


* ``elementId`` is the DOM ID of an arbitrary node in the content.
* ``elementTagName`` is the tag name for the node identified by
  ``elementId``. Both these properties *MUST NOT* be nil.

TextDomContentPointer
~~~~~~~~~~~~~~~~~~~~~

Content is anchored within text by describing a containing ancestor element,
plus some context information used to traverse to the anchored text:

.. code-block:: cpp

	//Adds redundant information about text content
	class TextDomContentPointer : DOMContentPointer {
		DomContentPointer ancestor; //Represents the containing element
									//this text is anchored in.
		TextContext[] contexts; //An array of TextContext
		                          //objects providing context for this anchor
		int edgeOffset; //The offset from the start or end of content_text of the edge
	}


This class should be used to reference portions of DOM `Text nodes
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#interface-text>`_
as ``ContentPointer`` objects, and is useful when a range begins or
ends inside of ``Text`` content.

* ``ancestor`` is a ``DomContentPointer`` that represents
  an element who is an ancestor (not necessarily a direct parent) of
  the text represented by this ``TextDomContentPointer`` object.  If
  ``ancestor`` is a ``ElementDomContentPointer`` its ``role`` will be ``ancestor``.
* ``contexts`` is an array of ``TextContext`` objects that provide
  contextual information for the ``range`` endpoint represented by
  this anchor. The length of ``contexts`` *MUST* be at least one. The
  first ``TextContext`` object in the array provides the *primary
  context* for this anchor, and represents a snippet of text adjacent
  to the ``range`` endpoint identified by this anchor. Additional
  ``TextContext`` objects in the array provide further context.
  Those objects closest to the beginning of the array provide the most
  specific (nearest) context while those towards the end provide less
  specific (more distant) context. If this anchor has a ``role``
  *EQUAL TO* ``start`` the additional context objects mirror the
  ``Text`` nodes returned by repeateadly asking `TreeWalker
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_
  configured to show non whitespace only ``Text`` nodes for ``previousNode`` starting from the node used to generate the
  *primary context* object. Similarily, if this anchor has a ``role``
  *EQUAL TO* ``end`` the additional context objects mirror the
  ``Text`` nodes returned by repeateadly asking `TreeWalker
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_
  configured to show non whitespace only ``Text`` nodes for ``nextNode`` starting from the node used to generate the
  *primary context* object. See ``Converting a Text Node to
  TextDomContentPointer`` for more information.
* ``edgeOffset`` is the character offset from the start of the
  ``primary context`` object's ``contextText`` string to the location
  of the edge thie anchor represents.


When specifying context information for a `TextDomContentPointer` the
following `TextContext` will be used:

.. code-block:: cpp

	//Provide a snippet of text context
	class TextContext {
		string contextText; //A chunk of text that can be used as context
		int contextOffset; //offset of contextText into contextOffset's
							//containing text node
	}

* ``contextText`` is a string contained in the `textContent or nodeValue
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-node-textcontent>`_
  of a ``Text`` node near the ``TextDomContentPointer`` this object is
  providing context for.
* ``contextOffset`` is the index of ``contextText`` from the start or end of ``textContent``.
  ``contextOffset`` *MUST* be an integer greater than or equal to zero.  Negative values are reserved for future use.
  If this object is providing context for an anchor with a ``role`` *EQUAL TO* ``"start"``, ``contextOffset``
  represents the character index from the end (right) of ``textContent``.
  If this object is providing context for an anchor with a ``role`` *EQUAL TO* ``"end"``,
  ``contextOffset`` represents the index from the start (left) of
  ``textContent``.  This keeps indexes closest to the selected
  range stable.


ContentRangeDescription conversion
==================================

To maintain parity between clients it is important the same algorithm
be used for converting ``ContentRangeDescription`` objects to and from DOM
ranges. The algorithm to use is detailed here.

We begin with some definitions:

*referenceable* (or *representable*) DOM ``Node``
	A ``Node`` which can supply the information
	necessary to completely create a ``ContentPointer.``

	This Node is either an ``Element`` (because it must have the  `id
	<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-id>`_,
	and `tagName
	<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-tagname>`_
	properties) with a *referenceable ID*, or a ``Text`` node that is a
	descendent (not necessarily a direct child) of such an ``Element.``

*referenceable ID*
	The value of an ``id`` property of an ``Element`` which is not null,
	not the empty string, and does not begin with one of the following
	excluded prefixes: ``MathJax``.

*synthetic node*
	A ``Node`` not found in the original rendered content.  An example
	of a *synthetic node* is a ``span`` injected client side as part of
	highlighting a portion of a ``Text`` node.

DOM Range to ContentRangeDescription
------------------------------------

Given a DOM ``Range``, ``range``, clients can only generate
``ContentRangeDescription`` objects if they are able to represent the
start and end of the ``range`` object using ``ContentPointer``
objects. If asked to create a ``ContentRangeDescription`` for a range
whose start or end cannot be represented using an
``ContentPointer``, clients should walk the end(s) that are not
representable inward (i.e., narrowing the range) [#]_ until the
range's start and end fall on nodes that can be represented as
``ContentPointers.``

.. [#] Because this usually takes place in the context of a user
  selecting a chunk of text, in the event we can't anchor the start or
  the end, we assume we want the largest representable range contained by the original
  range. That is, we shrink the range inward from the necessary edges.

When generating ``ContentRangeDescription`` objects, clients *MUST*
ignore all *synthetic nodes*.  Because it is impossible to know how
certain clients *MAY* change the content dom as part of
normal operation, the objects generated to model ``Anchored`` content
*MUST* be relative to the oringally rendered content.

Given a ``range`` whose edges can by represented by ``ContentPointers``,
the generation of a ``ContentRangeDescription`` is straightforward. As a
first step the DOM is walked upwards from the range's `commonAncestorComponent
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-commonancestorcontainer>`_
until a node that can be represented as an ``ElementDomContentPointer``
is found. This node is then converted to an
``ElementDomContentPointer`` as described below and the result becomes
the ``ancestor`` of the ``ContentRangeDescription``. With the ancestor
conversion complete,%z the client then converts both the range's `startContainer
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-startcontainer>`_
and `endContainer
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-endcontainer>`_
(at this point both of which we know can be represented by an
``ContentPointer``), and stores the result in the
``ContentRangeDescription`` as ``start`` and ``end``, respectively.

A start or end that is a representable ``Text`` Node will be represented with an
``TextDomContentPointer;`` all other endpoints will be represented with
an ``ElementDomContentPointer.``



Converting an Element to ElementDomContentPointer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Elements represented as an ``ElementDomContentPointer`` *MUST* have both
an ``id`` and ``tagname``. The ``ElementDomContentPointer``'s ``elementId``
*SHOULD* be set to the node's `id
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-id>`_,
and ``elementTagName`` *SHOULD* be set to the node's `tagName
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-tagname>`_.


Converting a Text Node to TextDomContentPointer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the ``startContainer`` or ``endContainer`` in a ``Range`` is a
``Text`` node, the result of conversion will be a
``TextDomContentPointer`` (the "text anchor"). Because ``Text`` nodes
do not have tag names or IDs, a text anchor describes a node that does
have those properties (a containing ``Element``) plus a set of context
objects that define the location of the text within (beneath) that
element.

The first step in generating a text anchor is to identify the
containing element (reference point). From the text node, walk up the
DOM until a refrenceable node is found. This node is converted to an
``ElementDomContentPointer`` object, and it becomes the
``TextDomContentPointer``'s ``ancestor``.

An anchor's ``contexts`` property is made up of a *primary context*
object and an optional set of *additional context* objects.  The first
``TextContext`` object in the ``contexts`` array is the anchor's
*primary context*.  Additional ``TextContext`` objects in the array
are the anchor's *additional context* objects.  An anchor *MUST*
have a *primary context* object and *MAY* have one or more
*additional context* objects.

The anchor's *primary context* and ``edgeOffset`` can be populated
given the ``TextDomContentPointer`` and the Range object. The method
for generating the *primary context* object may differ from the
method used to generate *additional* ``TextContext`` objects. In
order to populate a ``Range`` object's endpoints from
``TextDomContentPointers``, ``contexts`` should contain enough
``NTITextContent`` objects to uniquely identfiy this anchor point
beneath the reference node.

The generation of ``TextContext`` objects is defined here in a
simplistic manner; in the future, this may be refined, but the
algorithm must remain capable of intepreting existing data. Here, we
take a word based approach to extracting context from a ``Text`` node.
Given an anchor, a ``Text`` node, and an offset into that textnode
marking an edge of the range being anchored, the
following procedure should be used to generate the *primary context*
object:

Locate the first word to the left of offset in ``textContent``, left_offset_text.  This string *MAY* contain
trailing whitespace, but *MUST NOT* contain leading whitespace.  If
the offset identifies the beginning of the ``textContent``, e.g.
``offset == 0``, left_offset_text *MUST* be empty.  Locate the first
word to the right of offset, right_offset_text.  This string *MAY*
contain leading whitespace, but *MUST NOT* contain trailing
whitespace.  If the offset identifies the end of ``textContent``, e.g.
``offset = textContent.length``, right_offset_text *MUST* be empty.
Combine left_offset_text and right_offset_text to populate the ``TextContext``
object's ``contextText`` property.  The ``TextContext`` object's
``contextOffset`` property is the index of ``contextText`` in textContent.
If anchor ``role`` is ``start`` this offset is from the right of
textContent.  If anchor ``role`` is ``end`` this offset is from the
left of ``textContext``.

.. note::
	A word is a whitespace delimited set of characters.

Example 1:

This examples shows the start edge of a range that does not fall
at the beggining or end of the ``Text`` node.

.. code-block:: html

	[This text contains a start| endpoint]


.. code-block:: javascript

	{contextText: 'start endpoint', contextOffset: 13}

Example 2:

This example shows the end edge of a range that does not fall
at the beggning or end of the ``Text`` node.

.. code-block:: html

	[This text |contains a start endpoint]


.. code-block:: javascript

	{contextText: 'text contains', contextOffset: 23}


Example 3:

This example shows the end edge of a range that falls at the end
of the ``Text`` node.

.. code-block:: html

	[This text contains an end endpoint|]


.. code-block:: javascript

	{contextText: 'endpoint', contextOffset: 33}


Given a ``Text`` node that is contextually relevant to an anchor
endpoint and an anchor, *additional* ``TextContext`` objects can be
defined as follows.

If the anchor ``role`` is ``start``, ``contextText`` is the last word in the
``Text`` node's ``textContent`` string.  This word *MAY* contain trailing
whitespace, but *MUST NOT* contain leading whitespace.  ``contextOffset``
is the index of ``contextText`` from the right side of the ``Text``
node's ``textContent`` string.  Likewise, if the anchor ``role`` is ``end``,
``contextText`` is the first word in the
``Text`` node's ``textContent`` string.  This word *MAY* contain leading
whitespace, but *MUST NOT* contain trailing whitespace.  ``contextOffset``
is the index of ``contextText`` from the left side of the ``Text``
node's ``textContent`` string.

.. note::
	A ``Text`` node is considered contextually
	relevant to an anchor with a ``role`` of ``start``, if it can be found by
	walking from the ``Text`` node modeled by the anchors *primary
	context* object, using a ``TreeWalker's`` (configured to show non
	whitespace only ``Text`` nodes) ``previousNode`` function.
	Similarily, a ``Text`` node is considered contextually
	relevant to an anchor with a ``role`` of ``end``, if it can be found by
	walking from the ``Text`` node modeled by the anchors *primary
	context* object, using a ``TreeWalker's`` (configured to show non
	whitespace only ``Text`` nodes) ``nextNode`` function.

Given the ability to genreate the *primary context* object,
*additional context* objects and an ``edgeOffset`` as outlined
above, the following procedure can by used to model a range
endpoint, that exists withing a textNode, as a complete
``TextDomContentPointer`` object as follows:

Extract a container and offset from the range object.  If the anchor
``role`` is ``start`` use the range's ``startContainer`` and ``startOffset``
properties.  If the anchor ``role`` is ``end`` use the range's
``endContainer`` and ``endOffset`` properties.  From the container,
walk up the DOM tree to find a referenceable node. Generate an
``ElementDomContentPointer`` object from this node and set it as this
object's ``ancestor``.  Using the container, offset, and
anchor, generate the anchor's *primary context*.  The anchor's
``edgeOffset`` property is the index into the *primary context*
object's ``contextText`` property, of the offset from the range object.

Using a ``TreeWalker`` rooted at the anchor's ``ancestor``, start at container and
iterate non whitespace only ``Text`` node siblings to generate *additional context*
object's.  Continue to iterate creating ``TextContext`` objects
for each sibling until 15 characters have been collected, or 5 context objects have been created.
If anchor ``role`` is ``start``, iterate siblings to the left using the
``TreeWalker's`` ``previousNode`` method.  If anchor ``role`` is ``end``,
iterate siblings to the right using the ``TreeWalker's`` ``nextNode``
method.  The anchor's ``contexts`` property becomes an array whoes
head is the *primary context* object, and whose tail is the
*additional context* objects.

See examples at bottom of page.

.. note::
  In the past, when walking ``Text`` nodes, we have encountered nodes
  whose ``textContent`` is only whitespace.  This behaviour is
  different across the various browsers.  Some browsers specifically
  hide whitespace only ``Text`` nodes when working with the dom others seem
  to actually inject whitespace only ``Text`` nodes as a way to
  maintin formatting information of the original source. Generating
  ``TextContext`` objects that represent whitespace only content provides no additional useful
  information while at the same time introducing potential
  instability.  Because of this, and to ensure consistency across
  various browser implementations, when generating and resolving TextContext these empty
  ``Text`` nodes are skipped during DOM enumeration.

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

ContentRangeDescription to DOM Range
------------------------------------

When creating a DOM Range, ``range``, object from a
``ContentRangeDescription`` object, clients should keep in mind that from
a user perspective it is much worse to anchor something to the wrong
content than to not anchor it at all. If, when reconstructing the range
from the ``ContentRangeDescription``, a client is unable to confidently
locate the ``startContainer``, ``endContainer``, ``startOffset``, or
``endOffset`` using all the ``ContentPointer`` information provided,
the client *should* abort anchoring the content to a specific
location.

.. note::

	To maintain consistency across clients, in this version of the
	spec, confidently means the range produced from a
	``ContentRangeDescription`` following the procedure
	in ``ContentRangeDescription to DOM Range``, would produce the same
	``ContentRangeDescription``  by following the procedure in
	``DOM Range to ContentRangeDescription``.

Anchor resolution starts by resolving the ancestor
``ContentPointer`` to a DOM node (which *must* be a *referenceable* ``Element``).
This provides a starting point when searching for the start and end
``ContentPointers``. The ancestor can also be used to validate parts
of the ``ContentRangeDescription``. For example, the start and end should
be contained in the ancestor. If the ancestor can't be resolved it
should default to the DOM's `documentElement
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#document-element>`_.

Given an ancestor, the DOM can be traversed for the start and end
container ``Nodes`` and offsets needed to construct a range. The type
of ``ContentPointer`` used to model the ``start`` and ``end``
properties of the ``ContentRangeDescription`` will determine how the
dom is searched beneath the ancestor.

If a start and end ``Node``, and offset, cannot be located beneath the ancestor, and the ancestor
is not already the ``documentElement,`` resolution should be tried
again given an ancestor of the ``documentElement.`` If the start does
not come before end (as computed using `compareDocumentPosition
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-node-comparedocumentposition>`_),
the ``ContentRangeDescription`` is invalid and clients *should* abort
range creation and anchoring.

Details on how the different types of ``ContentPointer`` objects
should be searched for are discussed below:

Converting ElementDomContentPointer to a Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Given an ElementDomContentPointer find the DOM ``Element`` whose ID is
``elementId`` within the ancestor. If an ``Element`` with that ID
can't be found or the tagname of the ``Element`` does not match
``elementTagName``, conversion fails and the result is null.  Example
code for resolving ElementDomContentPointer as a start anchor follows:

.. code-block:: javascript

	function locateRangeStartForAnchor(absoluteAnchor, ancestorNode) {
		var tree_walker = document.createTreeWalker( ancestorNode, NodeFilter.SHOW_ELEMENT );

		while( test_node = tree_walker.nextNode() ) {
	    	if(    test_node.id === absoulteAnchor.elementId
			    && test_node.tagName === absoluteAnchor.elementTagName ) {
	       		return text_node;
	    	}
		}
		return null;
	}

An example of updating the range for an ElementDomContentPointer with
type === ``end`` is as follows:

.. code-block:: javascript

	function locateRangeEndForAnchor(absoluteAnchor, ancestorNode, startResult){
		var tree_walker = document.createTreeWalker(ancestorNode, NodeFilter.SHOW_ELEMENT );

		//We want to look after the start node so we reposition the walker
		tree_walker.currentNode =  startResult.node;

		while( test_node = tree_walker.nextNode() ) {
	    	if(    test_node.id === absoulteAnchor.elementId
			    && test_node.tagName === absoluteAnchor.elementTagName ) {
				return test_node;
	    	}
		}
		return null;
	}


Converting TextDomContentPointer to a Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The general algorithm for resolving a ``TextDomContentPointer`` is as
follows.  Begin by resolving the ``ancestor`` to a containing
``Element``.  If the ``ancestor`` cannot be resolved, use the
``ContentRangeDescription``'s ancestor as the containing ``Element``.  This
containing ``Element`` becomes the *reference node* used when searching for
text the anchored range. Using the *refernce node* as the root, create a ``TreeWalker`` to
interate each ``Text`` node, ``textNode``.

For each ``textNode`` create a list of all matches within that node
to the *primary context*.

.. note::

	Multiple matches within a text node are possible. "I see
	a dog. I do not see a cat." for the ``contextText`` "see a" is one such
	example, with matches at indices 2 and 22.

Assign each match a score in ``(0,1]`` based
on the difference between the primary context's ``contextOffset``,
(flipped to a start-based index if it's stored as an end-based index
due to the pointer's role being ``start``) and the index of the
``contextText`` within the ``textNode``'s data. If the two are
identical, it should return 1, and aside from that it should return
lower scores the further the difference is. The current formula is:

.. code-block:: javascript

	score = max(f / (f + abs(contextOffset - index of match)), 0.25)

where ``f`` is defined as

.. code-block:: javascript

	sqrt(textNode.contentText.length) * 2 + 1

.. note::
	These scoring functions are subject to change. The rationale
	behind making ``f`` dependent on the textNode's length is that
	larger paragraphs are likely to have larger and more changes,
	although more changes are more likely to cancel each other out
	hence the square root scaling.

Given a set of matches for the primary context, the secondary context
objects can be used to create a *score multiplier* for each text node.
*score multiplier* can be computing using the following algorithm:

1. Go through all of the secondary contexts and attempt to match them
against the corresponding node. Matches need to be exact, with the
exact offset given by the context object's ``contextOffset`` property,
to pass (which should not be a problem since the ``contextOffset`` is
essentially just the length of the first or last word).

	a. If context object index *i* fails to match, set the *score
	multiplier* to ``i / (i + 0.5)`` (0.66 if the first secondary context
 	fails, 0.8 if the second does, etc) and break.

	b. If all secondary contexts match, check if the number of secondary
	contexts is maximal (ie. either 15+ chars or 5+ secondary contexts). If
	it is, set the *score multiplier* to 1. If it is not, that implies
	that the secondary context generation algorithm was prevented from
	finishing because it reached the beginning or end of the document, and
	therefore must have finished at a null node. Check this assumption. If
	it turns out to be false, set the *score multiplier* to ``n / (n + 0.5)``
	(``n`` being the number of context objects, including the
	primary).

.. note::
	Legacy context objects may exist that represent whitespace only
	``Text`` nodes.  For backwards compatibility these empty
	``TextContext`` objects should be removed prior to scoring
	secondary context objects.

.. warning::
	CUTZ - The number of secondary context objects not being maximal
	doesn't necessarily imply the begining or end of the document.
	Rather it implies the beginning or end of the reference node.

For each text node, multiply the scores of all of the matches for that
text node by the text node's calculated *score multiplier*.

If any match from any of the visited ``textNodes`` has a perfect score,
return that match. If not, then if the ancestor node resolves, return the
highest-scoring match out of all the matches from all visited ``textNodes``.
If the ancestor node does not resolve, return a failure (consider changing
this in the future).

If a ``textNode`` has been identified as the start or end container, a
range can be constructed as follows. If anchor ``role`` is ``start``,
set the ``range's`` ``startContainer`` to ``textNode``. If anchor
``role`` is ``end``, set the ``range's`` ``endContainer`` to
``textNode``. Calculate the text offset by adjusting
the *primary context* object's ``contextOffset`` by  the anchor's
``edgeOffset`` property, and set the
range's ``startOffset``, if anchor ``role`` == ``start``, or
``endOffset``, if anchor ``role`` == ``end``, to the computed value.


Examples
--------

This section will provide example HTML documents with a selection, a representation of
their DOM, and the resulting ``ContentRangeDescription`` created (in JSON
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
			elementId: 'id',
			elementTagName: 'p',
		},
		start: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: 'A', contextOffset: 27 }],
			edgeOffset: 0
		},
		end: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: 'node', contextOffset: 23 }],
			edgeOffset: 4
		},
		selected_text: 'A single selected text node',
		offset: 0
	}


Example 2
~~~~~~~~~

This example spans from one text node to the next.

.. code-block:: html

	<p id="id">
		[|An ]<i>[italic]</i>[ word.]|
	</p>


.. code-block:: javascript

	// The content range
	{
		ancestor: {
			elementId: 'id',
			elementTagName: 'p',
		},
		start: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: 'An', contextOffset: 3 }],
			edgeOffset: 0
		},
		end: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: 'word.', contextOffset: 1 }],
			edgeOffset: 5
		}
	}



Example 3
~~~~~~~~~

This example has multiple text nodes that match. Notice that
the offsets within a text node are the same. How does it resolve?

.. code-block:: html

	<p id="id">
		[This is the ]<i>[first]</i>[ sentence. ]
		<span>[This is |the ]<i>second</i>[ sentence.|]</span>
	</p>


.. code-block:: javascript

	// The content range
	{
		ancestor: {
			elementId: 'id',
			elementTagName: 'p',
		},
		start: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: 'is the', contextOffset: 7 },
					   {contextText: 'sentence. ', contextOffset: 10},
					   {contextText: 'first', contextOffset: 5}],
			edgeOffset: 3
		},
		end: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: 'sentence.', contextOffset: 1 }],
			edgeOffset: 9
		}
	}

Example 4
~~~~~~~~~

This example currently produces a model that is ambiguous, resulting
in the wrong content being highlighted

.. code-block:: html

	<p id="id">
		[|This is a sentence]
		<b class="bfseries"><em>WOW</em></b>
		[. Another sentence]<em>YIKES</em>[ and ]<em>foo</em>[. |]
	</p>

.. code-block:: javascript

	// The content range
	{
		ancestor: {
			elementId: 'id',
			elementTagName: 'p',
		},
		start: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: 'This', contextOffset: 18 }],
			edgeOffset: 0
		},
		end: {
			ancestor : {elementId: 'id', elementTagName: 'p'},
			contexts: [{ contextText: '. ', contextOffset: 0 }],
			edgeOffset: 2
		}
	}

The user desires the entire paragraph to be highlighted.  However,
when resolving the model, the end context is ambigious and we
incorrectly end the highlight just after the first '.' following 'WOW'.

Anchor Migration
================

As time goes on and content around anchored items changes, we may need
some system for migrating/updating/correcting ``ContentRangeDescriptions``.
This likely has to happen on the client side and depending on the
severity of the change, in the worst case, we may want some kind of
input from the user. Does your highlight or note still make sense here
even though the content has changed? We should think about if and how
this sort of thing can happen.
