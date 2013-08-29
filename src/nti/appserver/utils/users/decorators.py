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

from nti.appserver._util import link_belongs_to_user

from nti.dataserver.links import Link
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

LINKS = ext_interfaces.StandardExternalFields.LINKS

@component.adapter(nti_interfaces.IUser)
@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class PreferencesDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		the_links = mapping.setdefault( LINKS, [] )
		for name, method in (('set_preferences', 'POST'), ('get_preferences', 'GET'), ('delete_preferences', 'DELETE')):
			link = Link( context,
						 rel=name,
						 method=method,
						 elements=('@@' + name,))
			link_belongs_to_user( link, context )
			the_links.append( link )
