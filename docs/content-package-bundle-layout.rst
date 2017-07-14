===================================
On-Disk ContentPackageBundle Layout
===================================

At the start of Nextthought, books mapped directly to ContentPackages.  Conceptually
all ContentPackages were thought of as books and all ContentPackages showed
up in the UI and could be browsed as if they were books.  With the introduction of courses
(specifically content based courses) it became no longer desired to have all
ContentPackages show up as "books".  Those ContentPackages whose TOC
specified isCourse=true were presented as Courses, all other ContentPackages continued to
be presented as books.  As courses evolved and moved into the dataserver course's
could theoretically reference multiple ContentPackages and those ContentPackages didn’t
necessarily need to specify isCourse=true.  The presented books then became the
set of ContentPackages not referenced by one of your CourseInstances' ContentPackageBundles.

At the time of writing this (October 2015), the hueristics that the UIs use to determine
what should be categorized as a book have become both complicated to
understand and expensive to implement.  To simplify this process, moving forward,
books in the UI will map directly to ContentPackageBundle objects.

This document describes the on-disk layout of ContentPackageBundle (book) objects.

Concepts
========

Objects called :dfn:`content bundles` represent a collection of one
or more content packages, presented as a viewable unit in the user interface.

.. warning:: At this writing, there is no auxillary navigation structure associated
			 with a ContentPackageBundle. UI's are currently treating the first
			 ContentPackage in the list as the provider of the TOC that defines the book
			 navigation.  This makes the usefulness of ContentPackageBundle objects
			 that reference multiple ContentPackages questionable.


Synchronization
---------------

ContentPackageBundle objects are part of the NTI Database. How do they get there in
the first place, and how are they maintained if changes need to occur?

One way would be to manage this through-the-web (with a Web UI).
Although this is certainly feasible to implement, it makes it hard to
manage an evaluation/testing process.

Instead, our process relies on reading the information from files and
directories on disk and updating the objects in the database when
specifically requested by an administrator. The remainder of this
document will describe these files and directories.

.. tip:: The files and directories containing this information are
		 ideally suited to being stored in version control.

.. note:: For synchronization to work correctly, file and directory
		  modification dates must be reliable.

Directory Structure
===================

As mentioned, all content bundles are contained within a single site. This is
accomplished on-disk by having the files and directories that make up
a bundle exist within the on-disk library for that site. A typical
layout to define sites might look like this::

	DataserverGlobalLibrary/
	    ... # globally-visible content lives here
	    sites/ # container for sites
	        platform.ou.edu/ # each directory is a site directory
	            ... # content visible to this site and children live here
	        ou-alpha.nextthought.com/
	        janux.ou.edu/

.. note:: Sites are arranged in a hierarchy (parent-child
		  relationship). Objects in a parent are visible when using
		  the child site, and objects in a child site can override the
		  same object in the parent site (by matching its name). This
		  can be convenient for testing and evaluation. In this
		  example, ``platform.ou.edu`` is a base site, and both
		  ``ou-alpha.nextthought.com`` and ``janux.ou.edu`` extend it.

Inside the global library (``DataserverGlobalLibrary``) are content
packages, and the special directory ``sites``. Inside the ``sites``
directory are directories named for each site (*site directories*).
Inside each site directory exist the content packages visible to that
site.

There are a few special directories that can exist inside a site
directory::

	platform.ou.edu/
	    ... # content
	    ContentPackageBundles/ # content bundles definitions
	    Courses/ # a site course directory, not relevant here

The one we are concerned with is called ``ContentPackageBundles``. This is the
site's bundle directory, or simply the bundles directory. All the
ContentPackageBundles available within the site (and children sites) are
defined by the structure inside this directory.

ContentPackageBundles Directory
-------------------------------

Inside the bundles directory are folders that define individual ContentPackageBundle
objects.

.. note:: Unlike courses defined in the ``Courses`` folder, bundles must currently
		  be defined as immediate children of the bundles directory.  That is, no
		  additional directory structure is allowed for organization.

ContentPackageBundle Directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The directories that actually define a content bundle are called
:dfn:`bundle directories`. These are direct child directories of the bundles directory
and they are identified by the presence of a file named ``bundle_meta_info.json``.


Bundle Directory Contents
=========================

With all the preliminaries about structuring the site and bundles
directories out of the way, we can now address the contents of a
bundle directory, or what actually defines a bundle.

This section will describe each file that may have meaning within a
bundle directory.

.. _bundle_meta_info.json:

``bundle_meta_info.json`` (required)
------------------------------------

This is the file that actually defines a bundle by relating
it to the content that it uses. A directory containing this file is a
bundle. This file is a standard bundle file as defined by
:mod:`nti.contentlibrary.bundle`::

	{
		"NTIID": "tag:nextthought.com,2011-10:USSC-Bundle-LawBundle"
	    "ContentPackages": ["tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california."],
	    "title": "A Title",
        "RestrictedAccess": false
    }

.. note:: ``RestrictedAccess`` defines whether this bundle should be visible
          to admins/editors or everyone by default. It does not currently imply
          anything about permissions to the underlying packages of the bundle.

.. note:: Unlike course bundles, bundles beneath ``ContentPackageBundles`` are required to specify an
		  NTIID.

.. warning:: Recall that current UIs can only fully handle a single
			 content package being defined here.


``bundle_dc_metadata.xml`` (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If present, this file is a standard Dublin Core XML file containing
additional metadata about the content bundle.

``presentation-assets/`` (optional)
-----------------------------------

If present, this directory is a standard presentation assets directory
containing convention-based images for different platforms. This will
be returned as the ``PlatformPresentationResources`` value on the
bundle.

