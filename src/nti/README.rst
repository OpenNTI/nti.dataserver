========
 README
========

Packages
========

A note on package organization:

`nti.appserver`
	Essentially deprecated, but still the master package for
	application code.

`nti.app.XXX`
	Core functionality of the application. These may add application
	functionality for a layer beneath them (e.g.,
	`nti.app.externalization` and `nti.externalization`). These will
	typically always be loaded into the application and used in all
	sites.

`nti.app.products.XXX`
	Add-on products for the application. They may not be loaded in all
	configurations, and they may not be configured in all sites. Often
	they will tie together many different lower layers to present a
	group of functionality.

`nti.contenttypes.XXX`
	Low-level packages for specific types of content the server can host.
