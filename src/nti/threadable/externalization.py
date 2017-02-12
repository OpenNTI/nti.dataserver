#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

from nti.externalization.oids import to_external_ntiid_oid

from nti.wref.interfaces import IWeakRefToMissing


class ThreadableExternalizableMixin(object):
    """
    Works with :class:`ThreadableMixin` with support for externalizing to and from a dictionary.
    Note that subclasses must extend something that is itself externalizable, and use
    cooperative super-class to be able to put this in the right order.

    The subclass can customize the way that references are externalized with the value
    of the :attr:`_ext_write_missing_references` attribute, as well as the methods
    :meth:`_ext_ref` and :meth:`_ext_can_update_threads`.

    The subclass must define the `_ext_replacement` function as the object being externalized.
    """

    # Cause these to be resolved automatically
    __external_oids__ = ['inReplyTo', 'references']

    #: If True (the default) then when objects that we are replies to or that
    #: we reference are deleted, we will write out placeholder missing values
    #: for them. Otherwise, there will be a null value or gap. 
    #: See :const:`nti.ntiids.ntiids.TYPE_MISSING`
    _ext_write_missing_references = True

    def toExternalObject(self, mergeFrom=None, **kwargs):
        extDict = super(ThreadableExternalizableMixin, 
                        self).toExternalObject(mergeFrom=mergeFrom, **kwargs)
        if self._ext_can_write_threads():
            assert isinstance(extDict, collections.Mapping)
            context = self._ext_replacement()
            extDict['inReplyTo'] = self._ext_ref(context.inReplyTo,
                                                 context._inReplyTo)
            extDict['references'] = [
                self._ext_ref(ref(), ref) for ref in context._references
            ]
        return extDict

    def _ext_ref(self, obj, ref):
        """
        Produce a string value for the object we reference (or are a reply to).
        By default, this will distinguish the three cases of never having been set,
        having been set and referring to an extant object, and having been set and
        now referring to an object that is deleted.
        """
        if obj is not None:
            result = to_external_ntiid_oid(obj)
            if not result:
                __traceback_info__ = self, obj, ref
                raise ValueError("Unable to create external reference", obj)
            return result

        # No object. Did we have a reference at one time?
        if ref is not None and self._ext_write_missing_references:
            # Yes. Can we write something out?
            missing_ref = IWeakRefToMissing(ref, None)
            if missing_ref is not None:
                return missing_ref.make_missing_ntiid() 
            return None

    def updateFromExternalObject(self, parsed, **kwargs):
        assert isinstance(parsed, collections.Mapping)
        inReplyTo = parsed.pop('inReplyTo', None)
        references = parsed.pop('references', ())
        super(ThreadableExternalizableMixin, 
              self).updateFromExternalObject(parsed, **kwargs)

        if self._ext_can_update_threads():
            context = self._ext_replacement()
            context.inReplyTo = inReplyTo
            context.clearReferences()
            for ref in references or ():
                context.addReference(ref)

    def _ext_can_update_threads(self):
        """
        By default, once this object has been created and the thread-related values
        have been set, they cannot be changed by sending external data.

        (This depends on the context object being
        :class:`persistent.Persistent`, or otherwise defining the
        ``_p_mtime`` property.)
        """
        mod_time = getattr(self._ext_replacement(), '_p_mtime', None)
        return not mod_time

    def _ext_can_write_threads(self):
        """
        Called to determine if we should even write the threadable
        properties to the dictionary. Sometimes subclasses may not want to.
        """
        return True
