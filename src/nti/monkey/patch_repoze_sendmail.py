#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import pkg_resources

dist = pkg_resources.get_distribution('repoze.sendmai')
if not dist.version or dist.version < '4.1':
	import repoze.sendmail.delivery
	from repoze.sendmail.delivery import DirectMailDelivery
	from repoze.sendmail.delivery import QueuedMailDelivery

	class _DirectMailDelivery(DirectMailDelivery):
		def __init__(self, mailer, *args, **kwargs):
			DirectMailDelivery.__init__(self, mailer)
	repoze.sendmail.delivery.DirectMailDelivery = _DirectMailDelivery
	
	class _QueuedMailDelivery(QueuedMailDelivery):
		def __init__(self, queuePath, *args, **kwargs):
			QueuedMailDelivery.__init__(self, queuePath)
	repoze.sendmail.delivery.QueuedMailDelivery = _QueuedMailDelivery

def patch():
	pass

