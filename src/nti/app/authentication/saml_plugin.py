#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import warnings
from glob import glob

import simplejson

try:
	from saml2.config import SPConfig
	from saml2.client import Saml2Client
	from saml2.sigver import SigverError
	from saml2.s2repoze.plugins.sp import SAML2Plugin as _SAML2Plugin
except ImportError:  # pypy
	_SAML2Plugin = object

from zope import component

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

# functions

def normalize_path(path):
	path = os.path.expandvars(path) if path else path
	path = os.path.expanduser(path) if path else path
	path = os.path.realpath(os.path.normpath(path)) if path else path
	return path

def find_xmlsec_path():
	try:
		from saml2.sigver import get_xmlsec_binary
		result = get_xmlsec_binary(["/opt/local/bin", "/usr/local/bin", "/usr/bin"])
	except (Exception, SigverError):
		warnings.warn("xmlsec1 not found")
		result = None
	return result

def etc_dir(path=None):
	if not path:
		ds = os.environ.get('DATASERVER_DIR')
		path = os.path.join(ds, 'etc') if ds else None
	path = normalize_path(path)
	return path

def find_sp_file(path=None):
	path = etc_dir(path)
	path = os.path.join(path, 'sp.json') if path else path
	if path and os.path.exists(path):
		return path
	return None

def find_idp_files(path=None):
	path = etc_dir(path)
	result = glob(os.path.join(path, 'idp*.xml')) if path else ()
	return result

def make_plugin(path=None,
				wayf="",
				cache="",
				discovery="",
				sid_store="",
				identity_cache="",
				idp_query_param="",
				virtual_organization="",
				remember_name=str("auth_tkt")):
	path = path or os.environ.get('DATASERVER_DIR')
	path = normalize_path(path)
	if _SAML2Plugin is object:
		return None

	# find config files
	sp = find_sp_file(path)
	idps = find_idp_files(path)

	# no service provider
	if not sp:
		return None

	# check service provider
	with open(sp) as fp:
		sp_json = simplejson.load(fp, "UTF-8")

	# check xmlsec binary
	xmlsec_path = find_xmlsec_path()
	spec_path = sp_json.get('xmlsec_binary')
	if not spec_path or not os.path.exists(spec_path):
		sp_json.pop('xmlsec_binary', None)
		if xmlsec_path:
			sp_json['xmlsec_binary'] = xmlsec_path

	# check anything specified exists
	cwd = os.getcwd()
	try:
		os.chdir(path)
		# check local idps
		metadata = sp_json.get('metadata') or {}
		local = metadata.get('local') or ()
		local = set(normalize_path(x) for x in local if os.path.exists(normalize_path(x)))
		# cert/key fields
		for name in ("cert_file", "key_file"):
			try:
				value = sp_json[name]
				value = normalize_path(value) if value else None
				if not value or not os.path.exists(value):
					sp_json.pop(name, None)
				else:
					sp_json[name] = value
			except KeyError:
				pass

		# add specified idps some
		local.update(idps)
		if not local:
			warnings.warn("No idps found")
			return None
		if sp_json.get('metadata') is None:
			sp_json['metadata'] = {}
		sp_json['metadata']['local'] = sorted(local)

		# parse config
		conf = SPConfig().load(sp_json)
		conf.context = "sp"
		# create client
		scl = Saml2Client(config=conf, identity_cache=identity_cache,
					  	  virtual_organization=virtual_organization)
		# create plugin
		plugin = SAML2Plugin(remember_name, conf, scl, wayf, cache, sid_store,
						 	 discovery, idp_query_param)
		return plugin
	finally:
		os.chdir(cwd)

# classes

class SAML2Plugin(_SAML2Plugin):

	def _pick_idp(self, environ, came_from):
		policy = component.queryAdapter(ISitePolicyUserEventListener)
		idp_entity_id = getattr(policy, 'IDP_ENTITY_ID', None)
		if idp_entity_id:
			return 0, idp_entity_id
		return _SAML2Plugin._pick_idp(self, environ, came_from)
