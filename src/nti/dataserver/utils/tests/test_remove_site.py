#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that

import unittest

from zope import component
from zope import lifecycleevent

from zope.component.hooks import site as current_site

from zope.interface.interfaces import IComponents

from nti.app.site.hostpolicy import create_site

from nti.dataserver.tests import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users.users import User

from nti.dataserver.users.common import set_user_creation_site
from nti.dataserver.users.common import remove_user_creation_site

from nti.dataserver.users.utils import get_users_by_site

from nti.dataserver.utils.nti_site_ops import remove_sites

from nti.site.hostpolicy import get_host_site


class TestRemoveSite(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    SITES_TO_USERS = {'base_site': ['base_site_user1'],
                      'site_to_delete': ['site_to_delete_user1'],
                      'parent_site': ['parent_site_user1'],
                      'child_site1': ['child_site_user1'],
                      'child_site2': ['child_site_user2']}

    def create_site(self, name):
        try:
            create_site(name)
        except KeyError:
            pass
        return get_host_site(name)

    def _create_sites(self):
        """
        Create sites and structure, idempotently.
        """
        self.create_site('base_site')
        self.create_site('site_to_delete')
        parent_site = self.create_site('parent_site')
        with current_site(parent_site):
            self.create_site('child_site1')
            self.create_site('child_site2')

    def _create_users(self):
        """
        Create users, idempotently.
        """
        for site_name, site_users in self.SITES_TO_USERS.items():
            for site_user in site_users:
                try:
                    user = User.create_user(username=site_user,
                                            external_value={'email': u"%s@gmail.com" % site_user})
                except KeyError:
                    user = User.get_user(site_user)
                remove_user_creation_site(user)
                set_user_creation_site(user, site_name)
                lifecycleevent.modified(user)

    def _validate_sites(self, deleted_sites=()):
        """
        Validate sites exist (or not) and they have registered component
        utilities.
        """
        for site_name in self.SITES_TO_USERS:
            site_check = none if site_name in deleted_sites else not_none
            assert_that(get_host_site(site_name, safe=True), site_check(), site_name)
            site_components = component.queryUtility(IComponents, name=site_name)
            assert_that(site_components, site_check(), site_name)

    def _validate_users(self, deleted_sites=(), removed_user_creation_sites=False, deleted_users=False):
        """
        Validate users exist (or do not) and that the site user counts
        line up with expectations.
        """
        for site_name, site_users in self.SITES_TO_USERS.items():
            exists_check = not_none
            user_count = len(site_users)
            if site_name in deleted_sites:
                if deleted_users:
                    exists_check = none
                    user_count = 0
                elif removed_user_creation_sites:
                    user_count = 0

            for site_user in site_users:
                user = User.get_user(site_user)
                assert_that(user, exists_check(), (site_user, site_name))
            site_users = get_users_by_site(site_name)
            assert_that(site_users, has_length(user_count), site_name)
        assert_that(User.get_user('unaffiliated_user'), not_none())

    def _validate(self, deleted_sites=(), removed_user_creation_sites=False, deleted_users=False):
        self._validate_sites(deleted_sites)
        self._validate_users(deleted_sites, removed_user_creation_sites, deleted_users)

    @WithMockDSTrans
    def test_remove_sites(self):
        """
        Test removing sites, as well as associated users. This should not affect
        other sites or other users in other sites.
        """
        User.create_user(username=u'unaffiliated_user',
                         external_value={'email': u"ichigo@bleach.org"})

        def reset():
            self._create_sites()
            self._create_users()
            self._validate()
        reset()

        # Simple site deletion
        remove_sites(names=('site_to_delete',),
                     remove_entity_creation_sites=False,
                     commit=True,
                     remove_site_entities=False)
        self._validate(deleted_sites=('site_to_delete',),
                       deleted_users=False)
        reset()

        remove_sites(names=('site_to_delete',),
                     remove_entity_creation_sites=False,
                     commit=True,
                     remove_site_entities=True)
        self._validate(deleted_sites=('site_to_delete',),
                       deleted_users=True)
        reset()

        remove_sites(names=('site_to_delete',),
                     remove_entity_creation_sites=True,
                     commit=True,
                     remove_site_entities=False)
        self._validate(deleted_sites=('site_to_delete',),
                       removed_user_creation_sites=True,
                       deleted_users=False)
        reset()

        # Remove child sites with exclusion
        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=False,
                     commit=True,
                     remove_site_entities=True,
                     remove_only_child_sites=True,
                     excluded_sites=('child_site2',))
        self._validate(deleted_sites=('child_site1',), deleted_users=True)
        reset()

        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=True,
                     commit=True,
                     remove_site_entities=False,
                     remove_only_child_sites=True,
                     excluded_sites=('child_site2',))
        self._validate(deleted_sites=('child_site1',),
                       removed_user_creation_sites=True,
                       deleted_users=False)
        reset()

        # Remove all child sites
        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=False,
                     commit=True,
                     remove_site_entities=False,
                     remove_only_child_sites=True)
        self._validate(deleted_sites=('child_site1', 'child_site2'), deleted_users=False)
        reset()

        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=False,
                     remove_site_entities=True,
                     commit=True,
                     remove_only_child_sites=True)
        self._validate(deleted_sites=('child_site1', 'child_site2'), deleted_users=True)
        reset()

        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=True,
                     commit=True,
                     remove_site_entities=False,
                     remove_only_child_sites=True)
        self._validate(deleted_sites=('child_site1', 'child_site2'),
                       removed_user_creation_sites=True,
                       deleted_users=False)
        reset()

        # Remove site tree
        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=False,
                     remove_site_entities=False,
                     commit=True,
                     remove_child_sites=True)
        self._validate(deleted_sites=('parent_site', 'child_site1', 'child_site2'),
                       deleted_users=False)
        reset()

        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=False,
                     commit=True,
                     remove_site_entities=True,
                     remove_child_sites=True)
        self._validate(deleted_sites=('parent_site', 'child_site1', 'child_site2'),
                       deleted_users=True)
        reset()

        remove_sites(names=('parent_site',),
                     remove_entity_creation_sites=True,
                     commit=True,
                     remove_site_entities=False,
                     remove_child_sites=True)
        self._validate(deleted_sites=('parent_site', 'child_site1', 'child_site2'),
                       removed_user_creation_sites=True,
                       deleted_users=False)
        reset()

        # Remove multiple sites
        remove_sites(names=('parent_site', 'site_to_delete'),
                     remove_entity_creation_sites=False,
                     commit=True,
                     remove_site_entities=True,
                     remove_child_sites=True)
        self._validate(deleted_sites=('parent_site', 'child_site1', 'child_site2', 'site_to_delete'),
                       deleted_users=True)

        # Running the same operation again (without a test reset) should log and ignore
        remove_sites(names=('parent_site', 'site_to_delete'),
                     remove_entity_creation_sites=False,
                     commit=True,
                     remove_site_entities=True,
                     remove_child_sites=True)
        self._validate(deleted_sites=('parent_site', 'child_site1', 'child_site2', 'site_to_delete'),
                       deleted_users=True)
        reset()

        # The same command without commiting just logs
        remove_sites(names=('parent_site', 'site_to_delete'),
                     remove_entity_creation_sites=False,
                     commit=False,
                     remove_site_entities=True,
                     remove_child_sites=False)
        self._validate()
        reset()

        remove_sites(names=('parent_site', 'site_to_delete'),
                     remove_entity_creation_sites=False,
                     commit=False,
                     remove_site_entities=False,
                     remove_child_sites=True)
        self._validate()
