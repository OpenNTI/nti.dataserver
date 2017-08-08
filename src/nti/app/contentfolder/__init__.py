#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

#: Content folder internal object
CFIO = 'cf.io'

#: Folder for storing assets
ASSETS_FOLDER = 'assets'

#: Folder for storing images
IMAGES_FOLDER = 'Images'

#: Folder for storing documents
DOCUMENTS_FOLDER = 'Documents'

#: Default content type
DEFAULT_CONTENT_TYPE = 'application/octet-stream'
