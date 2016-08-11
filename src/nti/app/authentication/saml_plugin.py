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
	from saml2.s2repoze.plugins.sp import SAML2Plugin as _SAML2Plugin
except ImportError: # pypy
	_SAML2Plugin = object

# functions

def find_xmlsec_path():
	try:
		from saml2.sigver import get_xmlsec_binary
		result = get_xmlsec_binary(["/opt/local/bin","/usr/local/bin", "/usr/bin"])
	except Exception:
		warnings.warn("xmlsec1 not found")
		result = None
	return result

def etc_dir(path=None):
	if not path:
		ds = os.environ.get('DATASERVER_DIR')
		path = os.path.join(ds, 'etc') if ds else None
	path = os.path.expanduser(path) if path else path
	path = os.path.normpath(path) if path else path
	return path

def find_sp_file(path=None):
	path = etc_dir(path)
	path = os.path.join(path, 'sp.xml') if path else path
	if path and os.path.exists(path):
		return path
	return None

def find_idp_files(path=None):
	path = etc_dir(path)
	result = glob(os.path.join(path, 'idp*.xml')) if path else ()
	return result

def create_saml2_plugin(path=None):
	path = path or os.environ.get('DATASERVER_DIR')	
	path = os.path.normpath(os.path.expanduser(path)) if path else path
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
	if (not spec_path or not os.path.exists(spec_path)) and xmlsec_path:
		sp_json['xmlsec_binary'] = xmlsec_path
	else:
		sp_json.pop('xmlsec_binary', None)

	# check anything specified exists
	cwd = os.getcwd()
	os.chdir(path)
	metadata = sp_json.get('metadata') or {}
	local = metadata.get('local') or ()
	local = set(os.path.normpath(x) for x in local if os.path.exists(os.path.normpath(x)))
	os.chdir(cwd)
		
	# add specified idps some
	local.update(idps)
	if not local:
		warnings.warn("No idps found")
		return None
	if sp_json.get('metadata') is None:
		sp_json['metadata'] = {}
	sp_json['metadata']['local'] = sorted(local)
	
	return None

# classes

class SAML2Plugin(_SAML2Plugin):
	pass
