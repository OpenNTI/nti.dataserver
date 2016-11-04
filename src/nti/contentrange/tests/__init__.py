#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import nti.contentrange

import nti.testing.base

class ConfiguringTestBase(nti.testing.base.SharedConfiguringTestBase):
	set_up_packages = (nti.contentrange,)
