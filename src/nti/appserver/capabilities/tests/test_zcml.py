#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: No value for argument,too many methods,accessing protected members
# pylint: disable=E1120,R0904,W0212

from hamcrest import is_in
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from zope import component

from zope.schema import vocabulary

from nti.appserver.capabilities.interfaces import VOCAB_NAME
from nti.appserver.capabilities.interfaces import ICapability

from nti.appserver.capabilities.vocabulary import CapabilityNameVocabulary
from nti.appserver.capabilities.vocabulary import CapabilityUtilityVocabulary
from nti.appserver.capabilities.vocabulary import CapabilityNameTokenVocabulary

from nti.testing.base import ConfiguringTestBase


class TestZcml(ConfiguringTestBase):

    def test_default_registrations(self):
        packages = (('capabilities.zcml', 'nti.appserver.capabilities'),)
        self.configure_packages(set_up_packages=packages)
        self._check_cap_present()

    def _check_cap_present(self, cap_name='nti.platform.p2p.chat'):
        component.getUtility(ICapability, cap_name)

        assert_that(cap_name, is_in(CapabilityNameTokenVocabulary()))
        assert_that(cap_name, is_in(CapabilityNameVocabulary(None)))

        assert_that(CapabilityUtilityVocabulary(None).getTermByToken(cap_name),
                    has_property('token', cap_name))

    def test_site_registrations(self):
        """
        Can we add new registrations in a sub-site?
        """
        packages = ('nti.appserver.capabilities',)
        self.configure_packages(set_up_packages=packages)
        zcml_string = u"""
        <configure xmlns="http://namespaces.zope.org/zope"
	               xmlns:zcml="http://namespaces.zope.org/zcml"
	               xmlns:cap="http://nextthought.com/ntp/capabilities"
	               i18n_domain='nti.dataserver'>

	        <include package="zope.component" />
	        <include package="z3c.baseregistry" file="meta.zcml" />

	        <cap:capability
	            id='nti.only_in_mathcounts'
	            title="only_in_mathcounts" />

        </configure>
        """
        self.configure_string(zcml_string)
        self._check_cap_present()  # the defaults are there

        cap_name = 'nti.only_in_mathcounts'
        assert_that(cap_name,
                    is_in(vocabulary.getVocabularyRegistry().get(None, VOCAB_NAME)))

        # Now, in the sub site, they are bath present
        self._check_cap_present()
        self._check_cap_present(cap_name)
