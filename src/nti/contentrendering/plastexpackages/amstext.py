#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import re, sys

from zope import interface

from nti.contentrendering import plastexids
from nti.contentrendering.resources import interfaces as res_interfaces

from plasTeX import Base

# SAJ: Partial support for the amstext package.

class text(Base.Command):
	pass
