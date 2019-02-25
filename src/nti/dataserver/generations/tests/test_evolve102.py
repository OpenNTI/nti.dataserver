#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

import fudge

from z3c.baseregistry.baseregistry import BaseComponents

from zope import component, interface

from zope.component import globalSiteManager as BASE

from zope.interface.interfaces import IComponents

from zope.intid.interfaces import IIntIds

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.policies.site_policies import AdultCommunitySitePolicyEventListener

from nti.appserver.policies.sites import BASEADULT

from nti.coremetadata.interfaces import IX_SITE

from nti.dataserver.interfaces import ISiteCommunity

from nti.dataserver.users import Community
from nti.dataserver.users import get_entity_catalog

from nti.dataserver.users.common import entity_creation_sitename

from nti.dataserver.generations.evolve102 import do_evolve

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.site.hostpolicy import synchronize_host_policies


ALPHA = BaseComponents(BASEADULT,
                       name='alpha.nextthought.com',
                       bases=(BASEADULT,))

ALPHA_CHILD = BaseComponents(ALPHA,
                             name='alpha-child.nextthought.com',
                             bases=(ALPHA,))

SITES = (ALPHA,
         ALPHA_CHILD)

class MockSitePolicyUserEventListener(AdultCommunitySitePolicyEventListener):

    COM_USERNAME = 'alpha.nextthought.com'


class TestEvolve102(mock_dataserver.DataserverLayerTest):

    def setUp(self):
        super(TestEvolve102, self).setUp()
        for bc in SITES:
            bc.__init__(bc.__parent__, name=bc.__name__, bases=bc.__bases__)
            BASE.registerUtility(bc, name=bc.__name__, provided=IComponents)
        ALPHA.registerUtility(MockSitePolicyUserEventListener(), ISitePolicyUserEventListener)

    def tearDown(self):
        for bc in SITES:
            BASE.unregisterUtility(bc, name=bc.__name__, provided=IComponents)
        ALPHA.unregisterUtility(MockSitePolicyUserEventListener(), ISitePolicyUserEventListener)
        super(TestEvolve102, self).tearDown()

    @mock_dataserver.WithMockDS
    def test_do_evolve(self):

        with mock_db_trans(self.ds) as conn:
            context = fudge.Fake().has_attr(connection=conn)
            synchronize_host_policies()

            # Create a site community
            intids = component.getUtility(IIntIds)
            alpha_site_policy = ALPHA.queryUtility(ISitePolicyUserEventListener)
            alpha_com_username = alpha_site_policy.COM_USERNAME
            alpha_site_community = Community.create_community(username=alpha_com_username)
            interface.alsoProvides(alpha_site_community, ISiteCommunity)

            ac_policy = ALPHA_CHILD.queryUtility(ISitePolicyUserEventListener)
            ac_site_comm = Community.get_community(ac_policy.COM_USERNAME)
            assert_that(ac_site_comm, is_(alpha_site_community))

            # Assert existing behavior of no creation site
            creation_sitename = entity_creation_sitename(alpha_site_community)
            assert_that(creation_sitename, is_(none()))

            doc_id = intids.getId(alpha_site_community)

            # Assert existing behavior of no indexed creation site
            catalog = get_entity_catalog()
            site_idx = catalog[IX_SITE]
            idx_creation_sitename = site_idx.values_to_documents.get(doc_id)
            assert_that(idx_creation_sitename, is_(none()))

            do_evolve(context)

            # Assert we now have a creation site
            creation_sitename = entity_creation_sitename(alpha_site_community)
            assert_that(creation_sitename, is_('alpha.nextthought.com'))

            # Assert the creation site is indexed
            catalog = get_entity_catalog()
            site_idx = catalog[IX_SITE]
            idx_creation_sitename = site_idx.documents_to_values.get(doc_id)
            assert_that(idx_creation_sitename, is_('alpha.nextthought.com'))
