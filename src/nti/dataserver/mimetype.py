#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Having to do with mime types.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# XXX Now make all the interfaces previously
# declared implement the correct interface
# This is mostly an optimization, right?
def __setup_interfaces():
	from zope import interface
	from zope.mimetype.interfaces import IContentTypeAware
	from nti.dataserver import interfaces
	from nti.mimetype.mimetype import nti_mimetype_with_class

	for x in interfaces.__dict__.itervalues():
		if interface.interfaces.IInterface.providedBy( x ):
			if x.extends( interfaces.IModeledContent ) and not IContentTypeAware.providedBy( x ):
				name = x.__name__[1:] # strip the leading I
				x.mime_type = nti_mimetype_with_class( name )
				interface.alsoProvides( x, IContentTypeAware )

__setup_interfaces()
del __setup_interfaces

import nti.deprecated
nti.deprecated.moved('nti.mimetype.mimetype')
