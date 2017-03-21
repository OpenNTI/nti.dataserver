#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#: Content file mimetype
CONTENT_FILE_MIMETYPE = u'application/vnd.nextthought.contentfile'

#: Content image mimetype
CONTENT_IMAGE_MIMETYPE = u'application/vnd.nextthought.contentimage'

#: Content blob file mimetype
CONTENT_BLOB_FILE_MIMETYPE = u'application/vnd.nextthought.contentblobfile'

#: Content blob image mimetype
CONTENT_BLOB_IMAGE_MIMETYPE = u'application/vnd.nextthought.contentblobimage'

from nti.contentfile.model import transform_to_blob
