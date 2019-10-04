#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import math
import time
import hashlib
from datetime import datetime

import isodate

from itsdangerous.jws import JSONWebSignatureSerializer as SignatureSerializer

from six.moves import urllib_parse

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from zope.dottedname import resolve as dottedname

from zope.i18n import translate

from zope.intid.interfaces import IIntIds

from zope.security.interfaces import IPrincipal

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.users import MessageFactory as _

from nti.app.users import VERIFY_USER_EMAIL_VIEW

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.base._compat import text_
from nti.base._compat import bytes_

from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.common import entity_creation_sitename
from nti.dataserver.users.common import set_entity_creation_site as set_creation_site
from nti.dataserver.users.common import remove_entity_creation_site as remove_creation_site

from nti.dataserver.users.communities import Community

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IEmailAddressable
from nti.dataserver.users.interfaces import ICommunityPolicyManagementUtility

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import get_users_by_site
from nti.dataserver.users.utils import get_community_members
from nti.dataserver.users.utils import intids_of_users_by_site
from nti.dataserver.users.utils import intids_of_community_members
from nti.dataserver.users.utils import get_communities_by_site

from nti.externalization.externalization import to_external_object

from nti.mailer.interfaces import ITemplatedMailer

from nti.site.hostpolicy import get_host_site

from nti.site.site import get_component_hierarchy_names

_EMAIL_VERIFICATION_TIME_KEY = 'nti.app.users._EMAIL_VERIFICATION_TIME_KEY'
_EMAIL_VERIFICATION_COUNT_KEY = 'nti.app.users._EMAIL_VERIFICATION_COUNT_KEY'

logger = __import__('logging').getLogger(__name__)


def get_user(user):
    return user if IUser.providedBy(user) else User.get_user(str(user or ''))


def _token(signature):
    return int(hashlib.sha1(bytes_(signature)).hexdigest(), 16) % (10 ** 8)


def _signature_and_token(username, email, secret_key):
    s = SignatureSerializer(secret_key)
    signature = s.dumps({'email': email, 'username': username})
    token = _token(signature)
    return signature, token


def generate_mail_verification_pair(user, email=None, secret_key=None):
    __traceback_info__ = user, email  # pylint: disable=unused-variable
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
    __traceback_info__ = user, email, params  # pylint: disable=unused-variable
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
    params = urllib_parse.urlencode({'username': user.username.lower(),
                                     'signature': signature})

    href = '%s/%s?%s' % (ds2, '@@' + VERIFY_USER_EMAIL_VIEW, params)
    result = urllib_parse.urljoin(host_url, href) if host_url else href
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
        logger.warning("Not sending email to %s because of no email or request",
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
                subject=translate(_(u"Email Confirmation")),
                recipients=[user],
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
        logger.debug("Not sending email verification during account "
                     "creation of %s", user)
        return

    try:
        return send_email_verification(user,
                                       profile,
                                       email,
                                       request=request,
                                       check=check)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Cannot send email confirmation to %s.", user)
        return False


def get_user_creation_sitename(user):
    return entity_creation_sitename(get_user(user))


def get_user_creation_site(user):
    name = get_user_creation_sitename(user)
    return get_host_site(name, True) if name else None


def get_entity_creation_sitename(user):
    return entity_creation_sitename(user)


def get_entity_creation_site(user):
    name = get_entity_creation_sitename(user)
    return get_host_site(name, True) if name else None


def remove_user_creation_site(user):
    user = get_user(user)
    remove_creation_site(user)


def set_user_creation_site(user, site=None):
    user = get_user(user)
    site = getSite() if site is None else site
    name = getattr(site, '__name__', None) or str(site)
    if name == 'dataserver2':
        remove_user_creation_site(user)
    elif name:
        set_creation_site(user, name)
    return name


def get_community_name_from_site():
    policy = component.getUtility(ISitePolicyUserEventListener)
    name =  getattr(policy, 'COM_USERNAME', None)
    return name
get_site_community_name = get_community_name_from_site


def get_community_from_site():
    name =  get_community_name_from_site()
    return Community.get_community(name) if name else None
get_site_community = get_community_from_site


def set_community_creation_site(community, site=None):
    site = getSite() if site is None else site
    name = getattr(site, '__name__', None) or str(site)
    if name == 'dataserver2':
        remove_creation_site(community)
    elif name:
        set_creation_site(community, name)
    return name


def intids_of_community_or_site_members(all_members=False, site=None):
    """
    Returns the intids of the community or site members
    """
    community = get_community_from_site()
    if community is not None:
        return intids_of_community_members(community, all_members)
    return intids_of_users_by_site(site)


def get_community_or_site_members(all_members=False):
    """
    Returns the community or site members for current site
    """
    community = get_community_from_site()
    if community is not None:
        return get_community_members(community, all_members)
    return get_users_by_site()


def get_members_by_site(site, all_members=False):
    """
    Returns the community or site members for the specified site
    """
    name = getattr(site, '__name__', site)
    site = get_host_site(name, True)
    if site is not None:
        with current_site(site):
            return get_community_or_site_members(all_members)
    else: # e.g dataserver2
        return get_users_by_site(name)


def set_entity_creation_site(entity, site=None):
    site = getSite() if site is None else site
    name = getattr(site, '__name__', None) or str(site)
    if name == 'dataserver2':
        remove_creation_site(entity)
    elif name:
        set_creation_site(entity, name)
    return name


def can_create_new_communities():
    """
    Return a bool whether new communities can be created in this site. This
    *does not* check user permissions.
    """
    policy = component.getUtility(ICommunityPolicyManagementUtility)
    site_communities = get_communities_by_site()
    return policy.max_community_limit is None \
        or len(site_communities) < policy.max_community_limit


def get_site_admins(site=None):
    """
    Returns all site admins.
    """
    result = []
    site = getSite() if site is None else site
    try:
        srm = IPrincipalRoleManager(site, None)
    except TypeError:
        # SiteManagerContainer (tests)
        srm = None
    if srm is not None:
        for prin_id, access in srm.getPrincipalsForRole(ROLE_SITE_ADMIN.id):
            if access == Allow:
                user = User.get_user(prin_id)
                if user is not None:
                    result.append(user)
    return result
