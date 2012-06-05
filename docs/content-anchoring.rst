Anchoring
=========

This document describes the method in which anchorable content is modeled as such, and the methods used to convert NTIAnchorable content to and from dom selections/ranges.

Considerations
--------------

We have the requirement to anchor various types of user data (at this point the requirement is for notes and highlights) to specific ranges of content within a container.  Beyond the basic explicit requirement made above, two implicit requirements need to be made explicit.

First, it is desired that anchors are as robust as possible to content changes such as the addition, removal or reordering of paragraphs, graphics, embedded media, etc. Preferably, even intra-paragraph changes would have minimal effect. This means that anchors need to store redundant information to be used as backup, and they also need to store enough information to know whether or not they have successfully located their target (assumed: highlighting/noting the wrong thing is worse than displaying a "missing highlight" indicator). (As a corollary, it also means that document-global information, such as a DOM range or XPath is not sufficient.)

Second, it is desired that anchors are as "local" as possible, to support "mashups," embedding, and reuse of content. A concrete, customer use-case of this the ability to recombine MathCounts problems from their own worksheets into custom worksheets ("I want to search for all problems about circles and make that a worksheet"). When this happens, notes/discussions attached to the questions should be able to come along. This ties in to the corollary of the first point.

To best support these two requirements we want to anchor things to authored content whenever possible.  For example, anchors should be tied to authored paragraphs, questions, or images rather than their containing divs used to layout those things.  Not only does this allow for robustness and mashups as described above, doing this should also make anchors robust to layout changes.  For example, a portion of text originally in the main body of a page that gets moved to a callout in the sidebar.

Assuming clients can perform any rendering or calculations required to show NTIAnchored content using objects conforming to the Dom Range Specification, range object, clients need only be concerned with the conversion of our modeled anchorable objects to/from range objects.

Modeling Anchorable Content
---------------------------

Taking inspiration from the `Dom Range Specification <http://dvcs.w3.org/hg/domcore/raw-file/tip/Overview.html#ranges>`_, we can use the following object model to represent anchored content:

::

	// An object associated with some portion of a content unit
	abstract class NTIAnchored {
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

*TODO* add back in xpath for fast first pass on NTIContentAnchor.  Removed to simplify thought process right now

Anchorable content *MUST* implement the abstract class NTIAnchored to specify the content_range it is anchored to.  NTIContentRangeSpec objects must have well formed NTIContentAnchor objects for start, end, and ancestor.  It *SHOULD* be considered an error if the start, end or ancestor of a NTIContentRangeSpec object is undefined.  A well formed NTIContentRangeSpec with valid start, end, and ancestor values should be used to create well formed dom range objects.

Objects of type NTIContentAnchor provide the information required to identify a location in the content for use as the start or end of a range or to identify a node that contains the start and end (common ancestor).  The abstract base class NTIContentAnchor contains the minimum amount of information required to identify an anchor in nti content. anchor_dom_id is the dom id of a node in the content.  anchor_tag_name is the tag name for the node identified by anchor_dom_id.  Both these properties *MUST NOT* be nil.  Concrete subclasses of NTIContentAnchor should provide the remaining information required to identify content location relative to the anchor provided by the abstract base class.

NTIContentAnchor implementations
++++++++++++++++++++++++++++++++

NTIContentAbsoluteAnchor
************************

An NTIContentAbsoluteAnchor adds no information to the abstract base class.  Its purpose is to identify a node that things
can be anchored relative to.  This type of anchor is most often seen as the ancestor portion of an NTIContentRangeSpec.

NTIContentTextAnchor
********************

::

	//Adds redundant information about text content
	class NTITextContentAnchor : NTIContentAnchor {
		string node_text; //The nodeValue for the textnode originally used as an anchor
		string selected_node_text; //The portion of node_text that was originally selected.
		int node_text_offset; //The offset into node_text of the endpoint
		string context_text; //A chunk of test surrounding the endpoint.  This should be a smaller more manageable chunk of text than node value and can be used when node_text no longer matches
		int context_text_offset; //The offset into context_text of the endpoint
	}


This class should used to reference portions of textNodes as NTIContentAnchor objects, and is useful when a range begines or ends inside of textNode content.  node_text is the nodeValue of the textNode this anchor represents.  selected_node_text is the portion of node_text that was contained in the range.  node_text_offset is the index into node_text of the endpoint.  In the case where the text local to an anchor does not change, these three properties should be enough to relocate the endpoint of a range.  However, if the textNode content changes or the way in which a chunk of text is broken into textNodes various cross browser these three fields may not be enough.  Two additional fields context_text and context_text_offset can be used as a fallback.  context_text is a chunk of text surrounding the endpoint.  This text may contain text that spans adjacent textNodes.  context_text_offset is the offset into context_text of the endpoint.


NTIContentRangeSpec conversion
------------------------------

To maintain parity between clients it is important the same algorithm be used for converting NTIContentRangeSpec objects to and from dom ranges.

DOM Range to NTIContentRangeSpec
++++++++++++++++++++++++++++++++

Given a DOM Range, range, clients can only generate NTIContentRangeSpec objects if they are able to reference the start and end of the range object using NTIContentAnchors. If asked to create an NTIContentRangeSpec for a range whose start or end cannot be represented using an NTIContentAnchor clients should walk the end(s) that are not representable inward[#]_ until it finds a ranges whose start and end can be represented by NTIContentAnchors.

.. [#] Because this usually takes place in the context of a user selecting a chunk of text, in the event we can't anchor the start or the end, we assume we want the largest range contained by the original range. I.E. we shrink the range inward from the necessary endpoints.

Given a range whose endpoints can by represented by NTIContentAnchors, the generation of an NTIContentRangeSpec is straightforward.  As a first step the dom is walked upwards from the commonAncestorComponent until a node that can be represented as a NTIContentAbsoluteAnchor is found.  This node is then converted to an NTIContentAbsoluteAnchor as described below and the result becomes the ancestor of the NTIContentRangeSpec.  With the ancestor conversion complete the client then converts both the startContainer and endContainer, at this point both of which we know can be represented by an NTIContentAnchor, and the values of stored as the NTIContentRangeSpec start and end, respectively.

Converting a node to NTIContentAbsoluteAnchor
*********************************************

Nodes represented as an NTIContentAbsoluteAnchor *MUST* have both an id and tagname.  The NTIContentAnchor anchor_dom_id should be set to the nodes id, and anchor_tag_name should be set to the nodes tag_name.

Converting a node to NTIContentTextAnchor
*****************************************

Only text nodes can be represented by NTIContentTextAnchor objects, text anchor.  A text anchor consists of a reference point and a set of fields used to find the endpoint in the some text beneath that reference point.  The first step in generating a text anchor is to identify the reference point.  From the text node walk up the dom until a refrenceable node, a node with an id and tagname, is found.  This nodes id and tagname become the anchor_dom_id and anchor_tag_name respectively.

node_text, selected_node_text, and node_text_offset can be populated given the textNode and the range.  node_text takes the value of the node's nodeValue property.  The node_text_offset is the ranges startOffset or endOffset if we are working on the start or end anchor respectively.  Finally, selected_node_text is the substring of node_text from beginning to node_text_offset if we are working on the start anchor, or from node_text_offset to the end if we are working on the end anchor.

The generation of context_text is less well defined and may change from anchor to anchor based on some set of heuristics.  The value of context_text *MAY* be text that originally spanned multiple consecutive text nodes.  context_text *should* contain some portion of the text that originally surrounded the range's offset.  For example give the structure below, <t> represents textNode and '|' marks the range start and end, context_text for the end anchor may be 'quick brown fox, jumps over the lazy'.

::

	<p id='foo'>
		<t>|The quick</t><t> brown fox, jumps</t><t> over| the lazy dog</t>
	</p>

context_text_offset is then set to the offset in the context_text of the endpoint.  In our example above that would be 22.

NTIContentRangeSpcc to DOM Range
++++++++++++++++++++++++++++++++

When converting DOM Range, range, objects from NTIContentRangeSpec objects, clients should keep in mind that from a user perspective it is much worse to anchor something to the wrong content than to not anchor it at all.  If when reconstructing the range from the NTIContentRangeSpec, a client is unable to locate the startContainer, endContainer, startOffset, or endOffset using all the NTIContentAnchor information provided, the client should abort anchoring the content to a specific location.

Anchor resolution starts by resolving the ancestor NTIContentAnchor to a node.  This provided a starting point when searching for the start and end point.  The ancestor can also be used to validate parts of the NTIContentRangeSpec.  For example, the start and end should be contained in the ancestor.  If the ancestor can't be resolved it should default to document.body.

Given an ancestor the dom can then be traversed for the start and end containers/offsets needed to construct a range.  If a start and end cannot be located beneath the ancestor, and the ancestor is not already document.body, resolution should be tried again given an ancestor of document.body.  If the end does not come after the start the NTIContentRangeSpec is invalid and clients should fail to create the dom.



Converting NTIContentAbsoluteAnchor to a node
*********************************************

Given an NTIContentAbsoluteAnchor find the node whose id is anchor_dom_id.  If a node with that id can't be found or the tagname of the node does not match anchor_tag_name return null.

Converting NTIContentTextAnchor to a node
*****************************************

NTIContentTextAnchor resolution should begin by locating the reference node.  If the reference node cannot be located the client should fail to resolve the anchor.  *TODO* instead of failing maybe we just have to search from the ancestor/document.body?  Given a reference node clients should search for a textNode beneath it whose nodeValue is node_text.  If a textNode is found it becomes the ranges container node and the offset stored in node_text_offset become the ranges offset for that endpoint.

In the event a textNode can't be located, clients should search beneath the reference node for context_text.  It is important to remember that context_text may span multiple text nodes.  If context_text can be located the context_text_offset should be used to identify the text node containing the endpoint.  That textNode and a computed offset can be used for the ranges endpoint.

Anchor Migration
----------------

As time goes on and content around anchored items changes, we may need some system for migrating/updating/correcting NTIContentRangeSpecs.  This likely has to happen on the client side and depending on the severity of the change, in the worst case, we may want some kind of input from the user.  Does your highlight or note still make sense here even though the content has changed?  We should think about if and how this sort of thing can happen.

