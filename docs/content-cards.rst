===================================
 Cards in Content (Embedded Links)
===================================

This document describes the appearance of *cards* in authored content.
A *card* is loosely modeled on `Twitter Cards
<https://dev.twitter.com/docs/cards>`_ and as such represents a
hyperlink to some other (possibly locally hosted) content. A card has
an independent identity of its own and thus functions as a
user-generated data *container*.

In the future, cards may be *modeled* content, capable of being stored
as user-generated data and being used within certain other embedding
contexts (such as notes). This document is written with that in mind,
but right now the **only** expression of cards is found within
authored content. Therefore, cards themselves cannot be the subject of
actions such as bookmarking, liking, favoriting or flagging.

Card Models
===========

Cards are defined to have the MIME type
``application/vnd.nextthought.nticard``. The minimal model of a card
has the following form:

.. code-block:: cpp

	// Notice these are not Dataserver objects (e.g., no OID)
	class Card {
		// The NTIID of the card itself.
		string ntiid;

		// The type property (a string) is a hint
		// about how the card is intended to be used/displayed.
		// Certain types may imply further constraints on other attributes.
		enum {
			summary,
		} type;

		// A plain text caption for the target of the card
		// of no more than 70 characters
		string title;

		// The hyperlink giving the target of the card.
		// This may be a relative URL path, an absolute URL,
		// or an NTIID URI.
		string href;

		// A plain text description of the target of the card
		// of no more than 200 characters; no formatting or paragraph
		// breaks.
		optional string description;

		// The Dublin Core creator value for the target of the card
		optional string creator;

		// A (usually relative) URL giving a thumbnail or preview
		// image (depending on the card type) for the target of the
		// card
		optional string image;
		optional int image_width;
		optional int image_height;

		// An NTIID for the actual target. If the target is hosted
		// content, this will be the same as the href. If the target
		// is external content, this may be derived. In either case,
		// it can be used as a containerId.
		optional string target_ntiid;
	}

The HTML for a card in authored content will have the following form
(notice that the ``href`` value *is not* the ``data`` attribute, to
keep the browser from doing things with it):

.. code-block:: html

	<object type="application/vnd.nextthought.nticard"
			class="nticard"
			data-ntiid="tag:card-ntiid"
			data-target_ntiid="tag:target-ntiid"
			data-type="summary"
			data-title="The Short Title"
			data-creator="Joe Smith"
			data-href="/path/to/resource.pdf">
		<!-- The data parameters are repeated -->
		<param name="ntiid" value="tag:card-ntiid" />
		<param name="target_ntiid" value="tag:target-ntiid" />
		<param name="type" value="summary" />
		<param name="title" value="The Short Title" />
		<param name="creator" value="Joe Smith" />
		<param name="href" value="/path/to/resource.pdf" />
		<!-- The content of the object is the description -->
		<span class="description">
			The description of the target.
		</span>
		<!-- Followed by the image tag used to represent the object -->
		<img src="/path/to/image.png" width="120" height="140" />
	</object>

Authoring
=========

In LaTeX, this is authored using the ``nticard`` environment. To
produce the above HTML, one would write:

.. code-block:: latex

	\begin{nticard}{/path/to/resource.pdf}<creator=Joe Smith>
		\label{testcard} % If the label is given, it is the part of NTIID
		\caption{The Short Title} % The caption becomes the title
		\includegraphics[width=120px,height=140]{/path/to/image.png}

		The description of the target.
	\end{nticard}

If the href you are linking to is an HTML page that implements Twitter
card support (coming soon) or the Facebook OpenGraph protocol, you can
use the ``auto=true`` optional argument. If the metadata is present in
the page, you can leave out the creator, image, and description: they
will all automatically be pulled from the page. This requires an
active Internet connection, and a non-authenticated page. For example:

.. code-block:: latex

	\begin{nticard}{http://www.newyorker.com/reporting/2013/01/07/130107fa_fact_green?currentPage=all}<auto=true>
	\end{nticard}

Likewise, a PDF can be used with ``auto`` to generate a thumbnail
based on the first page and extract the creator, subject (for
description) and title.

This is implemented with the following class:

.. autoclass:: nti.contentrendering.plastexpackages.ntilatexmacros.nticard
