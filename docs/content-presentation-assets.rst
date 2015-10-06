===================
Presentation Assets
===================

This document describes NTI's approach for handling UI specific presentation assets across multiple UI clients, as well as enumerating the current set of presentation specific assets in use. These presentation specific assets are things like library thumbnails, course background images, book covers images, etc.  These types of assets are specific to a given iteration of the UI on a given device (iPad, webapp, mobile, etc).  NextThought currently has two primary UIs, native iPad app and webapp, that require potentially different assets for a given content package.

Current Approach
================

The current approach uses references in the toc (among other places) to point to assets included in the content bundle.  This approach has two problems.  Primarily, the current system does not scale well beyond a single UI client or iteration of the UI.  While this was sufficient given a focus on only the webapp, the addition of a native iPad application whose UI diverges from that of the webapp has brought forth the need for presentation context specific assets. Secondly, the current approach lacks a necessary separation between the model of the content and UI of how it is presented in any given context.  Presentation specific information should not be encoded in the content model as it is now.

.. note::
   Jason should we include a link to your resource matrix here?

Consider a concrete example; the background image the webapp currently displays when in a particular course.  The asset shipped in the content package is specific to the current webapp's UI.  While the iPad may have a similar UI design, it requires a background image that is a different aspect ratio, and it also needs a couple different sizes to support retina/non-retina devices.  The handling of other assets (icons, thumbnails, etc) have similar problems with the way they are currently handled. The list of courses displayed on an iPhone may be different than the list on the webapp with both UIs requiring different sized assets.

Client Specific Presentation Assets
===================================

Given the shortcomings discussed above, it seems prudent to start thinking about these assets as being auxiliary to the content rather than a part of how the content is modeled.  Each client would have a set of well-known paths that it looks for the various presentation related assets in.  For example we could use the following structure for the background image example.

| presentation-assets/webapp/v1/background.png
| presentation-assets/iPad/v1/background.png
| presentation-assets/iPad/v1/background@2x.png

These are well-known paths.  Each client would be responsible for knowing what it needed and where to look for it given it's current context. This eliminates the meta-data defining where to find these assets.  This moves the presentation related information out of the models (think MVC) and provides flexibility for numerous clients and UIs.

The example above lists a set of relative URLs.  Presentation assets needed for a given content package are relative to that content package.  However, a course, at least going forward, won't have just one content package associated with it.  A given course may be made up of content from any number of traditional nti content packages.  Because of that fact, presentation assets for a course will have to be relative to some asset package created for that course.  This means any course generation pipeline would need to include a step where the asset packages are generated with proper assets for all known clients.

These asset locations contain information not only about the client but also a version.  This allows for backwards compatibility across *major* UI changes that may require new or changed assets on a given platform.

Should the same presentation asset be shared between two devices/version we can use a shared location and symlinks to prevent asset duplication.  For example if v1 and v2 of iPad both need a background.png that is the same we could create the following structure:

| presentation-assets/iPad/shared/background.png
| presentation-assets/iPad/v1/background.png -> presentation-assets/iPad/shared/background.png
| presentation-assets/iPad/v2/background.png -> presentation-assets/iPad/shared/background.png

A similar structure could be used if we need to share presentation assets between the iPad and webapp.

Considerations
==============

We must be very careful that the presentation assets used by clients are well defined and "static" for a given presentation style so that minor changes to UI don't require recreating all asset packages for every content package/course on the platform.  This also means that clients will need to degrade gracefully when they encounter missing/unexpected assets.


Known Presentation Assets
=========================

This section outlines the well known set of presentation assets currently in use by client and UI version.

iPad v1
-------

Assets found beneath presentation-assets/iPad/v1/

+------------------------------------+------------+----------------------------------------------------------------+
|Name                                |Size        |Description                                                     |
+====================================+============+================================================================+
|``contentpackage-cover-256x156.png``|256 x 156 px| the cover image for this particular content package.  This     |
|                                    |            | asset is presented above the navigation table to the left of   |
|                                    |            | the content area when browsing a content package as a book.    |
+------------------------------------+------------+----------------------------------------------------------------+
|``contentpackage-thumb-60x80.png``  | 60 x 80 px | thumbnail for this content package.  This is the thumbnail     |
|                                    |            | that shows up on the books view of the library.                |
+------------------------------------+------------+----------------------------------------------------------------+
|``background.png``                  |            | background image shown when in the context of this course or   |
|                                    |            | catalog entry.                                                 |
+------------------------------------+------------+----------------------------------------------------------------+
|``instructor-photos/{}.png``        |            | The avatar to use for the ith instructor listed in the catalog |
|e.g. ``instructor-photos/01.png``   |            | entry                                                          |
+------------------------------------+------------+----------------------------------------------------------------+


WebApp
------

Assets found beneath presentation-assets/webapp/v1/

+------------------------------------+------------+----------------------------------------------------------------+
|Name                                |Size        |Description                                                     |
+====================================+============+================================================================+
|``contentpackage-cover-232x170.png``|232 x 170 px| the cover image for this particular content package. Used in   |
|                                    |            | library.                                                       |
+------------------------------------+------------+----------------------------------------------------------------+
|``contentpackage-thumb-60x60.png``  | 60 x 60 px | thumbnail for this content package. Shown in the various small |
|                                    |            | squares peppered throught the app (note context, nav bar)      |
+------------------------------------+------------+----------------------------------------------------------------+
|``background.png``                  |            | background image shown when in the context of this course or   |
|                                    |            | catalog entry.                                                 |
+------------------------------------+------------+----------------------------------------------------------------+
|``vendoroverrideicon.png``          |  n x 70 px | If provided allows for a custom vendor icon to be shown in the |
|                                    |            | top left corner of the application when in this course context |
+------------------------------------+------------+----------------------------------------------------------------+


Legacy Presentation Assets Still In Use
=======================================

This table defines the legacy assets in use by clients

+-------------------------------------------------+--------------------------------------------+----------------------------------------------+
|Key Path                                         |Webapp                                      |iPad                                          |
+=================================================+============================================+==============================================+
|``ContentPackage/toc/icon``                      |Not Used                                    |Not Used                                      |
+-------------------------------------------------+--------------------------------------------+----------------------------------------------+
|``ContentPackage/toc/background``                |Course Background                           |Course background                             |
+-------------------------------------------------+--------------------------------------------+----------------------------------------------+
|``Purchasable/Icon``                             |Purchase Window, Purchase Prompts, Library  |Not Used                                      |
+-------------------------------------------------+--------------------------------------------+----------------------------------------------+
|``Purchasable/Thumbnail``                        |Not Used                                    |Not Used                                      |
+-------------------------------------------------+--------------------------------------------+----------------------------------------------+
|``CourseCatalogEntry/LegacyPurchasableIcon``     |Not Used                                    |Home screen Catalog tab                       |
+-------------------------------------------------+--------------------------------------------+----------------------------------------------+
|``CourseCatalogEntry/LegacyPurchasableThumbnail``|Not Used                                    |Home screen Courses tab, Top of course outline|
+-------------------------------------------------+--------------------------------------------+----------------------------------------------+
