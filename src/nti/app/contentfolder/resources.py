#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import to_external_download_oid_href
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link

from nti.app.contentfolder.utils import is_cf_io_href
from nti.app.contentfolder.utils import to_external_cf_io_href
from nti.app.contentfolder.utils import get_file_from_cf_io_url

logger = __import__('logging').getLogger(__name__)


def is_internal_file_link(link):
    return is_oid_external_link(link) or is_cf_io_href(link)


def get_file_from_external_link(link):
    if is_oid_external_link(link):
        return get_file_from_oid_external_link(link)
    elif is_cf_io_href(link):
        return get_file_from_cf_io_url(link)
    return None


def to_external_file_link(context, oid=False):
    if oid:
        return to_external_download_oid_href(context)
    return to_external_cf_io_href(context)
