#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from itsdangerous.jws import JSONWebSignatureSerializer

import saml2

from saml2 import BINDING_HTTP_POST
from saml2 import BINDING_HTTP_REDIRECT

from saml2 import xmldsig as ds
from saml2 import element_to_extension_element

from saml2.extension.pefim import SPCertEnc

from saml2.mdstore import destinations

from saml2.response import SAMLError

from saml2.samlp import Extensions

from zope import component
from zope import interface

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from nti.app.saml import make_location as _make_location

from nti.app.saml.interfaces import ISAMLClient
from nti.app.saml.interfaces import ISAMLNameId
from nti.app.saml.interfaces import ISAMLIDPInfo
from nti.app.saml.interfaces import ISAMLACSLinkProvider

from nti.appserver.interfaces import IApplicationSettings

from nti.base._compat import text_

from nti.schema.fieldproperty import createFieldProperties

RELAY_STATE = u'RelayState'
SAML_RESPONSE = u'SAMLResponse'
ERROR_STATE_PARAM = u'_nti_error'
SUCCESS_STATE_PARAM = u'_nti_success'

logger = __import__('logging').getLogger(__name__)


def _get_signer_secret(default_secret=u'not-very-secure-secret'):
    settings = component.queryUtility(IApplicationSettings) or {}
    # XXX: Reusing the cookie secret, we should probably have our own
    secret_key = settings.get('cookie_secret', default_secret)
    return secret_key or default_secret


def _make_signer(secret, salt=u'nti-saml-relay-state'):
    return JSONWebSignatureSerializer(secret, salt=salt)


@interface.implementer(ISAMLNameId)
class _SAMLNameId(object):
    createFieldProperties(ISAMLNameId)

    __external_class_name__ = 'SAMLNameId'

    mimeType = mime_type = 'application/vnd.nextthought.saml.samlnameid'

    def __init__(self, name_id):
        self.nameid = text_(name_id.text)
        self.name_format = name_id.format
        self.name_qualifier = text_(name_id.name_qualifier)
        self.sp_name_qualifier = text_(name_id.sp_name_qualifier)


@interface.implementer(ISAMLClient)
class BasicSAMLClient(object):
    """
    A basic implementation of ISAML client based on the saml2 client package.
    This is largerly based on the who middleware SAML2Plugin implementation
    but in a format that fits better into our existing multi idp login process.
    While the underlying SAML client supports the full spec we support the basic
    minimum based of OU's current SAML idp implementation.
    This can be expanded in the future.

    Notable omissions from the SAML2Plugin are:
    * Multi idp support
    * IDP discovery
    * Outstanding request and outstanding cert tracking/verification
    """

    saml_client = None

    def __init__(self, config, saml_client, wayf, cache, idp_query_param=u""):
        self.wayf = wayf
        self.cache = cache
        self.conf = config
        self.saml_client = saml_client
        self.idp_query_param = idp_query_param
        try:
            self.metadata = self.conf.metadata
        except KeyError:
            self.metadata = None

    def _pick_idp(self):
        idp = component.queryUtility(ISAMLIDPInfo)
        return idp.entity_id

    def _extract_relay_state(self, relay_state):
        signer = _make_signer(_get_signer_secret())

        state = signer.loads(relay_state)

        success = state.pop(SUCCESS_STATE_PARAM, None) if state else None
        error = state.pop(ERROR_STATE_PARAM, None) if state else None

        return state, success, error

    def _create_relay_state(self, state={}, success=None, error=None):
        if success:
            state[SUCCESS_STATE_PARAM] = success
        if error:
            state[ERROR_STATE_PARAM] = error

        signer = _make_signer(_get_signer_secret())
        return signer.dumps(state)

    def response_for_logging_out(self, session_auth_id, success,
                                 error, entity_id=None):
        if not entity_id:
            entity_id = self._pick_idp()

        if entity_id is None:
            raise ValueError('Unable to find idp entity id for SAML')

        _binding = BINDING_HTTP_REDIRECT
        _cli = self.saml_client

        if error is not None:
            logger.warn(error)

        logger.info("Generating SAML logout request for IDP %s", entity_id)
        srvs = _cli.metadata.single_logout_service(entity_id,
                                                   _binding,
                                                   'idpsso')
        dest = destinations(srvs)[0]

        location = _make_location(dest,
                                  {
                                      'TargetResource': success,
                                      'InErrorResource': success,
                                      'SpSessionAuthn': session_auth_id
                                  })
        return hexc.HTTPSeeOther(location)

    def response_for_logging_in(self, success, error, state={}, passive=False,
                                force_authn=False, entity_id=None, acs_link=None,
                                want_response_signed=None):
        if not entity_id:
            entity_id = self._pick_idp()

        if entity_id is None:
            raise ValueError('Unable to find idp entity id for SAML')

        _binding = BINDING_HTTP_REDIRECT
        _cli = self.saml_client

        logger.info("Generating SAML request for IDP %s", entity_id)

        try:
            srvs = _cli.metadata.single_sign_on_service(entity_id, _binding)
            logger.debug("srvs: %s", srvs)
            dest = srvs[0]["location"]
            logger.debug("destination: %s", dest)

            # cert = None
            extensions = None

            if _cli.config.generate_cert_func is not None:
                cert_str, _ = _cli.config.generate_cert_func()
                # cert = {
                #     "cert": cert_str,
                #     "key": req_key_str
                # }
                x509_certificate = ds.X509Certificate(text=cert_str)
                x509_data = ds.X509Data(x509_certificate=x509_certificate)
                spcertenc = SPCertEnc(x509_data=x509_data)
                extension_elements = [element_to_extension_element(spcertenc)]
                extensions = Extensions(extension_elements=extension_elements)

            is_passive = 'true' if passive else None
            force = 'true' if force_authn else None
            want_response_signed = 'false' if want_response_signed is None else 'true'

            if not acs_link:
                request = get_current_request()
                provider = component.queryAdapter(request,
                                                  ISAMLACSLinkProvider)
                acs_link = provider.acs_link(request) if provider else None

            extra_args = {
                'force_authn': force,
                'is_passive': is_passive,
                'assertion_consumer_service_url': acs_link,
                'want_response_signed': want_response_signed,
            }

            if _cli.authn_requests_signed:
                _sid = saml2.s_utils.sid()
                req_id, msg_str = \
                    _cli.create_authn_request(dest, vorg=u"",
                                              message_id=_sid,
                                              extensions=extensions,
                                              sign=_cli.authn_requests_signed,
                                              **extra_args)
                _sid = req_id
            else:
                req_id, req = \
                    _cli.create_authn_request(dest, vorg=u"",
                                              sign=False,
                                              extensions=extensions,
                                              **extra_args)
                msg_str = u"%s" % req
                _sid = req_id

            state = self._create_relay_state(state=state,
                                             success=success,
                                             error=error)

            ht_args = _cli.apply_binding(_binding, msg_str,
                                         destination=dest,
                                         relay_state=state)

            logger.debug("ht_args: %s", ht_args)
            if not ht_args["data"] and ht_args["headers"][0][0] == "Location":
                location = ht_args["headers"].pop(0)[1]
                logger.debug('redirect to: %s', location)
                return hexc.HTTPSeeOther(location, headers=ht_args["headers"])
            else:
                return ht_args["data"]

        except Exception as exc:
            logger.exception('Unable to generate SAML AuthnRequest')
            raise exc

    def _eval_authn_response(self, saml_response, binding=BINDING_HTTP_REDIRECT):
        logger.info('Processing SAML Authn Response')
        logger.info('response %s', saml_response)
        authresp = self.saml_client.parse_authn_request_response(saml_response,
                                                                 binding)
        return authresp

    def process_saml_acs_request(self, request):
        for param in (SAML_RESPONSE, RELAY_STATE):
            if param not in request.params:
                logger.warn('Unexpected saml response. No param named %s',
                            param)
                raise hexc.HTTPBadRequest()

        # parse out our relay state first so we have it
        state, success, error = \
            self._extract_relay_state(request.params.get(RELAY_STATE, None))

        # this will throw if the response is invalid, such as invalid authentication
        # but we need to capture and provide our state, success, and error
        # so we can get the user back to the proper place. Trap the error, and reraise
        # our exception to indicate a bad saml assertion
        try:
            if request.method == 'POST':
                binding = BINDING_HTTP_POST
            else:
                binding = BINDING_HTTP_REDIRECT
            response = self._eval_authn_response(request.params[SAML_RESPONSE],
                                                 binding=binding)
        except SAMLError as e:
            logger.exception('Invalid saml response')
            e.state = state
            e.success = success
            e.error = error
            raise e

        return response, state, success, error
