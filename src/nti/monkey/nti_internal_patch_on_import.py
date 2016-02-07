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
	moved(str("nti.dataserver.core"), str("nti.dataserver_core"))
	moved(str("nti.dataserver.core.interfaces"), str("nti.dataserver_core.interfaces"))
	
	moved(str("nti.dataserver.fragments"), str("nti.dataserver_fragments"))
	moved(str("nti.dataserver.fragments.interfaces"), str("nti.dataserver_fragments.interfaces"))

	# deleted session_consumer module
	moved(str("nti.dataserver.session_consumer"), str("nti.socketio.session_consumer"))
	
	# content search invalid package
	moved(str("nti.contentsearch._repoze_adpater"), str("nti.contentsearch._repoze_adapter"))
