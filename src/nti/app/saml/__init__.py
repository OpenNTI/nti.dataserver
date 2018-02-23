#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from six.moves import urllib_parse

#: Assertion Consumer Service
ACS = u'acs'

#: Single Logout Service
SLS = u'sls'

#: Provider info view
GET_PROVIDER_INFO = u'GetProviderUserInfo'

#: Provider info view used for deletion
PROVIDER_INFO = u'ProviderUserInfo'

#: Provider name ids
IDP_NAME_IDS = u'NameIds'


def make_location(url, params=None):
    if not params or not url:
        return url or None
    url_parts = list(urllib_parse.urlparse(url))
    query = dict(urllib_parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib_parse.urlencode(query)
    # pylint: disable=too-many-function-args
    return urllib_parse.urlunparse(url_parts)
