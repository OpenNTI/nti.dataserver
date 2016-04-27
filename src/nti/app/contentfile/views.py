#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from collections import Mapping

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfolder import MessageFactory as _

from nti.app.externalization.internalization import read_body_as_external_object

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.maps import CaseInsensitiveDict

from nti.contentfile.interfaces import IContentBaseFile

from nti.dataserver import authorization as nauth

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.ntiids.ntiids import find_object_with_ntiid

ITEMS = StandardExternalFields.ITEMS

expanded_expected_types = six.string_types + (Mapping,)

@view_config(context=IContentBaseFile)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ContentFileGetView(AbstractAuthenticatedView):

	def __call__(self):
		result = to_external_object(self.request.context)
		result.lastModified = self.request.context.lastModified
		return result

@view_config(context=IContentBaseFile)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name='associations',
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ContentFileAssociationsView(AbstractAuthenticatedView):

	def __call__(self):
		result = LocatedExternalDict()
		result[ITEMS] = items = []
		if self.context.has_associations():
			items.extend(self.context.associations())
		result['ItemCount'] = result['Total'] = len(items)
		return result

@view_config(context=IContentBaseFile)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name='associate',
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class ContentFileAssociateView(AbstractAuthenticatedView,
							   ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = {'ntiid': data}
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def __call__(self):
		values = self.readInput()
		ntiid = values.get('ntiid') or values.get('oid') or values.get('target')
		if not ntiid:
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))
		target = find_object_with_ntiid(ntiid)
		if target is None:
			raise hexc.HTTPUnprocessableEntity(_("Cannot find target object."))
		if target is not self.context:
			self.context.add_association(target)
		return hexc.HTTPNoContent()
