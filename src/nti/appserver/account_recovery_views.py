#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to recovering information about accounts (lost username and/or passcode)

For the general design, see `Everything you ever wanted to know about building a secure
password reset feature <http://www.troyhunt.com/2012/05/everything-you-ever-wanted-to-know.html>`_

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import uuid
import urllib
import datetime
import urlparse
from collections import namedtuple

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.schema.interfaces import ValidationError

from pyramid.view import view_config

from nti.appserver import MessageFactory as _

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users.interfaces import checkEmailAddress

from nti.dataserver.users.users import User

from nti.dataserver.users.user_profile import make_password_recovery_email_hash

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.app.externalization.error import raise_json_error
from nti.app.externalization.error import handle_validation_error
from nti.app.externalization.internalization import update_object_from_external_object

from nti.appserver._email_utils import queue_simple_html_text_email

import nti.appserver.httpexceptions as hexc

from nti.coremetadata.interfaces import IUsernameSubstitutionPolicy

#: The link relationship type for a link used to recover a username,
#: given an email address. Also serves as a route name for that same
#: purpose (:func:`forgot_username_view`). Unauthenticated users will
#: be given a link with this rel at logon ping and
#: handshake time.
REL_FORGOT_USERNAME = "logon.forgot.username"

#: The link relationship type for a link used to initiate the reset of a password,
#: given an email address *and* username. Also serves as a route name for that same
#: purpose (:func:`forgot_passcode_view`). Unauthenticated users will
#: be given a link with this rel at logon ping and
#: handshake time.
REL_FORGOT_PASSCODE = "logon.forgot.passcode"

#: The link relationship type for a link used to finish a reset of a
#: password, given username and the token generated by the previous
#: step. Also serves as a route name for that same purpose
#: (:func:`reset_passcode_view`). Unauthenticated users will be
#: given a link with this rel at logon ping
#: and handshake time.
REL_RESET_PASSCODE = 'logon.reset.passcode'


def _preflight_email_based_request(request):
    if request.authenticated_userid:
        raise_json_error(request,
                         hexc.HTTPForbidden,
                         {
                             'message': _(u"Cannot look for forgotten accounts while logged on.")
                         },
                         None)

    email_assoc_with_account = request.params.get('email')
    if not email_assoc_with_account:
        raise_json_error(request,
                         hexc.HTTPBadRequest,
                         {
                             'message': _(u"Must provide email.")
                         },
                         None)

    try:
        checkEmailAddress(email_assoc_with_account)
    except ValidationError as e:
        handle_validation_error(request, e)
    return email_assoc_with_account


def _create_mock_user(user):
    """
    Return the applicable alternate username, if we have a policy for it.
    """
    username = getattr(user, 'username', None) or ''
    policy = component.queryUtility(IUsernameSubstitutionPolicy)
    if policy is not None:
        result = policy.replace(username)
    else:
        result = username
    return MockUser(result)


MockUser = namedtuple('MockUser', ['username'])


@view_config(route_name=REL_FORGOT_USERNAME,
             request_method='POST',
             renderer='rest')
def forgot_username_view(request):
    """
    Initiate the recovery workflow for a lost/forgotten username by taking
    the email address associated with the account as a POST parameter named 'email'.

    Only if the request is invalid will this return an HTTP error; in all other cases,
    it will return HTTP success, having fired off (or queued) an email for sending.
    """

    email_assoc_with_account = _preflight_email_based_request(request)
    matching_users = find_users_with_email(email_assoc_with_account,
                                           request.registry.getUtility(IDataserver))
    if matching_users:
        # ensure only real users, not profiles or other matches
        matching_users = filter(IUser.providedBy,
                                matching_users)
        # create mock users for each user. This will let us apply the
        # username substitution policy to their usernames (for OU 4x4s)
        # without needing to modify the template.
        matching_users = map(lambda user: _create_mock_user(user),
                             matching_users)

    # Need to send both HTML and plain text if we send HTML, because
    # many clients still do not render HTML emails well (e.g., the popup notification on iOS
    # only works with a text part)
    policy = component.getUtility(ISitePolicyUserEventListener)
    base_template = getattr(policy,
                            'USERNAME_RECOVERY_EMAIL_TEMPLATE_BASE_NAME',
                            'username_recovery_email')

    text_ext = ".mak"
    if not matching_users:
        text_ext = ".txt"
        base_template = 'failed_' + base_template

    subject = getattr(policy,
                      'USERNAME_RECOVERY_EMAIL_SUBJECT',
                      'NextThought Username Reminder')

    package = getattr(policy, 'PACKAGE', None)
    queue_simple_html_text_email(base_template, subject=_(subject),
                                 recipients=[email_assoc_with_account],
                                 template_args={
                                     'users': matching_users,
                                     'email': email_assoc_with_account
                                 },
                                 request=request,
                                 package=package,
                                 text_template_extension=text_ext)
    return hexc.HTTPNoContent()


# We store a tuple as an annotation of the user object for
# password reset, and this is the key
# (token, datetime, ???)
_KEY_PASSCODE_RESET = __name__ + '.' + u'forgot_passcode_view_key'


@view_config(route_name=REL_FORGOT_PASSCODE,
             request_method='POST',
             renderer='rest')
def forgot_passcode_view(request):
    """
    Initiate the recovery workflow for a lost/forgotten password by taking
    the email address associated with the account as a POST parameter named 'email'
    together with the username to reset as the POST parameter named 'username'.
    The caller must also supply the POST parameter 'success', which lists a callback URL
    to continue the process.

    Only if the request is invalid will this return an HTTP error; in all other cases,
    it will return HTTP success, having fired off (or queued) an email for sending.

    The 'success' parameter should name a URL that is prepared to take two query parameters,
    'username' and 'id' and which can then interact with the server's :func:`reset_passcode_view`
    using those two parameters.

    """

    email_assoc_with_account = _preflight_email_based_request(request)

    username = request.params.get('username') or ''
    username = username.strip()
    if not username:
        raise_json_error(request,
                         hexc.HTTPBadRequest,
                         {
                             'message': _(u"Must provide username.")
                         },
                         None)
    username = username.lower()  # normalize

    success_redirect_value = request.params.get('success')
    if not success_redirect_value:
        raise_json_error(request,
                         hexc.HTTPBadRequest,
                         {
                             'message': _(u"Must provide success.")
                         },
                         None)

    matching_users = find_users_with_email(email_assoc_with_account,
                                           component.getUtility(IDataserver),
                                           username=username)

    policy = component.getUtility(ISitePolicyUserEventListener)
    base_template = getattr(policy,
                            'PASSWORD_RESET_EMAIL_TEMPLATE_BASE_NAME',
                            'password_reset_email')

    # Ok, we either got one user on no users
    if matching_users and len(matching_users) == 1:
        # We got one user. So we need to generate a token, and
        # store the timestamped value, while also invalidating any other
        # tokens we have for this user.
        matching_user = matching_users[0]
        annotations = IAnnotations(matching_user)

        token = uuid.uuid4().hex
        now = datetime.datetime.utcnow()
        value = (token, now)
        annotations[_KEY_PASSCODE_RESET] = value

        parsed_redirect = urlparse.urlparse(success_redirect_value)
        parsed_redirect = list(parsed_redirect)
        query = parsed_redirect[4]
        if query:
            query =   query + '&username=' \
                    + urllib.quote(matching_user.username) \
                    + '&id=' + urllib.quote(token)
        else:
            query =  'username=' \
                   + urllib.quote(matching_user.username) \
                   + '&id=' + urllib.quote(token)

        parsed_redirect[4] = query
        success_redirect_value = urlparse.urlunparse(parsed_redirect)

        reset_url = success_redirect_value

    else:
        logger.warn("Failed to find user with username '%s' and email '%s': %s",
                    username, email_assoc_with_account, matching_users)
        matching_user = None
        value = (None, None)
        reset_url = None
        base_template = 'failed_' + base_template

    subject = getattr(policy,
                      'PASSWORD_RESET_EMAIL_SUBJECT',
                      'NextThought Password Reset')
    package = getattr(policy, 'PACKAGE', None)

    queue_simple_html_text_email(base_template, subject=_(subject),
                                 recipients=[email_assoc_with_account],
                                 template_args={
                                    'users': matching_users,
                                    'user': matching_user,
                                    'reset_url': reset_url,
                                    'email': email_assoc_with_account},
                                 package=package,
                                 request=request)

    return hexc.HTTPNoContent()


from nti.dataserver.users import index as user_index
from zope.catalog.interfaces import ICatalog


def find_users_with_email(email, unused_dataserver, username=None, match_info=False):
    """
    Looks for and returns all users with an email or password recovery
    email hash (or parent/contact email hash) matching the given email.

    :param basestring username: If given, we will only examine
            a user with this name (and will return a sequence of length 0 or 1); if found,
            only an :class:`.IUser` will be in the sequence.

    :param bool match_info: If given and True, then the result will be a sequence of
            `tuple` objects, first the user and then the name of the field that matched.
    :return: A sequence of the matched user objects.
    """

    matches = set()
    hashed_email = make_password_recovery_email_hash(email)
    ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)

    for match_type, v in (('email', email),
                          ('contact_email', email),
                          ('password_recovery_email_hash', hashed_email),
                          ('contact_email_recovery_hash', hashed_email)):
        # If we're not collecting the match info, then keep the set property based just
        # on the matches, not the type too. this prevents getting duplicate IUser objects back
        # in the case that a restricted profile user recorded the same email information
        # for his own use and his parental contact.
        record_type = match_type if match_info else ''
        matches.update(((x, record_type)
                        for x in ent_catalog.searchResults(**{match_type: (v, v)})))

    if username:
        matches = ((u, match_type) for u, match_type in matches
                   if IUser.providedBy(u) and u.username.lower() == username)

    return [x[0] for x in matches] if not match_info else list(matches)


def _is_link_expired(token_time):
    now = datetime.datetime.utcnow()
    # JZ - 2.2016 - 4 hour trial run (was 1 hour).
    delta = datetime.timedelta(hours=-4)
    start_boundary = now + delta
    result = token_time < start_boundary
    if result:
        age = now - token_time
        logger.info('Password recovery link expired (days=%s) (hours=%s) (minutes=%s)',
                    age.days,
                    int(age.seconds / 3600 % 24),
                    int(age.seconds / 60 % 60))
    return result


@view_config(route_name=REL_RESET_PASSCODE,
             request_method='POST',
             renderer='rest')
def reset_passcode_view(request):
    """
    The culmination of a password reset process. Takes as POST parameters the
    ``username`` and ``id`` that were generated in the :func:`forgot_passcode_view`,
    plus (optionally) the new ``password``.

    If no new password is provided, this will serve as a preflight check on the
    username and id, making sure it hasn't expired and is valid for the username; if
    any of those conditions do not hold, then an http 4XX will be returned.

    If the username and id are valid, and a new password is provided, then
    we will attempt to reset the password, the same as if the user was normally
    resetting the passcode through posting to the User object. That implies that this
    function can return the same sets of errors for invalid passwords as normal.

    If all goes according to plan and the password is reset, the User object is returned.
    Note that this does not log the user in; they must use their new password to do that.

    """
    if request.authenticated_userid:
        raise_json_error(request,
                         hexc.HTTPForbidden,
                         {
                             'message': _(u"Cannot look for forgotten accounts while logged on.")
                         },
                         None)

    username = request.params.get('username')
    if not username:
        raise_json_error(request,
                         hexc.HTTPBadRequest,
                         {
                             'message': _(u"Must provide username.")
                         },
                         None)

    token = request.params.get('id')
    if not token:
        raise_json_error(request,
                         hexc.HTTPBadRequest,
                         {
                             'message': _(u"Must provide token id.")
                         },
                         None)

    # Return the same error message for no-such-user, bad-token, and expired-token.
    # To make it harder to phish in the system. The app can only say "start
    # over"
    user = User.get_user(username)
    value = (None, None)
    annotations = IAnnotations(user) if user else {}
    value = annotations.get(_KEY_PASSCODE_RESET, value)
    if value[0] != token or _is_link_expired(value[1]):
        # expired, no user, bad token
        raise_json_error(request,
                         hexc.HTTPNotFound,
                         {
                             'code': 'InvalidOrMissingOrExpiredResetToken',
                             'message': _(u"Your reset link is not valid. Please request a new one.")
                         },
                         None)

    new_password = request.params.get('password')
    if not new_password:  # preflight
        return hexc.HTTPNoContent()

    # First, clear the old password, because we do not have one to
    # send for comparison purposes. Note that if we fail to reset
    # do to the policy, then we will abort the transaction and this
    # won't be persistent
    if user.has_password():
        del user.password

    update_object_from_external_object(user, {'password': new_password},
                                       notify=False, request=request)

    # Great, it worked. Kill the annotation so that it CANNOT be used again
    # (otherwise the window of vulnerability is larger than it needs to be)
    del annotations[_KEY_PASSCODE_RESET]

    # Assuming that works, return the user
    return user
