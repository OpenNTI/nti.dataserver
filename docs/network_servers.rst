=================
 Network Serving
=================

This document discusses how network serving is accomplished.

Gunicorn
========

Gunicorn is used to handle HTTP serving. We require a specific worker to integrate with
Gunicorn.

.. automodule:: nti.appserver.nti_gunicorn
	:private-members:

Servers
=======

Our gunicorn integration relies on specific gevent-based servers
to handle websockets and other types of network traffic.

.. automodule:: nti.appserver.application_server
