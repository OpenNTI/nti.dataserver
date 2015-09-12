#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

try:
    from zodbpickle.fastpickle import Unpickler
except ImportError:  # PyPy?
    from cPickle import Unpickler

from cStringIO import StringIO

_has_noload = True
try:
    Unpickler(StringIO(b'')).noload
except AttributeError:
    _has_noload = False

_all_missed_classes = set()

from zope.app.broken.broken import Broken

import ZODB.broken

def _make_find_global():
    Broken_ = Broken  # make it local for speed
    _find_global = ZODB.broken.find_global

    def type_(name, bases, tdict):
        logger.warn("Broken class reference to %s", tdict['__module__'] + '.' + name)
        _all_missed_classes.add(tdict['__module__'] + '.' + name)
        cls = type(name, bases, tdict)
        return cls

    def _the_find_global(modulename, globalname):
        return _find_global(modulename, globalname, Broken_, type_)

    return _the_find_global

find_global = _make_find_global()

def getrefs(p, storage_name, ignore):
    "Return a sequence of (db_name, oid) pairs"
    refs = []
    u = Unpickler(StringIO(p))
    u.persistent_load = refs  # Just append to this list
    u.find_global = find_global
    if _has_noload:
        b1 = u.noload()  # Once for the class/type reference
    else:
        # if we don't have noload, we also probably don't support the
        # optimized case of appending to the list, so we
        # need to give it a callable
        u.persistent_load = refs.append
        # PyPy calls find_global 'find_class'; is that not a standard
        # attribute?
        u.find_class = find_global
        b1 = u.load()
    try:
        b2 = u.load()  # again for the state
    except AttributeError as e:
        if e.message != "'DATETIME' object has no attribute 'numtype'":
            # Ancient whoosh error
            raise

    for ref in refs:
        if isinstance(ref, tuple):
            # (oid, class meta data)
            yield storage_name, ref[0]
        elif isinstance(ref, bytes):
            # oid
            yield storage_name, ref
        elif not ref:
            print("Empty reference?", ref, refs, b1, b2)
            raise ValueError("Unexpected empty reference")
        elif ref:
            assert isinstance(ref, list)
            # [reference type, args] or [oid]
            if len(ref) == 1:
                print("Legacy persistent weak ref")
                yield storage_name, ref
                continue

            # Args is always a tuple, but depending on
            # the value of the reference type, the order
            # may be different. Types n and m are in the right
            # order, type w is different
            kind, ref = ref

            if kind in (b'n', b'm'):
                if ref[0] not in ignore:
                    yield ref[:2]
            elif kind == b'w':
                if len(ref) == 1:  # oid in this db
                    yield storage_name, ref[0]
                elif len(ref) == 2:  # oid in other db
                    yield ref[1], ref[0]
                else:
                    raise ValueError('Unknown weak ref type', ref)
            else:
                raise ValueError('Unknown persistent ref', kind, ref)

import zope.interface.declarations

def Provides(*interfaces):
    """
    Due to a bug in nti.mimetype, some very old objects
    may have invalid values for __provides__. We fix this
    by ignoring them, since the only contain class objects
    """
    return zope.interface.declarations.ProvidesClass(interfaces[0])

def configure():
    """
    Some pickles in the wild (notably ACLs) need ZCA to be set up
    in order to successfully load. The result of failing to do this
    is a TypeError.
    """

    from zope.component.hooks import setHooks
    setHooks()
    from nti.dataserver.utils import _configure
    _configure(set_up_packages=('nti.dataserver',))


    # Similarly, some pickles to site components exist in the database
    # but we don't want to actually try to load all the sites, so replace
    # the component lookup with simply returning a new registry
    # (they pickle as a call to the global function BC with args (parent, name))
    # which is what the constructor takes
    import z3c.baseregistry.baseregistry
    z3c.baseregistry.baseregistry.BC = z3c.baseregistry.baseregistry.BaseComponents

    # Some pickles may also refer to a library
    from zope import component
    from nti.contentlibrary.library import EmptyLibrary
    from nti.contentlibrary.interfaces import IContentPackageLibrary
    component.provideUtility(EmptyLibrary(), IContentPackageLibrary)

def fixrefs():
    import zc.zodbdgc
    zc.zodbdgc.getrefs = getrefs
    configure()
    # Only *after* we're configured
    zope.interface.declarations.Provides = Provides

def report():
    if _all_missed_classes:
        logger.warn("The following classes are missing: %s", _all_missed_classes)


import sys

from pkg_resources import load_entry_point

def main():
    fixrefs()

    # Not a threaded process, no need to check for switches
    sys.setcheckinterval(100000)
    try:
        ec = load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-gc')()
    finally:
        report()
    sys.exit(ec)

if __name__ == '__main__':
    main()
