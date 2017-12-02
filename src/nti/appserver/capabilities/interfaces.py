#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interface definitions relating to capabilities.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.security.interfaces import IPermission

from nti.appserver import MessageFactory as _

from nti.schema.field import DecodingValidTextLine

# A :class:`zope.schema.interfaces.IVocabularyTokenized` vocabulary
# will be available as a registered vocabulary under this name
VOCAB_NAME = 'nti.appserver.capabilities.vocabulary'


class ICapability(IPermission):
    """
    A capability is a type of umbrella permission. Although it is an
    actual permission, it is not typically used directly in an ACL; rather,
    it is checked and applied at a higher level. A single capability
    may imply several other permissions or it may not directly imply any.

    Capabilities and permissions share the same namespace, so be careful
    to avoid collisions.
    """

    id = DecodingValidTextLine(
        title=_(u"Id"),
        description=_(u"Id as which this permission will be known and used."),
        readonly=True,
        required=True)
