#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External decorators to provide access to the things exposed through this package.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from pyramid.threadlocal import get_current_request

from nti.appserver._util import link_belongs_to_user
from nti.appserver._view_utils import get_remote_user

from nti.dataserver.links import Link
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

@component.adapter(nti_interfaces.IUser)
@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class PreferencesDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		request = get_current_request()
		if request is not None:
			dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
			remote_user = get_remote_user(request, dataserver) if dataserver else None
			if remote_user != context:
				return

		the_links = mapping.setdefault(ext_interfaces.StandardExternalFields.LINKS, [])
		for name, method in (('set_preferences', 'POST'), ('get_preferences', 'GET'), ('delete_preferences', 'DELETE')):
			link = Link( context,
						 rel=name,
						 method=method,
						 elements=('@@' + name,))
			link_belongs_to_user( link, context )
			the_links.append( link )
