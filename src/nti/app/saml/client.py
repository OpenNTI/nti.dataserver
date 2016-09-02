#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: __init__.py 94273 2016-08-15 18:55:08Z carlos.sanchez $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import saml2

from saml2 import BINDING_HTTP_POST
from saml2 import BINDING_HTTP_REDIRECT

from saml2 import xmldsig as ds

from saml2.saml import NameID

from saml2.extension.pefim import SPCertEnc

from saml2.samlp import Extensions

from zope import component
from zope import interface

from pyramid import httpexceptions as hexc

from nti.app.saml.interfaces import ISAMLClient

from nti.schema.fieldproperty import createFieldProperties

from .interfaces import ISAMLIDPInfo
from .interfaces import ISAMLNameId
from .interfaces import ISAMLUserAssertionInfo

SAML_RESPONSE = u'SAMLResponse'


@interface.implementer(ISAMLNameId)
class _SAMLNameId(object):

	createFieldProperties(ISAMLNameId)

	def __init__(self, name_id):
		self.nameid = name_id.text
		self.name_format = name_id.format



@interface.implementer(ISAMLClient)
class BasicSAMLClient(object):
	"""
	A basic implementation of ISAML client based on the saml2 client package.
	This is largerly based on the who middleware SAML2Plugin implementation
	but in a format that fits better into our existing multi idp login process.  While the underlying
	SAML client supports the full spec we support the basic minimum based of OU's current
	SAML idp implementation.  This can be expanded in the future.

	Notable omissions from the SAML2Plugin are:
	* Multi idp support
	* IDP discovery
	* Outstanding request and outstanding cert tracking/verification
	"""

	saml_client = None

	def __init__(self,
				 config,
				 saml_client,
				 wayf,
				 cache,
				 idp_query_param=""):

		self.wayf = wayf
		self.saml_client = saml_client
		self.conf = config
		self.cache = cache
		self.idp_query_param = idp_query_param

		try:
			self.metadata = self.conf.metadata
		except KeyError:
			self.metadata = None

	def _pick_idp(self):
		from IPython.core.debugger import Tracer;Tracer()()
		idp = component.queryUtility(ISAMLIDPInfo)
		return idp.entity_id

	def response_for_logging_in(self, success, error, state=None, passive=False):

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

			extensions = None
			cert = None

			if _cli.config.generate_cert_func is not None:
				cert_str, req_key_str = _cli.config.generate_cert_func()
				cert = {
				"cert": cert_str,
				"key": req_key_str
				}
				spcertenc = SPCertEnc(x509_data=ds.X509Data(x509_certificate=ds.X509Certificate(text=cert_str)))
				extensions = Extensions(extension_elements=[element_to_extension_element(spcertenc)])

			if _cli.authn_requests_signed:
				_sid = saml2.s_utils.sid()
				req_id, msg_str = _cli.create_authn_request(
					dest, vorg="", sign=_cli.authn_requests_signed,
					message_id=_sid, extensions=extensions)
				_sid = req_id
			else:
				req_id, req = _cli.create_authn_request(
					dest, vorg="", sign=False, extensions=extensions)
				msg_str = "%s" % req
				_sid = req_id

			ht_args = _cli.apply_binding(_binding, msg_str,
				destination=dest,
				relay_state="")

			logger.debug("ht_args: %s", ht_args)

			if not ht_args["data"] and ht_args["headers"][0][0] == "Location":
				logger.debug('redirect to: %s', ht_args["headers"][0][1])
				return hexc.HTTPSeeOther(headers=ht_args["headers"])
			else:
				return ht_args["data"]

		except Exception as exc:
			logger.error('Unable to generate SAML AuthnRequest')
			raise exc

	def _eval_authn_response(self, saml_response, binding=BINDING_HTTP_REDIRECT):
		logger.info('Processing SAML Authn Response')
		try:

			try:
				authresp = self.saml_client.parse_authn_request_response(saml_response, binding, )
			except Exception:
				logger.exception('Unable to parse response')
				raise

			session_info = authresp.session_info()
		except TypeError:
			logger.exception('Unable to parse response')
			return None

		logger.info('sessioninfo: %s', session_info)
		return session_info

	def process_saml_acs_request(self, request):
		if SAML_RESPONSE not in request.params:
			raise hexc.HTTPBadRequest('Unexpected SAML Response. No %s', SAML_RESPONSE)
		binding = BINDING_HTTP_POST if request.method == 'POST' else BINDING_HTTP_REDIRECT
		response_info = self._eval_authn_response(request.params[SAML_RESPONSE], 
												  binding=binding)
		return response_info
