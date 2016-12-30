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
	# content search
	moved(str("nti.contentsearch._content_utils"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch._discriminators"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch._indexmanager"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch._repoze_index"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch._whoosh_schemas"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch.content_types"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch.discriminators"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch.indexmanager"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch.repoze_adpater"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch.whoosh_schemas"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch.whoosh_searcher"), str("nti.contentsearch._deprecated"))
	moved(str("nti.contentsearch.whoosh_storage"), str("nti.contentsearch._deprecated"))
	
	# deprecated core/fragments pkgs
	moved(str("nti.dataserver.core"), str("nti.coremetadata"))
	moved(str("nti.dataserver.core.interfaces"), str("nti.coremetadata.interfaces"))
	moved(str("nti.dataserver_core"), str("nti.coremetadata"))
	moved(str("nti.dataserver_core.mixins"), str("nti.coremetadata.mixins"))
	moved(str("nti.dataserver_core.schema"), str("nti.coremetadata.schema"))
	moved(str("nti.dataserver_core.interfaces"), str("nti.coremetadata.interfaces"))
	
	moved(str("nti.dataserver.fragments"), str("nti.coremetadata"))
	moved(str("nti.dataserver.fragments.interfaces"), str("nti.coremetadata.interfaces"))
	moved(str("nti.dataserver_fragments"), str("nti.coremetadata"))
	moved(str("nti.dataserver_fragments.mixins"), str("nti.coremetadata.mixins"))
	moved(str("nti.dataserver_fragments.schema"), str("nti.coremetadata.schema"))
	moved(str("nti.dataserver_fragments.interfaces"), str("nti.coremetadata.interfaces"))

	# deleted session_consumer module
	moved(str("nti.dataserver.session_consumer"), str("nti.socketio.session_consumer"))
