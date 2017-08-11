#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import Mapping

from pyramid import security as sec

from zope import component
from zope import interface

from zope.component import getMultiAdapter

from zope.event import notify

from pyramid.view import view_config

from saml2.response import SAMLError

from saml2.saml import NAMEID_FORMAT_PERSISTENT

from nti.app.saml import ACS
from nti.app.saml import SLS

from nti.app.saml import make_location as _make_location

from nti.app.saml.interfaces import ISAMLClient
from nti.app.saml.interfaces import ISAMLIDPInfo
from nti.app.saml.interfaces import IUserFactory
from nti.app.saml.interfaces import ISAMLACSLinkProvider
from nti.app.saml.interfaces import ISAMLIDPEntityBindings
from nti.app.saml.interfaces import ISAMLUserAssertionInfo
from nti.app.saml.interfaces import ISAMLAuthenticationResponse
from nti.app.saml.interfaces import ISAMLExistingUserValidator
from nti.app.saml.interfaces import ISAMLUserAuthenticatedEvent

from nti.app.saml.interfaces import ExistingUserMismatchError

from nti.app.saml.views import SAMLPathAdapter

from nti.appserver.interfaces import ILogoutForgettingResponseProvider

from nti.appserver.logon import logout as _do_logout
from nti.appserver.logon import _create_failure_response
from nti.appserver.logon import _create_success_response
from nti.appserver.logon import _deal_with_external_account

from nti.appserver.policies.interfaces import INoAccountCreationEmail

from nti.base._compat import text_

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IRecreatableUser

from nti.dataserver.users.utils import force_email_verification

LOGIN_SAML_VIEW = 'logon.saml'


@view_config(name=SLS,
             context=SAMLPathAdapter,
             route_name='objects.generic.traversal')
def sls_view(request):
    response = _do_logout(request)
    return response


@interface.implementer(ILogoutForgettingResponseProvider)
class SAMLLogoutResponseProvider(object):
    """
    A saml logout response provider that bounces the user through the saml SLO
    endpoint if they are authetnicated via saml. Sites that use SAML authentication
    should register this in their site.
    """

    def __init__(self, request):
        pass

    def _do_default(self, request, redirect_param_name, redirect_value=None):
        default_response_provider = component.getAdapter(request,
                                                         ILogoutForgettingResponseProvider,
                                                         name='default')
        return default_response_provider.forgetting(request,
                                                    redirect_param_name,
                                                    redirect_value=redirect_value)

    def forgetting(self, request, redirect_param_name, redirect_value=None):
        identity = request.environ.get('repoze.who.identity', {})
        userdata = identity.get('userdata', {})

        idp = userdata.get('nti.saml.idp')
        resp_id = userdata.get('nti.saml.response_id')
        if not idp or not resp_id:
            return self._do_default(request,
                                    redirect_param_name,
                                    redirect_value=redirect_value)

        if not redirect_value:
            redirect_value = request.params.get(redirect_param_name)

        # Unlike the default provider, where the redirect_value is relative to us,
        # a third party is ultimately issuing this redirect so it needs to be made
        # absolute
        redirect_value = request.relative_url(redirect_value)

        saml_client = component.queryUtility(ISAMLClient)
        response = saml_client.response_for_logging_out(resp_id,
                                                        redirect_value,
                                                        redirect_value,
                                                        idp)
        response.headers.extend(sec.forget(request))
        return response


@interface.implementer(ISAMLExistingUserValidator)
class ExistingUserNameIdValidator(object):
    """
    A default existing user validator that checks
    the persisted ISAMLNameId information
    """

    def __init__(self, request):
        pass

    def validate(self, user, user_info, idp):
        bindings = ISAMLIDPEntityBindings(user)
        try:
            nameid = bindings.binding(user_info.nameid, name_qualifier=idp)
        except KeyError:
            # No binding so we can't validate
            logger.warn('user %s exists but no preexisting saml bindings can be found %s',
                        user.username, idp)
            return False

        if nameid.nameid == user_info.nameid.nameid:
            return True

        msg = 'SAML persistent nameid {} for user {} does not match idp returned nameid {}'
        raise ExistingUserMismatchError(msg.format(nameid.nameid,
                                                   user.username,
                                                   user_info.nameid.nameid))


def _validate_idp_nameid(request, user, user_info, idp):
    """
    If a user has a preexisting nameid for this idp, verifies the idp identifier matches
    up with what we stored.  If the nameids are a mismatch we raise an exception.  It is unclear
    if we should do the same if the user has an associated binding to a different idp already.
    """
    validator = component.getAdapter(request,
                                     ISAMLExistingUserValidator,
                                     name='nameid')
    if validator.validate(user, user_info, idp):
        return

    # Our default nameid validator couldn't verify this user is the same
    # as our assertion, but it also didn't raise.  This means we found
    # a user with no nameid information for the appropriate name qualifiers.
    #
    # Adapt the request to a non-named ISAMLExistingUserValidator and if it
    # exists give it a chance to validate.  If it affirms the user is the same
    # then allow the authentication to go through.  If it doesn't explitly affirm
    # raise a mismatch error
    validator = component.queryAdapter(request, ISAMLExistingUserValidator)
    if validator and validator.validate(user, user_info, idp):
        return

    # We aren't sure this is the same user. Raise a mismatch error to stop
    # the authentication
    raise ExistingUserMismatchError(
        'Unable to validate existing user ' + user.username)


@view_config(name=LOGIN_SAML_VIEW,
             context=SAMLPathAdapter,
             request_method="GET",
             route_name='objects.generic.traversal')
def saml_login(context, request):
    if 'idp_id' not in request.params:
        return _create_failure_response(request, error='Missing idp_id')

    idp_id = request.params['idp_id']

    # validate the idp_id is valid in this site context
    idp = component.queryUtility(ISAMLIDPInfo)
    if not idp or idp.entity_id != idp_id:
        return _create_failure_response(request, error='IDP Mismatch')

    # If we get here without one of these something or someone really screwed up
    # bail loudly
    saml_client = component.queryUtility(ISAMLClient)
    success = request.params.get('success', '/')
    failure = request.params.get('failure', '/')
    return saml_client.response_for_logging_in(success,
                                               failure,
                                               entity_id=idp.entity_id)


@interface.implementer(ISAMLACSLinkProvider)
class ACSLinkProvider(object):

    def __init__(self, request):
        pass

    def acs_link(self, request):
        root = component.getUtility(IDataserver).dataserver_folder
        return request.resource_url(root, 'saml', '@@' + ACS)


def _failure_response(request, msg, error, state):
    _failure = _make_location(error, state) if (
        error and state is not None) else None
    error_str = msg
    return _create_failure_response(request,
                                    failure=_failure,
                                    error=(error_str if error_str else "An unknown error occurred."))


def _existing_user(request, user_info):
    username = user_info.username
    if username is None:
        raise ValueError("No username provided")
    user = User.get_entity(username)
    return user


@interface.implementer(IUserFactory)
class AssertionUserFactory(object):

    def __init__(self, request, info):
        self.request = request

    def create_user(self, user_info, factory=None):
        username = user_info.username

        if username is None:
            raise ValueError("No username provided")

        logger.info('Creating new user for %s', username)

        email = user_info.email
        email_found = bool(email)
        email = email or username

        # get realname
        firstName = user_info.firstname
        lastName = user_info.lastname
        realname = user_info.realname

        factory = factory if factory else User.create_user
        request = self.request
        if request is not None:
            interface.alsoProvides(self.request, INoAccountCreationEmail)
        user = _deal_with_external_account(request,
                                           username=username,
                                           fname=firstName,
                                           lname=lastName,
                                           email=email,
                                           idurl=None,
                                           iface=None,
                                           user_factory=factory,
                                           realname=realname)
        interface.alsoProvides(user, IRecreatableUser)
        if email_found:  # trusted source
            force_email_verification(user)
        return user


@view_config(name=ACS,
             context=SAMLPathAdapter,
             request_method="POST",
             route_name='objects.generic.traversal')
def acs_view(request):
    error = state = None
    try:
        saml_client = component.queryUtility(ISAMLClient)
        logger.info('Received an acs request')
        saml_response, state, success, error = \
            saml_client.process_saml_acs_request(request)

        interface.alsoProvides(saml_response, ISAMLAuthenticationResponse)

        response = saml_response.session_info()
        logger.info('sessioninfo: %s', response)

        idp_id = response['issuer']
        logger.info('Response from %s recieved, success %s, error %s',
                    idp_id, success, error)

        # Component lookup error here would be a programmer or config error
        user_info = component.getAdapter(response,
                                         ISAMLUserAssertionInfo,
                                         idp_id)
        logger.info('user_info parsed as %s', user_info)

        nameid = user_info.nameid
        if nameid is None:
            raise ValueError("No nameid provided")

        if nameid.name_format != NAMEID_FORMAT_PERSISTENT:
            raise ValueError("Expected persistent nameid but was %s",
                             nameid.name_format)

        user = component.queryMultiAdapter((request, user_info), IUser)

        # if user, verify saml nameid against idp
        if user is not None:
            logger.info('Found an existing user for %s', user.username)
            _validate_idp_nameid(request, user, user_info, idp_id)
        else:
            factory = component.getMultiAdapter((request, user_info),
                                                IUserFactory)
            user = factory.create_user(user_info)

        nameid_bindings = ISAMLIDPEntityBindings(user)
        try:
            nameid_bindings.store_binding(user_info.nameid,
                                          name_qualifier=idp_id)
        except KeyError:
            # Ignore existing binding for this user. We raise
            # earlier in the function if the binding exists but doesn't
            # match
            pass

        logger.info("%s logging in through SAML", user.username)
        request.environ['REMOTE_USER_DATA'] = {}

        # Manually fire event with SAML user info
        event = getMultiAdapter((idp_id, user, user_info, request),
                               ISAMLUserAuthenticatedEvent)
        event.saml_response = saml_response
        notify(event)

        return _create_success_response(request,
                                        userid=user.username,
                                        success=_make_location(success, state))

    except SAMLError as e:
        logger.error("Invalid SAML Assertion")
        error_msg = text_(repr(e))
        return _create_failure_response(request,
                                        failure=_make_location(e.error, e.state),
                                        error=error_msg)
    except ExistingUserMismatchError as e:
        logger.exception('Unable to match assertion to existing user')
        return _failure_response(request, 'User Mismatch', error, state)
    except Exception as e:
        logger.exception("An unknown error occurred processing saml response")
        return _failure_response(request, None, error, state)


import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.saml.model",
    "nti.app.saml.model",
    "SAMLIDPEntityBindings",
    "_SAMLIDEntityBindingsFactory",
    "SAML_IDP_BINDINGS_ANNOTATION_KEY")
