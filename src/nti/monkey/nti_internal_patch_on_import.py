#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.common.deprecated import moved

def patch():
	# deprecated core/fragments pkgs
	moved("nti.dataserver.core", "nti.dataserver_core")
	moved("nti.dataserver.core.interfaces", "nti.dataserver_core.interfaces")
	moved("nti.dataserver.fragments", "nti.dataserver_fragments")
	moved("nti.dataserver.fragments.interfaces", "nti.dataserver_fragments.interfaces")

	# deleted session_consumer module
	moved("nti.dataserver.session_consumer", "nti.socketio.session_consumer")
