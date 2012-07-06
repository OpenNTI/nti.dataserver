====================================================
 Resolving Content and Content-Specific Preferences
====================================================

This document describes how content is resolved from the dataserver (see :doc:`content-in-cdn`).

Basics
======

Content is resolved from the dataserver based on its NTIID, using the
standard NTIID/Object URLs, e.g.,
``/dataserver2/Objects/tag:nextthought.com,2011-10:Provider-HTML-Content``.
In the simplest case, the result of this GET request will be an HTTP
redirect to the HTML content.

PageInfo Objects
----------------

If the HTTP ``Accept`` header is provided and specifies a dataserver
datatype (i.e., not HTML, but JSON), then an ``PageInfo`` object will
be returned. This object defines not just how to get the content
(through the 'content' link) but how to access related information
(through the other links) and includes user preferences.

.. note:: This document assumes the datastructures defined in :doc:`dataserver-contenttypes`.

.. code-block:: cpp

	// The relationship types returned for links from a PageInfo.
	enum {
		UserGeneratedData,
		RecursiveUserGeneratedData,
		Stream,
		RecursiveStream,
		UserGeneratedDataAndRecursiveStream,
		content, // The HTML content
	} PageRelationships;

	// Data that functions as a user preference
	// for the page.
	// Preferences are inherited from parent pages in the NTIID
	// tree; to set a preference to apply everywhere, use the Root NTIID
	abstract struct PagePreference {
		readonly enum {
			// not set by user, comes from somewhere else
			// for this node
			default,
			// specifically set by user for this node
			set,
			// inherited from 'higher' in the tree; that
			// node may be in either of the other states
			inherited,
		} State;

		// The NTIID that defined the value for this preference.
		// Most useful when the State is inherited or default.
		// If the State is 'set' it will match the PageInfo's ID
		readonly ntiid Provenance;
	}

	// Stores the default value for the 'sharedWith' field
	// of new UGD created within this page.
	struct SharingPagePreference {
		// The usernames that will be added to 'sharedWith'
		string sharedWith[];
	}

	// The data filters to apply when viewing this page.
	struct DataFilterPagePreference {
		// TODO: Undefined
	}

	struct PageInfo : Object {
		optional readonly Question AssessmentItems[];
		optional SharingPagePreference sharingPreference;
		optional DataFilterPagePreference dataFilterPreference;
	}


Editing Preferences
-------------------


To edit the preferences for a page of content (and its descendents
that have not overridden the preferences), follow the usual rules to
update a single field of an object and POST to the field's URL, e.g.,
``/dataserver2/Objects/tag:nextthought.com,2011-10:Provider-HTML-Contnet/++fields++sharingPreference``
