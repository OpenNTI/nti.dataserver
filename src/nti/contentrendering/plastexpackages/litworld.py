#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Base

class litclubsession(Base.chapter):
    pass

class litclubsessionsection(Base.section):
    pass

class litclubsection(Base.subsection):
    pass

class litclubsubsection(Base.subsubsection):
    pass

class litclubwelcomesection(Base.section):
    pass

class litclubhellosongsubsection(Base.subsubsection):
    pass

class litclubcheckinsubsection(Base.subsubsection):
    pass

class litclubcommunitysection(Base.section):
    pass

class litclubreadaloudsection(Base.section):
    pass

class litclubdiscussionsubsection(Base.subsubsection):
    pass

class litclubcoresection(Base.section):
    pass

class litclubindereadingsection(Base.subsection):
    pass

class litclubwrapupsection(Base.section):
    pass

class litclubpraisesubsection(Base.subsubsection):
    pass

class litclubgoodbyesongsubsection(Base.subsubsection):
    pass
