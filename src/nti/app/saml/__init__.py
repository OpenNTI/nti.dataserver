#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

import urllib
import urlparse

#: Assertion Consumer Service
ACS = 'acs'

#: Single Logout Service
SLS = 'sls'

#: Provider info view
GET_PROVIDER_INFO = 'GetProviderUserInfo'

#: Provider info view used for deletion
PROVIDER_INFO = 'ProviderUserInfo'

#: Provider name ids
IDP_NAME_IDS = 'NameIds'

def make_location(url, params=None):
    if not params:
        return url

    if not url:
        return None

    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.urlencode(query)

    return urlparse.urlunparse(url_parts)
