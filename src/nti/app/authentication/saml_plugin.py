#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import warnings
from glob import glob
from io import BytesIO

import simplejson

try:
    from saml2.config import SPConfig
    from saml2.client import Saml2Client
    from saml2.sigver import SigverError
    from saml2.s2repoze.plugins.sp import SAML2Plugin as _SAML2Plugin
except ImportError:  # pypy
    _SAML2Plugin = object

from zope import component

from nti.app.saml.client import BasicSAMLClient

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

DEFAULT_SP_JSON = 'sp.json'

logger = __import__('logging').getLogger(__name__)


# functions


def normalize_path(path):
    path = os.path.expandvars(path) if path else path
    path = os.path.expanduser(path) if path else path
    path = os.path.realpath(os.path.normpath(path)) if path else path
    return path


def find_xmlsec_path():
    xml_sec_dirs = ("/opt/local/bin", "/usr/local/bin", "/usr/bin")
    try:
        from saml2.sigver import get_xmlsec_binary
        result = get_xmlsec_binary(xml_sec_dirs)
    except (Exception, SigverError):  # pylint: disable=broad-except
        warnings.warn("xmlsec1 not found")
        result = None
    return result


def etc_saml_dir(path=None):
    if not path:
        path = os.environ.get('DATASERVER_SAML_DIR')
        if not path:
            ds = os.environ.get('DATASERVER_DIR')
            path = os.path.join(ds, 'etc/saml') if ds else None
    path = normalize_path(path)
    return path


def find_sp_file(path=None, config_name=DEFAULT_SP_JSON):
    path = etc_saml_dir(path)
    path = os.path.join(path, config_name) if path else path
    if path and os.path.exists(path):
        return path
    return None


def find_idp_files(path=None):
    path = etc_saml_dir(path)
    result = glob(os.path.join(path, 'idp*.xml')) if path else ()
    return result


def make_saml_client(path=None,
                     sp_config_name=DEFAULT_SP_JSON,
                     identity_cache="",
                     virtual_organization="",
                     client_factory=BasicSAMLClient):
    # find config files
    sp = find_sp_file(path, sp_config_name)
    idps = find_idp_files(path)

    # no service provider
    if not sp:
        return None

    # check service provider
    with open(sp) as fp:
        sp_json = simplejson.load(fp, "UTF-8")

    path = path or os.environ.get('DATASERVER_DIR')
    path = normalize_path(path)

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
        local = set(normalize_path(x)
                    for x in local if os.path.exists(normalize_path(x)))
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
        return client_factory(conf, scl, "", "", "")
    finally:
        os.chdir(cwd)


def make_plugin(path=None,
                wayf="",
                cache="",
                discovery="",
                sid_store="",
                identity_cache="",
                idp_query_param="",
                virtual_organization="",
                remember_name=str("auth_tkt")):
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

    path = path or os.environ.get('DATASERVER_DIR')
    path = normalize_path(path)

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
        local = set(normalize_path(x)
                    for x in local if os.path.exists(normalize_path(x)))
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

    def _wsgi_input(self, environ):
        try:
            environ['wsgi.input'].seek(0)  # allow reading
            wsgi_input = environ['wsgi.input'].read()  # copy
            return wsgi_input or ''
        except Exception:  # pylint: disable=broad-except
            return ''

    def identify(self, environ):
        # allow SAML2Plugin to consume input
        wsgi_input = self._wsgi_input(environ)
        environ['wsgi.input'] = BytesIO(wsgi_input)  # save
        try:
            result = _SAML2Plugin.identify(self, environ)
            result = None if not result else result
        finally:
            # restore
            environ['wsgi.input'] = BytesIO(wsgi_input)
        return result
