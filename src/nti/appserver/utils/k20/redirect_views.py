#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import urllib

from urlparse import urlparse

from requests.structures import CaseInsensitiveDict

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver import authorization as nauth

from nti.dataserver.users.users import User


from nti.ntiids.oids import to_external_ntiid_oid

K20_VIEW_NAME = 'k20_link'
K20_LINK_PARAM_NAME = 'href'
K20_IDENTIFIER_NAME = 'token'


def _get_user_token(user):
    return to_external_ntiid_oid(user, mask_creator=True)


@view_config(route_name='objects.generic.traversal',
             name=K20_VIEW_NAME,
             request_method='GET',
             permission=nauth.ACT_READ)
class K20Link(AbstractAuthenticatedView):
    """
    Given a link, returns the link with an appended user identifying parameter.
    """

    def __call__(self):
        request = self.request
        params = CaseInsensitiveDict(request.params)
        url = params.get(K20_LINK_PARAM_NAME)

        username = self.remoteUser
        user = User.get_user(username)
        if user is None or url is None:
            return hexc.HTTPBadRequest("User or link invalid.")

        user_token = _get_user_token(user)
        params = urllib.urlencode({K20_IDENTIFIER_NAME: user_token})
        if urlparse(url)[4]:
            new_link = url + '&' + params
        else:
            new_link = url + '?' + params
        return hexc.HTTPFound(location=new_link)
