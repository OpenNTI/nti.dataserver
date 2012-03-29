#!/usr/bin/env python

# Note that we're not exporting anything by importing it.
# This helps reduce the chances of import cycles

# XXX Import side-effects.
# Loading this file monkey-patches sockets and ssl to work with gevent.
# This is needed for the openid handling in logon.py, but doing it here is a bit
# earlier and has a greater chance of working. This is also after
# we have loaded ZODB and doesn't seem to interfere with it. See gunicorn.py.
# NOTE: 1.0 of gevent seems to fix the threading issue that cause problems with ZODB.
# Try to confirm that
import logging
logger = logging.getLogger(__name__)

import gevent
import gevent.monkey
if getattr( gevent, 'version_info', (0,) )[0] >= 1:
	logger.info( "Monkey patching most libraries for gevent" )
	# omit thread, it's required for multiprocessing futures, used in contentrendering
	gevent.monkey.patch_all(thread=False)

	# However, locals we must also patch
	import gevent.local
	import threading
	threading.local = gevent.local.local
	_threading_local = __import__('_threading_local')
	_threading_local.local = gevent.local.local

	# depending on the order of imports, we may need to patch
	# things up manually
	import transaction
	if gevent.local.local not in transaction.ThreadTransactionManager.__bases__:
		class GeventTransactionManager(transaction.TransactionManager):
			pass
		manager = GeventTransactionManager()
		transaction.manager = manager
		transaction.get = transaction.__enter__ = manager.get
		transaction.begin = manager.begin
		transaction.commit = manager.commit
		transaction.abort = manager.abort
		transaction.__exit__ = manager.__exit__
		transaction.doom = manager.doom
		transaction.isDoomed = manager.isDoomed
		transaction.savepoint = manager.savepoint
		transaction.attempts = manager.attempts

	import zope.component
	import zope.component.hooks
	if gevent.local.local not in type(zope.component.hooks.siteinfo).__bases__:
		# TODO: Is there a better way to do this?
		# This code is copied from zope.component 3.12
		class SiteInfo(threading.local):
			site = None
			sm = zope.component.getGlobalSiteManager()

			def adapter_hook(self):
				adapter_hook = self.sm.adapters.adapter_hook
				self.adapter_hook = adapter_hook
				return adapter_hook

			adapter_hook = zope.component.hooks.read_property(adapter_hook)

		zope.component.hooks.siteinfo = SiteInfo()

else:
	logger.info( "Monkey patching minimum libraries for gevent" )
	gevent.monkey.patch_socket(); gevent.monkey.patch_ssl()
