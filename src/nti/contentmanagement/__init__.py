#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
content management module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces

from nti.ntiids import ntiids

def get_ntiid_path(ntiid, library=None, registry=component):
    result = ()
    library = registry.queryUtility(lib_interfaces.IContentPackageLibrary) if library is None else library
    if library and ntiid:
        paths = library.pathToNTIID(ntiid)
        result = tuple([p.ntiid for p in paths]) if paths else ()
    return result

def get_collection_root(ntiid, library=None, registry=component):
    library = registry.queryUtility(lib_interfaces.IContentPackageLibrary) if library is None else library
    paths = library.pathToNTIID(ntiid) if library else None
    return paths[0] if paths else None

def get_collection_root_ntiid(ntiid, library=None, registry=component):
    croot = get_collection_root(ntiid, library, registry)
    result = croot.ntiid.lower() if croot else None
    return result
