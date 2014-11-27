#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid

from zope import component
from zope.mimetype.interfaces import IContentTypeAware

from ZODB.POSException import POSError

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.externalization.interfaces import LocatedExternalDict

@view_config(route_name='objects.generic.traversal',
			 name='unregister_missing_objects',
			 renderer='rest',
			 request_method='POST',
			 context=IDataserverFolder,
			 permission=nauth.ACT_MODERATE)
class UnregisterMissingObjectsView(AbstractAuthenticatedView, 
						 		   ModeledContentUploadRequestUtilsMixin):
	
	def __call__(self):
		total = 0
		result = LocatedExternalDict()
		broken = result['Broken'] = {}
		missing = result['Missing'] = []
		intids = component.getUtility(zope.intid.IIntIds)
		for uid in intids:
			obj = None
			total += 1
			try:
				obj = intids.getObject(uid)
				if obj is not None and hasattr(obj, '_p_activate'):
					obj._p_activate()
				else:
					# load to validate
					getattr(obj, "creator", None)
					IDeletedObjectPlaceholder.providedBy(obj)
					IContentTypeAware(obj, None)
			except KeyError:
				missing.append(uid)
				logger.info("Unregistering missing %s", uid)
				intids.forceUnregister(uid, notify=False, removeAttribute=False)
			except POSError:
				broken[uid] = str(type(obj))
				logger.info("Unregistering broken object %s,%s", uid, type(obj))
				intids.forceUnregister(uid, notify=False, removeAttribute=False)
		result['Total'] = total
		result['TotalBroken'] = len(broken)
		result['TotalMissing'] = len(missing)
		logger.info("unregister missing objects %s", result)
		return result
