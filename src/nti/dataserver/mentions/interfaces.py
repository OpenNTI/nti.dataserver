#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.coremetadata.mentions.schema import Mention

from nti.schema.field import TupleFromObject
from nti.schema.field import UniqueIterable


class IPreviousMentions(interface.Interface):

    mentions = TupleFromObject(title=u"Mentioned entities",
                               value_type=Mention(min_length=1,
                                                  title=u"A single mention",
                                                  __name__=u'mentions'),
                               unique=True,
                               default=())

    notified_mentions = UniqueIterable(
        title=u"Notified Mentions",
        description=u"The set of mentioned entities that have already "
                    u"been notified for the associated object.",
        value_type=Mention(min_length=1,
                           title=u"A mentioned entity that has been notified.",
                           __name__=u'mentions'),
        default=set())

