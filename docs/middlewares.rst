========================
 Middlewares and Tweens
========================

This document describes the WSGI middlewares and Pyramid tweens shipped with the application
and how they should be installed. The middlewares must be manually
configured as follows; the tweens are installed as part of the application::

	[pipeline:dataserver_gunicorn]
	pipeline =
		 nti_cors
		 nti_cors_options
		 paste_error
		 egg:nti.dataserver#ops_ping
		 dataserver

Ping
====

Innermost (just before the application proper) is a WSGI "ping" handler. This is provided for very cheap, basic
monitoring.

.. automodule:: nti.appserver.wsgi_ping
	:members:
	:private-members:


CORS
====

Outermost of everything (and around Paste's :class:`~paste.exceptions.errormiddleware.ErrorMiddleware`) is support for CORS::

	# CORS needs to be outermost so that even 401 errors ond
	# exceptions have the chance to get their responses wrapped
	[filter:nti_cors]
	use = egg:nti.dataserver#cors

	[filter:nti_cors_options]
	use = egg:nti.dataserver#cors_options

.. automodule:: nti.wsgi.cors
	:members:
	:private-members:


Site
====

The Zope Component Architecture depends on having access to a "site."

Tween
-----

.. automodule:: nti.appserver.tweens.zope_site_tween
	:members:
	:private-members:

Model
-----

This tween is implemented using functions provided by the underlying dataserver.

.. automodule:: nti.dataserver.site
