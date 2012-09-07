#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Having to do with mime types.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver import interfaces
from zope import interface
from zope.mimetype.interfaces import IContentTypeAware

from nti.mimetype.mimetype import MIME_BASE
from nti.mimetype.mimetype import MIME_EXT_JSON
from nti.mimetype.mimetype import MIME_EXT_PLIST
from nti.mimetype.mimetype import MIME_BASE_PLIST
from nti.mimetype.mimetype import MIME_BASE_JSON

from nti.mimetype.mimetype import ModeledContentTypeAwareRegistryMetaclass

from nti.mimetype.mimetype import is_nti_mimetype
from nti.mimetype.mimetype import nti_mimetype_class
from nti.mimetype.mimetype import nti_mimetype_with_class
from nti.mimetype.mimetype import nti_mimetype_from_object

# XXX Now make all the interfaces previously
# declared implement the correct interface
# This is mostly an optimization, right?
def __setup_interfaces():

	for x in interfaces.__dict__.itervalues():
		if interface.interfaces.IInterface.providedBy( x ):
			if x.extends( interfaces.IModeledContent ) and not IContentTypeAware.providedBy( x ):
				name = x.__name__[1:] # strip the leading I
				x.mime_type = nti_mimetype_with_class( name )
				interface.alsoProvides( x, IContentTypeAware )

__setup_interfaces()
