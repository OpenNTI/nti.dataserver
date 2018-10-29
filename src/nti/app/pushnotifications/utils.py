#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from six.moves import urllib_parse

from itsdangerous import JSONWebSignatureSerializer as SignatureSerializer

from zope import component

from zope.intid.interfaces import IIntIds

from nti.base._compat import text_

from nti.dataserver.users.users import User

logger = __import__('logging').getLogger(__name__)


def _signature(username, secret_key):
    s = SignatureSerializer(secret_key)
    signature = s.dumps({'username': username})
    return signature


def validate_signature(user, signature, secret_key=None):
    """
    Validate the given signature for the given user, raising
    an exception if the data does not match.
    """
    username = user.username.lower()
    intids = component.getUtility(IIntIds)

    if not secret_key:
        uid = intids.getId(user)
        secret_key = text_(uid)

    s = SignatureSerializer(secret_key)
    data = s.loads(signature)
    if data['username'] != username:
        raise ValueError("Invalid token user")
    return data


def generate_signature(user, secret_key=None):
    """
    Generate a key based on the intid of the user.
    """
    user = User.get_user(user)
    if user is None:
        raise ValueError("User not found")
    username = user.username.lower()

    intids = component.getUtility(IIntIds)
    if not secret_key:
        uid = intids.getId(user)
        secret_key = text_(uid)
    result = _signature(username, secret_key)
    return result


def generate_unsubscribe_url(user, request=None, host_url=None, secret_key=None):
    try:
        ds2 = request.path_info_peek()
    except AttributeError:
        ds2 = "dataserver2"

    try:
        host_url = request.host_url if not host_url else None
    except AttributeError:
        host_url = None

    signature = generate_signature(user=user, secret_key=secret_key)
    params = urllib_parse.urlencode({'username': user.username.lower(),
                                     'signature': signature})

    href = '/%s/%s?%s' % (ds2, '@@unsubscribe_digest_email_with_token', params)
    result = urllib_parse.urljoin(host_url, href) if host_url else href
    return result
