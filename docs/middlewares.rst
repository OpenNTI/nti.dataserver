========================
 Middlewares and Tweens
========================

This document describes the WSGI middlewares and Pyramid tweens shipped with the application
and how they should be installed. The middlewares must be manually
configured as follows; the tweens are installed as part of the application.

WSGI Middleware
===============

First come our configured WSGI middlewares.  The pipeline is setup in pserve.ini::

	[pipeline:dataserver_gunicorn]
	pipeline =
		 egg:nti.dataserver#ops_ping
		 egg:nti.dataserver#ops_identify
		 nti_cors
		 nti_cors_options
		 egg:Paste#gzip
		 paste_error
		 dataserver

Ping
----

.. automodule:: nti.appserver.wsgi_ping
	:members:
	:private-members:

Identify
--------


.. automodule:: nti.app.authentication.wsgi_identifier
	:members:
	:private-members:


CORS
----

Next comes support for for CORS. CORS needs to be outermost so that even 401 errors and
exceptions have the chance to get their responses wrapped::

	[filter:nti_cors]
	use = egg:nti.dataserver#cors

	[filter:nti_cors_options]
	use = egg:nti.dataserver#cors_options

.. automodule:: nti.wsgi.cors
	:members:
	:private-members:

PASTE
-----

Last of the WSGI middlewares are Paste :class:`~paste.gzipper.middleware` and
Paste :class:`~paste.exceptions.errormiddleware.ErrorMiddleware`.


Pyramid Tweens
==============

`Pyramid Tweens <https://docs.pylonsproject.org/projects/pyramid/en/latest/glossary.html#term-tween>`_
come next and are arranged between the wsgi middleware and pyramid's router.  They pyramid docs say it best:

  A bit of code that sits between the Pyramid router's main request
  handling function and the upstream WSGI component that uses Pyramid as
  its 'app'. The word "tween" is a contraction of "between". A tween may
  be used by Pyramid framework extensions, to provide, for example,
  Pyramid-specific view timing support, bookkeeping code that examines
  exceptions before they are returned to the upstream WSGI application,
  or a variety of other features. Tweens behave a bit like WSGI
  middleware but they have the benefit of running in a context in which
  they have access to the Pyramid application registry as well as the
  Pyramid rendering machinery.

Our tween stack is setup in :py:meth:`nti.appserver.application.createApplication`.

If you have `Pyramid Debug Toolbar <https://docs.pylonsproject.org/projects/pyramid_debugtoolbar/en/latest/>`_
enabled you can view the stack of configured tweens beneath Global/Tweens.

The current stack (as of Fall 2018) from top to bottom is::

  perfmetrics
  performance
  debugtoolbar
  exceptionview
  greenletrunner
  zodb
  transaction
  site
  securityinteraction

Perfmetrics
-----------

When a statsd uri is configured the perfmetrics tween is installed.  This tween pushes a perfmetrics statsd
client on to the statsd client stack.  When configured application code can use the `perfmetrics` module for pushing
code to statsd.

.. automodule:: perfmetrics
	:members:

Performance
-----------

.. automodule:: nti.appserver.tweens.performance
	:members:
	:private-members:

DebugToolbar
------------

If configured, `Pyramid Debug Toolbar <https://docs.pylonsproject.org/projects/pyramid_debugtoolbar/en/latest/>`_
installs this tween to faciliate request debugging.

ExceptionView
-------------

Pyramid's exception view tween comes next.

GreenletRunner
--------------

.. automodule:: nti.appserver.tweens.greenlet_runner_tween
	:members:
	:private-members:


ZODB Connection
---------------

.. automodule:: nti.appserver.tweens.zodb_connection_tween
	:members:
	:private-members:


Transaction
-----------

.. automodule:: nti.appserver.tweens.transaction_tween
	:members:
	:private-members:



Site
~~~~

.. automodule:: nti.appserver.tweens.zope_site_tween
	:members:
	:private-members:

Model
~~~~~

This tween is implemented using functions provided by the underlying dataserver.

.. automodule:: nti.dataserver.site


Zope Security Interaction
-------------------------

.. automodule:: nti.appserver.tweens.zope_security_interaction_tween
	:members:
	:private-members:
