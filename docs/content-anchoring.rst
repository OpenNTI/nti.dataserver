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
	broken down into two classes, ``Inside`` and ``Outside``. ``Inside`` changes
	are those changes in the content that occur in between a ranges endpoints.
	``Outside`` changes are those changes which occur outside, or surrounding,
	the ranges endpoints.

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
show NTIAnchored content using objects conforming to the Dom Range
Specification's, ``Range`` object, clients need only be concerned with the
conversion of our modeled anchorable objects to/from range objects.

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

Concrete subclasses of ``NTIContentAnchor`` should provide the
remaining information required to identify content location relative
to the anchor provided by the abstract base class.

NTIContentAnchor implementations
--------------------------------

NTIContentAbsoluteAnchor
~~~~~~~~~~~~~~~~~~~~~~~~

An ``NTIContentAbsoluteAnchor`` adds no information to the abstract base
class. Its purpose is to identify a node that things can be anchored
relative to. This type of anchor is most often seen as the ancestor
portion of an ``NTIContentRangeSpec``.

NTIContentTextAnchor
~~~~~~~~~~~~~~~~~~~~

.. code-block:: cpp

	//Adds redundant information about text content
	class NTITextContentAnchor : NTIContentAnchor {
		string context_text; //A chunk of test surrounding the edge.
		int context_offset; //The offset from the start or end of nodeValue of context_text
		int edge_offset; //The offset from the start or end of content_text of the edge
	}


This class should be used to reference portions of DOM `Text nodes
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#interface-text>`_
as ``NTIContentAnchor`` objects, and is useful when a range begins or
ends inside of ``Text`` content.

* ``context_text`` is a string contained in the `textContent or nodeValue
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-node-textcontent>`_
  of the ``Text`` node this anchor represents.
* ``context_offset`` is the index of ``context_text`` from the start or end of ``textContent``.
  If this anchor represents the ``start`` of the ``NTIContentRangeSpec``, ``content_offset`` must be
  >= 0, and it represents the index from the start of ``textContent``.  If this anchor represents
  the ``end`` value of the ``NTIContentRangeSpec``, ``content_offset`` must be <=0, and it represents
  the index from the end of ``textContent``.
* ``edge_offset`` is index from the start of ``context_text`` to the location of the edge.

.. note::
	The original ``NTIContentTextAnchor`` specification allowed for ``context_text`` to span
	multiple nodes.  However, because during resolution, the fallback case of searching from the
	document root is common, the performance implications of allowing ``context_text`` to span
	nodes may be difficult to overcome.

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

* ``selected_text`` is the subsection of the ``Text`` node's nodeValue that falls
  within the ``start`` and ``end`` of the range spec.
* ``offset`` is the index into the ``Text`` node's nodeValue of ``selected_text``


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

Given a DOM Range, ``range``, clients can only generate
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
first step the DOM is walked upwards from the ``range``'s `commonAncestorComponent
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-commonancestorcontainer>`_
until a node that can be represented as a ``NTIContentAbsoluteAnchor``
is found. This node is then converted to an
``NTIContentAbsoluteAnchor`` as described below and the result becomes
the ``ancestor`` of the ``NTIContentRangeSpec``. With the ancestor
conversion complete the client then converts both the ``range``'s `startContainer
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-startcontainer>`_
and `endContainer
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-endcontainer>`_
(at this point both of which we know can be represented by an
``NTIContentAnchor``), and stores the result in the
``NTIContentRangeSpec`` as ``start`` and ``end``, respectively.

A start or end that is a representable ``Text`` Node will be represented with an
``NTContentTextAnchor;`` all other endpoints will be represented with
an ``NTIContentAbsoluteAnchor.``

In the special case where ``start`` and ``end`` are ``NTIContentTextAnchor`` objects that
represent the same ``Text`` node, the subclass ``NTIContentSimpleTextRangeSpec`` should be
produced.  In this case ``selected_text`` should be populated from the ``start`` anchors nodeValue
from the range's ``startOffset`` to ``endOffset``.  ``offset`` should be populated with the range's
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
``Element``) plus the location of the text within (beneath) that element.

The first step in generating a text anchor is to identify the
containing element (reference point). From the text node walk up the
DOM until a refrenceable node is found. This node's ID and tag name
become the ``anchor_dom_id`` and ``anchor_tag_name`` respectively.

The anchor's ``context_text``, ``context_offset``, and
``edge_offset`` can be populated given the ``Text`` node and the
Range object. The generation of ``context_text`` may change
from anchor to anchor based on some set of heuristics.  In order to
resolve a range endpoints from ``NTIContentTextAnchors``, ``context_text``
should be large enough to be unique, but small enough such that it is not too
fragile to content changes near the endpoint.  In general, the more context used,
the more fragile the ``NTIContentTextAnchor``.

The genration of ``context_text`` should be designed in such a way that the
heuristics can be easily tweaked.  As a first pass, ``context_text`` should be generated
such that it contains 6 characters on either side of the endpoint.  In the event that the
edge is closer than 6 characters to the start or end of the ``Text`` node's nodeValue clients
should use as many characters as possible.

When working on ``start``, given ``context_text``, ``context_offset`` and ``edge_offset`` can
be calculated as such:

.. code-block:: javascript

	var context_text = generateContextText(range);

	context_offset = range.startContainer.indexOf(context_text);
	edge_offset = range.startOffset - contextOffset;

Similarly, when working on ``end``, given ``context_text``, ``context_offset`` and ``edge_offset`` can
be calculated as such:

.. code-block:: javascript

	var context_text = generateContextText(range);

	context_offset = -1 * (range.endContainer.nodeValue.length
							- range.endContainer.indexOf(context_text));
	edge_offset = range.endOffset - range.endContainer.nodeValue.length + contextOffset;

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

When creating a DOM Range, ``range``, object from an ``NTIContentRangeSpec``
object, clients should keep in mind that from a user perspective it
is much worse to anchor something to the wrong content than to not
anchor it at all. If when reconstructing the range from the
``NTIContentRangeSpec``, a client is unable to confidently locate the ``startContainer``,
``endContainer``, ``startOffset``, or ``endOffset`` using all the ``NTIContentAnchor``
information provided, the client *should* abort anchoring the content to
a specific location.

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
range creation and anchoring.

NTIContentSimpleTextRangeSpec to DOM Range
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the event a range spec is actually an ``NTIContentSimpleTextRangeSpec`` a fast first pass can
be attempted to generate the ``range``.  As above, anchor resolution begins by resolving the
``ancestor`` component of the ``spec``.  If the ancestor cannot be resolved the ``document.body``
should be used.  Given the resolved ``ancestor`` as a reference node, clients should search for a
``Text`` node *beneath* it whose ``textContent`` contains ``selected_text`` at ``offset``. This is
conveniently done with a `TreeWalker <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_:

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
``anchor_dom_id``. If an ``Element`` with that ID can't be found or the tagname of
the ``Element`` does not match ``anchor_tag_name``, conversion fails
and the result is null.

Converting NTIContentTextAnchor to a Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``NTIContentTextAnchor`` resolution should begin by locating the
reference node as per ``NTIContentAbsoluteAnchor``. If the reference
node cannot be located ``document.body`` should be used instead.

Given a reference node, clients should search *beneath* it for the textNode that contains ``context_text``
most closely to ``context_offset``.  Again this is
conveniently done with a `TreeWalker <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_:
The example code below demonstrates resolving ``start`` and ``end`` anchors to a textNode

.. code-block:: javascript

	var ref_node    = //...
	var anchor = //...
	var isStart = //...

	var textNode = null
	var distanceFromOffset = Number.MAX_VALUE;

	var tree_walker = document.createTreeWalker( ref_node, NodeFilter.SHOW_TEXT );

	while( test_node = tree_walker.nextNode() ) {
		var idx = text_node.textContent.indexOf(anchor.context_text);
		if(idx >= 0){
			var normalizedOffset = anchor.offset
			//Recall end anchor offsets are from the right
			if( !isStart ){
				normalizedOffset = text_node.nodeValue.length + anchor.context_offset
			}

			var distance = abs(normalizedOffset - idx);
	   	 	if( distance < distanceFromOffset ) {
	        	distanceFromOffset = distance;
	        	textNode = text_node;
	    	}
		}
	}

At this point, if clients are unable to resolve the ``NTIContentTextAnchor`` to a node, it should be treated as
an anchor that can no longer be resolved.  Future versions of this spec may apply more heuristics and fallbacks.

Given a textNode that represents a ``start`` or ``end`` the range object can be adapted as follows:

.. code-block:: javascript

	var node = //...
	var range = /...
	var isStart = //..
	var anchor = //...

	if(isStart){
		range.setStart(node, node.textValue.indexOf(anchor.context_text) + anchor.edge_offset);
	}
	else{
		range.setEnd(node, node.textValue.indexOf(anchor.context_text) + anchor.edge_offset)l
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
