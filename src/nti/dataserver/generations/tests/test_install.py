#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import contains
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

import fudge

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.component.hooks import site

from zope.container.contained import Contained

from zope.event import notify

from zope.lifecycleevent import ObjectModifiedEvent

from zc.intid.interfaces import IIntIds

from persistent import Persistent

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans


class PersistentContained(Contained, Persistent):
    pass


class TestInstall(mock_dataserver.DataserverLayerTest):

    @mock_dataserver.WithMockDSTrans
    def test_install_creates_intid_utility_and_contained_objects_are_registered(self):
        intids = component.getUtility(IIntIds)
        assert_that(intids, verifiably_provides(IIntIds))

        ds = self.ds

        contained_obj = PersistentContained()
        ds.root['NewKey'] = contained_obj

        assert_that(contained_obj, has_property('__parent__', ds.root))
        assert_that(contained_obj, has_property('__name__', 'NewKey'))

        assert_that(intids.getId(contained_obj), is_not(none()))
        assert_that(intids.getObject(intids.getId(contained_obj)), 
                    is_(contained_obj))

        del ds.root['NewKey']
        assert_that(intids.queryId(contained_obj), is_(none()))

        everyone = ds.users_folder['Everyone']
        assert_that(intids.getObject(intids.getId(everyone)), is_(everyone))

    @mock_dataserver.WithMockDS
    def test_installed_catalog(self):

        with mock_db_trans() as conn:
            context = fudge.Fake().has_attr(connection=conn)
            ExampleDatabaseInitializer(max_test_users=0, skip_passwords=True).install(context)

        with mock_db_trans() as conn:
            ds_folder = context.connection.root()['nti.dataserver']

            with site(ds_folder):
                jason = ds_folder['users']['jason.madden']
                ent_catalog = component.getUtility(ICatalog, 
                                                   name='nti.dataserver.++etc++entity-catalog')

                results = list(ent_catalog.searchResults(email=('Jason.madden', 'jason.madden@nextthought.com')))
                assert_that(results, contains(jason))

                results = list(ent_catalog.searchResults(realname=('JASON MADDEN', 'JASON MADDEN')))
                assert_that(results, contains(jason))

                results = list(ent_catalog.searchResults(topics='opt_in_email_communication'))
                assert_that(results, has_length(0))

                # Changing the profile and notifying updates the index
                IUserProfile(jason).opt_in_email_communication = True
                notify(ObjectModifiedEvent(jason))

                results = list(ent_catalog.searchResults(topics='opt_in_email_communication'))
                assert_that(results, contains(jason))

                # Changing the profile and updating all indexes updates
                IUserProfile(jason).opt_in_email_communication = False
                ent_catalog.updateIndexes()
                results = list(ent_catalog.searchResults(topics='opt_in_email_communication'))
                assert_that(results, has_length(0))

                # Now deleting him clears him out of the catalog
                del ds_folder['users']['jason.madden']
                results = list(ent_catalog.searchResults(topics='opt_in_email_communication'))
                assert_that(results, has_length(0))

                results = list(ent_catalog.searchResults(email=('Jason.madden@nextthought.com', 'jason.madden')))
                assert_that(results, has_length(0))
