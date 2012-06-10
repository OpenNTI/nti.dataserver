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

	abstract class ContentRangeDescription {
		ContentPointer start; //must not be nil
		ContentPointer end; //must not be nil
		ContentPointer ancestor; //must not be nil
	}

	abstract class ContentPointer {}

	abstract class DomContentPointer : ContentPointer {
		string elementId;    //dom id of the anchoring node
		string elementTagName; //tagname of the anchoring node
		string type; //The type/kind of anchor this is being used for
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


Anchorable content *MUST* implement the abstract class ``NTIAnchored`` to
specify the ``applicableRange`` it is anchored to. ``ContentRangeDescription``
objects must have well formed ``ContentPointer`` objects for start, end,
and ancestor. It *SHOULD* be considered an error if the start, end or
ancestor of a ContentRangeDescription object is undefined. A well formed
ContentRangeDescription with valid start, end, and ancestor values should
be used to create well formed DOM Range objects.

Objects of type ``ContentPointer`` provide the information required to
identify a location in the content for use as the start or end of a
range or to identify a node that contains the start and end (common
ancestor). The abstract base class ``ContentPointer`` contains the
minimum amount of information required to identify an anchor in NTI
content.

* ``elementId`` is the DOM ID of an arbitrary node in the content.
* ``elementTagName`` is the tag name for the node identified by
  ``elementId``. Both these properties *MUST NOT* be nil.
* ``type`` specifies how this anchor is to be used.  It *MUST*
  take one of the following three values: ``"start"``, ``"end"``,
  ``"ancestor"``

Concrete subclasses of ``ContentPointer`` should provide the
remaining information required to identify content location relative
to the anchor provided by the abstract base class.

ContentPointer implementations
------------------------------

The class ``ContentPointer`` is abstract. A few subclasses are
specified which provide concrete storage and rules for resolution. In
the future, more subclasses may be added.

ElementDomContentPointer
~~~~~~~~~~~~~~~~~~~~~~~~

An ``ElementDomContentPointer`` adds no information to the abstract base
class. Its purpose is to identify a node that things can be anchored
relative to. This type of anchor is most often seen as the ``ancestor``
portion of an ``ContentRangeDescription``.

TextDomContentPointer
~~~~~~~~~~~~~~~~~~~~~

Content is anchored within text by describing a containing element,
plus some context information used to traverse to the anchored text:

.. code-block:: cpp

	//Adds redundant information about text content
	class TextDomContentPointer : ContentPointer {
		TextContext[] contexts; //An array of TextContext
		                          //objects providing context for this anchor
		int edgeOffset; //The offset from the start or end of content_text of the edge
	}


This class should be used to reference portions of DOM `Text nodes
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#interface-text>`_
as ``ContentPointer`` objects, and is useful when a range begins or
ends inside of ``Text`` content.


* ``contexts`` is an array of ``TextContext`` objects that provide
  contextual information for the ``range`` endpoint represented by
  this anchor. The length of ``contexts`` *MUST* be at least one. The
  first ``TextContext`` object in the array provides the *primary
  context* for this anchor, and represents a snippet of text adjacent
  to the ``range`` endpoint identified by this anchor. Additional
  ``TextContext`` objects in the array provide further context.
  Those objects closest to the beginning of the array provide the most
  specific (nearest) context while those towards the end provide less
  specific (more distant) context. If this anchor has a ``type``
  *EQUAL TO* ``start`` the additional context objects mirror the
  ``Text`` nodes returned by repeateadly asking `TreeWalker
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_
  for ``previousNode`` starting from the node used to generate the
  *primary context* object. Similarily, if this anchor has a ``type``
  *EQUAL TO* ``end`` the additional context objects mirror the
  ``Text`` nodes returned by repeateadly asking `TreeWalker
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#treewalker>`_
  for ``nextNode`` starting from the node used to generate the
  *primary context* object. See ``Converting a Text Node to
  TextDomContentPointer`` for more information.
* ``edgeOffset`` is the character offset from the start of the
  ``primary context`` object's ``context_text`` string to the location
  of the edge thie anchor represents.


When specifying context information for a `TextDomContentPointer` the
following `TextContext` will be used:

.. code-block:: cpp

	//Provide a snippet of text context
	class TextContext {
		string contextText; //A chunk of text that can be used as context
		int context_offset; //offset of contextText into context_offset's
							//containing text node
	}

* ``contextText`` is a string contained in the `textContent or nodeValue
  <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-node-textcontent>`_
  of a ``Text`` node near the ``TextDomContentPointer`` this object is
  providing context for.
* ``context_offset`` is the index of ``contextText`` from the start or end of ``textContent``.
  ``content_offset`` *MUST* be an integer greater than or equal to zero.  Negative values are reserved for future use.
  If this object is providing context for an anchor with a type *EQUAL TO* ``"start"``, ``content_offset``
  represents the character index from the end (right) of ``textContent``.
  If this object is providing context for an anchor with a type *EQUAL TO* ``"end"``,
  ``content_offset`` represents the index from the start (left) of
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
	and `tag_name
	<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-tagname>`_
	properties) with a *referenceable ID*, or a ``Text`` node that is a
	descendent (not necessarily a direct child) of such an ``Element.``

*referenceable ID*
	The value of an ``id`` property of an ``Element`` which is not null,
	not the empty string, and does not begin with one of the following
	excluded prefixes: ``MathJax``.

DOM Range to ContentRangeDescription
------------------------------------

Given a DOM ``Range``, ``range``, clients can only generate
``ContentRangeDescription`` objects if they are able to represent the
start and end of the ``range`` object using ``ContentPointer``
objects. If asked to create an ``ContentRangeDescription`` for a range
whose start or end cannot be represented using an
``ContentPointer``, clients should walk the end(s) that are not
representable inward (i.e., narrowing the range) [#]_ until the
range's start and end fall on nodes that can be represented as
``ContentPointers.``

.. [#] Because this usually takes place in the context of a user
  selecting a chunk of text, in the event we can't anchor the start or
  the end, we assume we want the largest representable range contained by the original
  range. That is, we shrink the range inward from the necessary edges.

Given a ``range`` whose edges can by represented by ContentPointers,
the generation of an ContentRangeDescription is straightforward. As a
first step the DOM is walked upwards from the range's `commonAncestorComponent
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-range-commonancestorcontainer>`_
until a node that can be represented as a ``ElementDomContentPointer``
is found. This node is then converted to an
``ElementDomContentPointer`` as described below and the result becomes
the ``ancestor`` of the ``ContentRangeDescription``. With the ancestor
conversion complete the client then converts both the range's `startContainer
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
an ``id`` and ``tagname``. The ``ContentPointer``'s ``elementId``
*SHOULD* be set to the node's `id
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-element-id>`_,
and ``elementTagName`` should be set to the node's `tag_name
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
DOM until a refrenceable node is found. This node's ID and tag name
become the ``elementId`` and ``elementTagName`` respectively.

An anchor's ``contexts`` property is made up of a *primary context*
object and an optional set of *subsequent context* objects.  The first
``TextContext`` object in the ``contexts`` array is the anchor's
*primary context*.  Additional ``TextContext`` objects in the array
are the anchor's *subsequent context* objects.  An anchor *MUST*
have a *primary context* object and *MAY* have one or more
*subsequent context* objects.

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

.. JAM: Define this in words, not an implementation. An implementation
.. is not a specification. An implementation contains unnecessary
.. details that distract from what is actually intended, and probably contains bugs.
.. Pseudo-code is alright for *examples*. A reference implementation
.. can be provided in addition.
.. Another problem with mixing in implementations is that it makes it
.. unclear what is actually being specified (i.e., the data structures
.. required for interoperability).

Locate the first word to the left of offset in ``textContent``, left_offset_text.  This string *MAY* contain
trailing whitespace, but *MUST NOT* contain leading whitespace.  If
the offset identifies the beginning of the textContent, e.g.
``offset == 0``, left_offset_text *MUST* be empty.  Locate the first
word to the right of offset, right_offset_text.  This string *MAY*
contain leading whitespace, but *MUST NOT* contain trailing
whitespace.  If the offset identifies the end of textContent, e.g.
``offset = textContent.length``, right_offset_text *MUST* be empty.
Combine left_offset_text and right_offset_text to populate the ``Text
Context`` object's ``context_text`` property.  The ``Text Context`` object's
``context_offset`` property is the index of ``context_text`` in textContent.
If anchor ``type`` is ``start`` this offset is from the right of
textContent.  If anchor ``type`` is ``end`` this offset is from the
left of textContnet.

.. nate::
	A word is a whitespace delimited set of characters.

Example 1:

.. code-block:: html

	[This text contains a start| endpoint]


.. code-block:: javascript

	{context_text: 'start endpoint', context_offset: 13}

Example 2:

.. code-block:: html

	[This text |contains a start endpoint]


.. code-block:: javascript

	{context_text: 'text contains', context_offset: 23}


Example 3:

.. code-block:: html

	[This text contains an end endpoint|]


.. code-block:: javascript

	{context_text: 'endpoint', context_offset: 33}


Given a ``Text`` node that is contextually relevant to an anchor
endpoint and an anchor, *subsequent* ``NTITextContext`` objects can be
defined as follows.

If the anchor ``type`` is ``start``, ``context_text`` is the last word in the
``Text`` node's textContent string.  This word *MAY* contain trailing
whitespace, but *MUST NOT* contain leading whitespace.  ``context_offset``
is the index of ``context_text`` from the right side of the ``Text``
node's textContent string.  Likewise, if the anchor ``type`` is ``end``,
``context_text`` is the first word in the
``Text`` node's textContent string.  This word *MAY* contain leading
whitespace, but *MUST NOT* contain trailing whitespace.  ``context_offset``
is the index of ``context_text`` from the left side of the ``Text``
node's textContent string.

.. note::
	A ``Text`` node is considered contextually
	relevant to an anchor with a type of ``start``, if it can be found by
	walking from the ``Text`` node modeled by the anchors *primary
	context* object, using a ``TreeWalker's`` ``previousNode`` function.
	Similarily, a ``Text`` node is considered contextually
	relevant to an anchor with a type of ``end``, if it can be found by
	walking from the ``Text`` node modeled by the anchors *primary
	context* object, using a ``TreeWalker's`` ``nextNode`` function.

Given the ability to genreate the *primary context* object,
*subsequent context* objects and an ``edge_offset`` as outlined
above, the following procedure can by used to model a range
endpoint, that exists withing a textNode, as a complete
``TextDomContentPointer`` object as follows:

Extract a container and offset from the range object.  If the anchor
``type`` is ``start`` use the range's ``startContainer`` and ``startOffset``
properties.  If the anchor ``type`` is ``end`` use the range's
``endContainer`` and ``endOffset`` properties.  From the container,
walk up the DOM tree to find a referenceable node. This node's ``id``
and ``tagName`` become the anchor`s ``elementId`` and
``elementTagName`` respectively.  Using the container, offset, and
anchor, generate the anchor's *primary context*.  The anchor's
``edgeOffset`` property is the index into the *primary context*
object's ``context_text`` property, of the offset from the range object.

Using a ``TreeWalker`` rooted at the reference node, start at container and
iterate ``Text`` node siblings to generate *subsequent context*
object's.  Continue to iterate, creating ``NTITextContext`` objects
for each sibling until 15 characters have been collected or 5 context objects have been created.
If anchor type is ``start``, iterate siblings to the left using the
``TreeWalker's`` ``previousNode`` method.  If anchor type is ``end``,
iterate siblings to the right using the ``TreeWalker's`` ``nextNdoe``
method.  The anchor's ``contexts`` property becomes an array whoes
head is the *primary context* object, and whose tail is the
*subsequent context* objects.

See examples at bottom of page.

.. warning::
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

ContentRangeDescription to DOM Range
------------------------------------

When creating a DOM Range, ``range``, object from an
``ContentRangeDescription`` object, clients should keep in mind that from
a user perspective it is much worse to anchor something to the wrong
content than to not anchor it at all. If, when reconstructing the range
from the ``ContentRangeDescription``, a client is unable to confidently
locate the ``startContainer``, ``endContainer``, ``startOffset``, or
``endOffset`` using all the ``ContentPointer`` information provided,
the client *should* abort anchoring the content to a specific
location.

.. JAM: FIXME: What are we trying to say here? We're not defining an
.. implementation, we're describing the algorithm.

.. code-block:: javascript

	//deleted


Anchor resolution starts by resolving the ancestor
``ContentPointer`` to a DOM node (which *must* be an ``Element``).
This provides a starting point when searching for the start and end
``ContentPointers``. The ancestor can also be used to validate parts
of the ``ContentRangeDescription``. For example, the start and end should
be contained in the ancestor. If the ancestor can't be resolved it
should default to the DOM's `documentElement
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#document-element>`_.

Given an ancestor the DOM can then be traversed for the start and end
container ``Nodes`` and offsets needed to construct a range. If a start
and end ``Node`` cannot be located beneath the ancestor, and the ancestor
is not already the ``documentElement,`` resolution should be tried
again given an ancestor of the ``documentElement.`` If the start does
not come before end (as computed using `compareDocumentPosition
<http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#dom-node-comparedocumentposition>`_),
the ``ContentRangeDescription`` is invalid and clients *should* abort
range creation and anchoring. Given an ``ContentRangeDescription`` the
following procedure should be used to resolve a dom range.

.. JAM: FIXME: Please actually define what we're trying to do.


.. code-block:: javascript

	//deleted



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
	       		return {node: test_node, confidence: 1};
	    	}
		}
		return {confidence: 0};
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
				return {node: test_node, confidence: 1};
	    	}
		}
		return {confidence: 0};
	}


Converting TextDomContentPointer to a Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The general algorithm for resolving a ``TextDomContentPointer`` is a
follows.  Begin by resolving the *reference node* using
``elementId`` and ``elementTagName``.  If the *reference node*
can't be resolved, use the ``ancestor`` as the *reference node*.  Using
the *refernce node* as the root, create a ``TreeWalker`` to
interate each ``Text`` node, ``textNode``, using the ``nextNode`` method.

For each ``textNode`` check if the *primary context* object matches
``textNode``. If it does, using a ``TreeWalker`` rooted at *reference
node*, compare each *additional context* object by walking the tree
using the ``previousNode`` method, if anchor ``type`` is ``start``, or
forward using the ``nextNode`` method, if the anchor ``type`` is
``end``. If all context objects match, ``textNode`` will become the
range's ``startContainer`` if the anchor ``type`` is ``start``, or
``endContainer`` if the anchor ``type`` is ``end``. If not all the
context objects match, continue the outer loop by comparing context
objects for the next ``textNode``.

If a ``textNode`` has been identified as the start or end container, a
range can be constructed as follows. If anchor ``type`` is ``start``,
set the ``ranges`` ``startContainer`` to ``textNode``. If anchor
``type`` is ``end``, set the ``ranges`` ``endContainer`` to
``textNode``. Calculate the text offset by adjusting
the *primary context* object's ``contextOffset`` by  the anchor's
``edgeOffset`` property, and set the
range's ``startOffset``, if anchor ``type`` == ``start``, or
``endOffset``, if anchor ``type`` == ``end``, to the computed value.


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
			elementId: 'id',
			elementTagName: 'p',
			contexts: [{ contextText: 'A', context_offset: 26 }]
			edgeOffset: 0
		},
		end: {
			elementId: 'id',
			elementTagName: 'p',
			contexts: [{ contextText: 'node', context_offset: 22 }],
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
		[|An] <i>[italic]</i> [word.]|
	</p>


.. code-block:: javascript

	// The content range
	{
		ancestor: {
			elementId: 'id',
			elementTagName: 'p',
		},
		start: {
			elementId: 'id',
			elementTagName: 'p',
			contexts: [{ contextText: 'An', context_offset: 2 }]
			edgeOffset: 0
		},
		end: {
			elementId: 'id',
			elementTagName: 'p',
			contexts: [{ contextText: 'word.', context_offset: 0 }],
			edgeOffset: 5
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
			elementId: 'id',
			elementTagName: 'p',
		},
		start: {
			elementId: 'id',
			elementTagName: 'p',
			contexts: [{ contextText: 'is the', context_offset: 3 },
					   {contextText: 'sentence.', context_offset: 9},
					   {contextText: 'first', context_offset: 5},
					   {contextText: 'the'}, context_offset: 3]
			edgeOffset: 8
		},
		end: {
			elementId: 'id',
			elementTagName: 'p',
			contexts: [{ contextText: 'sentence.', context_offset: 0 }],
			edgeOffset: 9
		}
	}


Anchor Migration
================

As time goes on and content around anchored items changes, we may need
some system for migrating/updating/correcting ``ContentRangeDescriptions``.
This likely has to happen on the client side and depending on the
severity of the change, in the worst case, we may want some kind of
input from the user. Does your highlight or note still make sense here
even though the content has changed? We should think about if and how
this sort of thing can happen.
