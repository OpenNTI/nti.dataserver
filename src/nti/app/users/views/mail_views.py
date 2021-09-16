#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from itsdangerous.exc import BadSignature

from pyramid import httpexceptions as hexc

from pyramid.renderers import render

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

import six
from six.moves import urllib_parse

from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error as raise_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users import VERIFY_USER_EMAIL_VIEW
from nti.app.users import REQUEST_EMAIL_VERFICATION_VIEW
from nti.app.users import SEND_USER_EMAIL_VERFICATION_VIEW
from nti.app.users import VERIFY_USER_EMAIL_WITH_TOKEN_VIEW

from nti.app.users.utils import get_email_verification_time
from nti.app.users.utils import safe_send_email_verification
from nti.app.users.utils import generate_mail_verification_pair
from nti.app.users.utils import get_verification_signature_data
from nti.app.users.utils import generate_legacy_mail_verification_pair

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.common._compat import sleep

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import checkEmailAddress

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import reindex_email_verification

from nti.externalization.externalization import to_external_object

MAX_REQUEST_COUNT = 5

#: Max wait time between emails
MAX_WAIT_TIME_EMAILS = 300  # 5 mins

logger = __import__('logging').getLogger(__name__)


def _login_app_root():
    settings = component.getUtility(IApplicationSettings)
    login_root = settings.get('login_app_root', '/login/')
    return login_root


@view_config(route_name='objects.generic.traversal',
             name=VERIFY_USER_EMAIL_VIEW,
             request_method='GET',
             context=IDataserverFolder)
class VerifyUserEmailView(AbstractAuthenticatedView):

    def process_verification(self, user, values):
        signature = values.get('signature') or values.get('token')
        if not signature:
            raise_error(self.request,
                        hexc.HTTPUnprocessableEntity,
                        {
                            'message': _(u"No signature specified."),
                        },
                        None)
        try:
            get_verification_signature_data(user, signature, params=values)
        except BadSignature:
            raise_error(self.request,
                        hexc.HTTPUnprocessableEntity,
                        {
                            'message': _(u"Invalid signature."),
                        },
                        None)
        except ValueError as e:
            raise_error(self.request,
                        hexc.HTTPUnprocessableEntity,
                        {
                            'message': str(e),
                        },
                        None)

        self.request.environ['nti.request_had_transaction_side_effects'] = 'True'
        IUserProfile(user).email_verified = True
        reindex_email_verification(user)

    def _do_render(self, template_args):
        result = render("../templates/email_verification_completion_page.pt",
                        template_args,
                        request=self.request)

        response = self.request.response
        response.content_type = str('text/html')
        response.content_encoding = str('identity')
        response.text = result
        return response

    @Lazy
    def _brand_name(self):
        return component.getMultiAdapter((getSite(), self.request),
                                         IDisplayNameGenerator)()

    def __call__(self):
        request = self.request
        user = self.remoteUser
        login_root = _login_app_root()

        if user is None:
            # If unauthenticated, redirect to login with redirect to this view.
            # This seems generic enough that we would want to do
            # this for all authenticated views (or the
            # BrowserRedirectorPlugin).
            current_path = request.current_route_path()
            current_path = urllib_parse.quote(current_path)
            return_url = "%s?return=%s" % (login_root, current_path)
            return hexc.HTTPFound(location=return_url)

        destination_url = urllib_parse.urljoin(self.request.application_url,
                                               login_root)
        template_args = {'href': destination_url}

        policy = component.getUtility(ISitePolicyUserEventListener)
        support_email = getattr(policy, 'SUPPORT_EMAIL', None)
        support_email = support_email or 'support@nextthought.com'

        profile = IUserProfile(user)
        user_ext = to_external_object(user)
        informal_username = user_ext.get('NonI18NFirstName', profile.realname)
        # pylint: disable=no-member
        informal_username = informal_username or user.username

        template_args['profile'] = profile
        template_args['error_message'] = None
        template_args['support_email'] = support_email
        template_args['informal_username'] = informal_username
        template_args['site_name'] = self._brand_name
        template_args['username'] = getattr(user, 'username', '')

        try:
            values = CaseInsensitiveDict(request.params)
            self.process_verification(user, values)
        except hexc.HTTPError as e:
            logger.info('Account verification for user "%s" failed. %s',
                        user,
                        getattr(e, 'detail', ''))
            template_args['error_message'] = _(u"Unable to verify account.")

        return self._do_render(template_args)


@view_config(route_name='objects.generic.traversal',
             name=VERIFY_USER_EMAIL_WITH_TOKEN_VIEW,
             request_method='POST',
             context=IDataserverFolder)
class VerifyUserEmailWithTokenView(AbstractAuthenticatedView,
                                   ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        token = values.get('hash') or values.get('token')
        if not token:
            raise_error(self.request,
                        hexc.HTTPUnprocessableEntity,
                        {
                            'message': _(u"No token specified."),
                        },
                        None)
        try:
            token = int(token)
        except (TypeError, ValueError):
            raise_error(self.request,
                        hexc.HTTPUnprocessableEntity,
                        {
                            'message': _(u"Invalid token."),
                        },
                        None)

        sig, computed = generate_mail_verification_pair(self.remoteUser)
        if token != computed:
            legacy_sig, legacy_computed = \
                generate_legacy_mail_verification_pair(self.remoteUser)
            if token != legacy_computed:
                # pylint: disable=unused-variable
                __traceback_info__ = sig, computed, legacy_sig, legacy_computed
                raise_error(self.request,
                            hexc.HTTPUnprocessableEntity,
                            {
                                'message': _(u"Wrong token."),
                            },
                            None)

        IUserProfile(self.remoteUser).email_verified = True
        reindex_email_verification(self.remoteUser)
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             name=REQUEST_EMAIL_VERFICATION_VIEW,
             request_method='POST',
             context=IUser,
             renderer='rest',
             permission=nauth.ACT_UPDATE)
class RequestEmailVerificationView(AbstractAuthenticatedView,
                                   ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        if self.request.body:
            values = super(RequestEmailVerificationView, self).readInput(value)
        else:
            values = self.request.params
        result = CaseInsensitiveDict(values)
        return result

    def __call__(self):
        user = self.remoteUser
        profile = IUserProfile(user)
        email = self.readInput().get('email')
        if email:
            if checkEmailAddress(email):
                profile.email = email
                profile.email_verified = None
                reindex_email_verification(user)
            else:
                raise_error(self.request,
                            hexc.HTTPUnprocessableEntity,
                            {
                                'message': _(u"Invalid email address."),
                            },
                            None)
        else:
            email = profile.email

        if email is None:
            raise_error(self.request,
                        hexc.HTTPUnprocessableEntity,
                        {
                            'message': _(u"Email address not provided."),
                        },
                        None)

        if not profile.email_verified:
            last_time = get_email_verification_time(user) or 0
            diff_time = time.time() - last_time
            if diff_time > MAX_WAIT_TIME_EMAILS:
                safe_send_email_verification(
                    user, profile, email, self.request
                )
            else:
                raise_error(self.request,
                            hexc.HTTPUnprocessableEntity,
                            {
                                'message': _(u"A current request is being processed."),
                                'seconds': MAX_WAIT_TIME_EMAILS - diff_time
                            },
                            None)
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             name=SEND_USER_EMAIL_VERFICATION_VIEW,
             request_method='POST',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN)
class SendUserEmailVerificationView(AbstractAuthenticatedView,
                                    ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        usernames = values.get('usernames') or values.get('username')
        if not usernames:
            raise_error(self.request,
                        hexc.HTTPUnprocessableEntity,
                        {
                            'message': _(u"Must specify a username."),
                        },
                        None)
        if isinstance(usernames, six.string_types):
            usernames = usernames.split(',')

        for username in usernames:
            user = User.get_user(username)
            if not IUser.providedBy(user):
                continue
            # send email
            profile = IUserProfile(user, None)
            email = getattr(profile, 'email', None)
            email_verified = getattr(profile, 'email_verified', False)
            if not email_verified:
                safe_send_email_verification(user, profile,
                                             email, self.request)
            else:
                logger.debug("Not sending email verification to %s", username)
            # wait a bit
            sleep(0.5)
        return hexc.HTTPNoContent()
