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

from nti.app.contentfile.view_mixins import file_contraints

from nti.app.contentfile.view_mixins import transfer_data
from nti.app.contentfile.view_mixins import validate_sources
from nti.app.contentfile.view_mixins import get_content_files
from nti.app.contentfile.view_mixins import read_multipart_sources
from nti.app.contentfile.view_mixins import transfer_internal_content_data

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import to_external_oid_and_link
from nti.app.contentfile.view_mixins import to_external_download_oid_href
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link
