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

from ZODB.POSException import POSError

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict

@view_config(route_name='objects.generic.traversal',
			 name='unregister_missing',
			 renderer='rest',
			 request_method='POST',
			 context=IDataserverFolder,
			 permission=nauth.ACT_MODERATE)
class UnregisterMissingView(AbstractAuthenticatedView, 
						 	ModeledContentUploadRequestUtilsMixin):
	
	def __call__(self):
		result = LocatedExternalDict()
		broken = result['Broken'] = {}
		missing = result['Missing'] = []
		intids = component.getUtility(zope.intid.IIntIds)
		for uid in intids:
			try:
				obj = intids.queryObject(uid)
				if obj is None:
					missing.append(uid)
			except (POSError, TypeError):
				broken[uid] = str(type(obj))
		result['TotalBroken'] = len(broken)
		result['TotalMissing'] = len(missing)
		return result
