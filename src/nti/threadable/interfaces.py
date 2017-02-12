#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.schema.field import Object
from nti.schema.field import ListOrTuple
from nti.schema.field import UniqueIterable


class IThreadable(interface.Interface):
    """
    Something which can be used in an email-like threaded fashion.

    .. note:: All the objects should be IThreadable, but it is not possible
            to put that in a constraint without having infinite recursion
            problems.
    """

    inReplyTo = Object(interface.Interface,
                       title="""The object to which this object is directly a reply.""",
                       required=False)

    references = ListOrTuple(title="""A sequence of objects this object transiently references, in order up to the root""",
                             value_type=Object(interface.Interface, 
                                               title="A reference"),
                             default=())

    replies = UniqueIterable(title="All the direct replies of this object",
                             description="This property will be automatically maintained.",
                             value_type=Object(interface.Interface, title="A reply"))
    replies.setTaggedValue('_ext_excluded_out', True)  # Internal use only

    referents = UniqueIterable(title="All the direct and indirect replies to this object",
                               description="This property will be automatically maintained.",
                               value_type=Object(interface.Interface, title="A in/direct reply"))
    referents.setTaggedValue('_ext_excluded_out', True)  # Internal use only


class IWeakThreadable(IThreadable):
    """
    Just like :class:`IThreadable`, except with the expectation that
    the items in the reply chain are only weakly referenced and that
    they are automatically cleaned up (after some time) when deleted. Thus,
    it is not necessarily clear when a ``None`` value for ``inReplyTo``
    means the item has never had a reply, or the reply has been deleted.
    """


class IInspectableWeakThreadable(IWeakThreadable):
    """
    A weakly threaded object that provides information about its
    historical participation in a thread.
    """

    def isOrWasChildInThread():
        """
        Return a boolean object indicating if this object is or was
        ever part of a thread chain. If this returns a true value, it
        implies that at some point ``inRelpyTo`` was non-None.
        """
