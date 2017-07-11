#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import math
import time
import hashlib
from urllib import urlencode
from urlparse import urljoin
from datetime import datetime

import isodate

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.dottedname import resolve as dottedname

from zope.i18n import translate

from zope.intid.interfaces import IIntIds

from zope.security.interfaces import IPrincipal

from itsdangerous import JSONWebSignatureSerializer as SignatureSerializer

from nti.app.users import MessageFactory as _

from nti.app.users import VERIFY_USER_EMAIL_VIEW

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.base._compat import text_

from nti.dataserver.interfaces import IUser

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IEmailAddressable

from nti.externalization.externalization import to_external_object

from nti.mailer.interfaces import ITemplatedMailer

_EMAIL_VERIFICATION_TIME_KEY = 'nti.app.users._EMAIL_VERIFICATION_TIME_KEY'
_EMAIL_VERIFICATION_COUNT_KEY = 'nti.app.users._EMAIL_VERIFICATION_COUNT_KEY'


def get_user(user):
    return user if IUser.providedBy(user) else User.get_user(str(user or ''))


def _token(signature):
    return int(hashlib.sha1(signature).hexdigest(), 16) % (10 ** 8)


def _signature_and_token(username, email, secret_key):
    s = SignatureSerializer(secret_key)
    signature = s.dumps({'email': email, 'username': username})
    token = _token(signature)
    return signature, token


def generate_mail_verification_pair(user, email=None, secret_key=None):
    __traceback_info__ = user, email
    user = get_user(user)
    if user is None:
        raise ValueError("User not found")
    username = user.username.lower()

    intids = component.getUtility(IIntIds)
    profile = IUserProfile(user, None)
    email = email or getattr(profile, 'email', None)
    if not email:
        raise ValueError("User does not have an mail")
    email = email.lower()

    if not secret_key:
        uid = intids.getId(user)
        secret_key = text_(uid)

    result = _signature_and_token(username, email, secret_key)
    return result


def get_verification_signature_data(user, signature, params=None,
                                    email=None, secret_key=None):
    __traceback_info__ = user, email
    user = get_user(user)
    if user is None:
        raise ValueError("User not found")
    username = user.username.lower()

    intids = component.getUtility(IIntIds)
    profile = IUserProfile(user)
    email = email or getattr(profile, 'email', None)
    if not email:
        raise ValueError("User does not have an email")
    email = email.lower()

    if not secret_key:
        uid = intids.getId(user)
        secret_key = text_(uid)

    s = SignatureSerializer(secret_key)
    data = s.loads(signature)

    if data['username'] != username:
        raise ValueError("Invalid token user")

    if data['email'] != email:
        raise ValueError("Invalid token email")
    return data


def generate_verification_email_url(user, request=None, host_url=None,
                                    email=None, secret_key=None):
    try:
        ds2 = request.path_info_peek() if request else "/dataserver2"
    except AttributeError:
        ds2 = "/dataserver2"

    try:
        host_url = request.host_url if not host_url else None
    except AttributeError:
        host_url = None

    signature, token = generate_mail_verification_pair(user=user,
                                                       email=email,
                                                       secret_key=secret_key)
    params = urlencode({'username': user.username.lower(),
                        'signature': signature})

    href = '%s/%s?%s' % (ds2, '@@' + VERIFY_USER_EMAIL_VIEW, params)
    result = urljoin(host_url, href) if host_url else href
    return result, token


def get_email_verification_time(user):
    annotes = IAnnotations(user)
    result = annotes.get(_EMAIL_VERIFICATION_TIME_KEY)
    return result


def get_email_verification_count(user):
    annotes = IAnnotations(user)
    result = annotes.get(_EMAIL_VERIFICATION_COUNT_KEY)
    return result or 0


def set_email_verification_time(user, now=None):
    now = time.time() if now is None else math.fabs(now)
    annotes = IAnnotations(user)
    annotes[_EMAIL_VERIFICATION_TIME_KEY] = now


def set_email_verification_count(user, count=None):
    count = 0 if count is None else int(math.fabs(count))
    annotes = IAnnotations(user)
    annotes[_EMAIL_VERIFICATION_COUNT_KEY] = count


def incr_email_verification_count(user):
    count = get_email_verification_count(user)
    set_email_verification_count(user, count + 1)


def _get_package(policy, template='email_verification_email'):
    base_package = 'nti.app.users'
    package = getattr(policy, 'PACKAGE', None)
    if not package:
        package = base_package
    else:
        package = dottedname.resolve(package)
        path = os.path.join(os.path.dirname(package.__file__), 'templates')
        if not os.path.exists(os.path.join(path, template + ".pt")):
            package = base_package
    return package


def send_email_verification(user, profile, email, request=None, check=True):
    if not request or not email:
        logger.warn("Not sending email to %s because of no email or request",
                    user)
        return

    username = user.username
    policy = component.getUtility(ISitePolicyUserEventListener)

    if check:
        assert getattr(IPrincipal(profile, None), 'id', None) == user.username
        assert getattr(IEmailAddressable(profile, None), 'email', None) == email

    user_ext = to_external_object(user)
    informal_username = user_ext.get('NonI18NFirstName', profile.realname)
    informal_username = informal_username or username

    site_alias = getattr(policy, 'COM_ALIAS', '')
    support_email = getattr(policy, 'SUPPORT_EMAIL', 'support@nextthought.com')
    href, token = generate_verification_email_url(user, request=request)

    args = {'user': user,
            'href': href,
            'token': token,
            'profile': profile,
            'request': request,
            'brand': policy.BRAND,
            'site_alias': site_alias,
            'support_email': support_email,
            'informal_username': informal_username,
            'today': isodate.date_isoformat(datetime.now())}

    template = 'email_verification_email'
    package = _get_package(policy, template=template)

    logger.info("Sending email verification to %s", user)

    mailer = component.getUtility(ITemplatedMailer)
    mailer.queue_simple_html_text_email(
        template,
        subject=translate(_("Email Confirmation")),
        recipients=[profile],
        template_args=args,
        request=request,
        package=package)

    # record time
    set_email_verification_time(user)
    incr_email_verification_count(user)
    return True


def safe_send_email_verification(user, profile, email, request=None, check=True):
    iids = component.getUtility(IIntIds)
    if iids.queryId(user) is None:
        logger.debug("Not sending email verification during account creation of %s",
                     user)
        return

    try:
        return send_email_verification(user,
                                       profile,
                                       email,
                                       request=request,
                                       check=check)
    except Exception:
        logger.exception("Cannot send email confirmation to %s.", user)
        return False
