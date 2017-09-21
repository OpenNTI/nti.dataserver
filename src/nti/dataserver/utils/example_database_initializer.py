#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility to initialize an environment

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from zope import component
from zope import interface

from zope.component.hooks import site
from zope.component.hooks import getSite

import zope.generations.generations

from zope.generations.interfaces import IInstallableSchemaManager

from zc.intid.interfaces import IIntIds

from nti.dataserver.users.communities import Community

from nti.dataserver.users.friends_lists import FriendsList

from nti.dataserver.users.users import User

from nti.dataserver.users.interfaces import IRecreatableUser

logger = __import__('logging').getLogger(__name__)


def exampleDatabaseInitializerSubscriber(event):
    """
    Subscriber to the :class:`zope.processlifetime.IDatabaseOpenedEvent`.
    If the example database has previously been installed in this
    database, then we provide the schema manager to continue
    its evolution (since the schema manager is optional).
    """
    with event.database.transaction() as conn:
        root = conn.root()
        generations = root.get(zope.generations.generations.generations_key)
        if generations is not None and 'nti.dataserver-example' in generations:
            component.provideUtility(ExampleDatabaseInitializer(),
                                     name='nti.dataserver-example')


@interface.implementer(IInstallableSchemaManager)
class ExampleDatabaseInitializer(object):

    generation = 8
    max_test_users = 101
    skip_passwords = False
    minimum_generation = 8
    nti_testers = "NTI_TESTERS"

    def __init__(self, *unused_args, **kwargs):
        """
        :param int max_test_users: The number of test users to create.
        """
        for k in ('max_test_users', 'skip_passwords'):
            if k in kwargs:
                setattr(self, k, kwargs.pop(k))

    def _make_usernames(self):
        """
        :return: An iterable of two-tuples of (userid, realname). email will be used
                as userid
        """
        USERS = [('admin@nextthought.com', 'Admin'),
                 ('rusczyk@artofproblemsolving.com', 'Richard Rusczyk'),  # Aops
                 ('patrick@artofproblemsolving.com', 'Dave Patrick')]

        # Add the ok people
        for uid in ('aaron.eskam', 'andrew.ligon', 'carlos.sanchez',
                    'chris.utz', 'greg.higgins', 'jason.madden',
                    'jeff.muehring', 'jonathan.grimes', 'josh.zuech', 'julie.zhu',
                    'kaley.white', 'ken.parker',
                    'ray.hatfield', 'sean.jones', 'mary.enos',
                    'zachary.roux', 'bobby.hagen',
                    'austin.graham', 'ethan.berman', 'admin'):
            USERS.append((uid, uid.replace('.', ' ').title(),
                          uid + '@nextthought.com'))

        # Add test users
        max_test_users = self.max_test_users
        for x in range(1, max_test_users):
            uid = u'test.user.%s' % x
            name = u'TestUser-%s' % x
            USERS.append((uid, name))

        # Some busey people
        USERS.append(('philip@buseygroup.com', 'Philip Busey Jr'))
        USERS.append(('phil@buseygroup.com', 'Phil Busey'))
        USERS.append(('cathy@buseygroup.com', 'Cathy Busey'))
        USERS.append(('clay@buseygroup.com', 'Clay Stanley'))
        USERS.append(('brian@buseygroup.com', 'Brian Busey'))

        # Example people. Notice that we give them @nextthought.com
        # emails so we can control the gravatars
        for uid in ('luke.skywalker', 'amelia.earhart', 'charles.lindbergh',
                    ('darth.vader', 'Lord Vader'), ('jeanluc.picard', 'Captain Picard'),
                    ('obiwan.kenobi', 'General Kenobi')):
            uname = uid if isinstance(uid, basestring) else uid[0]
            if isinstance(uid, six.string_types):
                rname = uid.replace('.', ' ').title()
            else:
                rname = uid[1]
            USERS.append((uname, rname))

        # Demo accounts
        USERS.append(('jessica.janko', 'Jessica Janko'))
        USERS.append(('suzie.stewart', 'Suzie Stewart'))

        return USERS

    def _make_communities(self, ds):
        # Communities
        aopsCommunity = Community.create_entity(ds, 
                                                username=u"ArtOfProblemSolving")
        aopsCommunity.realname = aopsCommunity.username
        aopsCommunity.alias = u'AOPS'

        ntiCommunity = Community.create_entity(ds, username=u'NextThought')
        ntiCommunity.realname = ntiCommunity.username
        ntiCommunity.alias = u'NTI'

        mathcountsCommunity = Community.create_entity(ds, 
                                                      username=u'MathCounts')
        mathcountsCommunity.realname = mathcountsCommunity.username
        mathcountsCommunity.alias = u'MathCounts'

        testUsersCommunity = Community.create_entity(ds, 
                                                     username=self.nti_testers)
        testUsersCommunity.realname = testUsersCommunity.username
        testUsersCommunity.alias = self.nti_testers

        return (aopsCommunity, ntiCommunity, mathcountsCommunity, testUsersCommunity)

    def _add_friendslists_to_user(self, for_user):
        if for_user.username != 'jason.madden':
            return

        fl = FriendsList(u'Pilots')
        fl.creator = for_user
        fl.addFriend('luke.skywalker')
        fl.addFriend('amelia.earhart')
        fl.addFriend('charles.lindbergh')
        fl.containerId = 'FriendsLists'
        for_user.addContainedObject(fl)

        fl = FriendsList(u'CommandAndControl')
        fl.creator = for_user
        fl.addFriend('darth.vader')
        fl.addFriend('jeanluc.picard')
        fl.addFriend('obiwan.kenobi')
        fl.containerId = 'FriendsLists'
        for_user.addContainedObject(fl)

        fl = FriendsList(u'NTI_OK')
        fl.creator = for_user
        fl.addFriend('chris.utz')
        fl.addFriend('carlos.sanchez')
        fl.addFriend('jeff.muehring')
        fl.addFriend('ken.parker')
        fl.containerId = 'FriendsLists'
        for_user.addContainedObject(fl)

    def _add_test_user_friendlist(self, for_user):
        fl = FriendsList(u'FL-' + self.nti_testers)
        for x in range(1, self.max_test_users):
            uid = u'test.user.%s@nextthought.com' % x
            if uid != for_user.username:
                fl.addFriend(uid)
        for_user.addContainedObject(fl)

    def install(self, context):

        conn = context.connection
        root = conn.root()['nti.dataserver']
        # If we're in tests, we probably already have a site setup
        if        getSite() \
            and getSite().getSiteManager() \
            and getSite().getSiteManager().queryUtility(IIntIds):
            self._install_in_site(context, conn, root)
        else:
            with site(root):
                self._install_in_site(context, conn, root)

    def _install_in_site(self, unused_context, unused_conn, root):
        # ONLY_NEW = '--only-new' in sys.argv
        # if ONLY_NEW:
        #     def add_user( u ):
        #         if u.username not in root['users']:
        #             root['users'][u.username] = u
        # else:
        def register_user(u):
            # Because we're not in that site, we need to make sure the events
            # go to the right place
            utility = component.getUtility(IIntIds)
            _id = utility.register(u)
            # print( u, _id, utility, id(u) )
            assert utility.getObject(_id) is u

        def add_user(u):
            assert u.__parent__ is root['users']
            root['users'][u.username] = u
            register_user(u)

        class mock_dataserver(object):
            pass
        mock_dataserver.root = root
        mock_dataserver.shards = root['shards']
        communities = self._make_communities(mock_dataserver)

        USERS = self._make_usernames()

        def create_add_user(user_tuple):
            uname = user_tuple[0]
            is_test_user = uname.startswith('test.user.')
            password = user_tuple[1].replace(' ', '.').lower()
            if is_test_user or len(password) < 6:
                password = u'temp001'
            if self.skip_passwords:
                # this can speed up creation a lot, the encrpytion is slow.
                # This matters for test cases.
                password = None

            args = {'username': six.text_type(uname), 
                    'password': six.text_type(password) if password else None,
                    'dataserver': mock_dataserver}
            ext_value = {}
            ext_value['realname'] = six.text_type(user_tuple[1])
            email = uname if len(user_tuple) < 3 else user_tuple[2]
            if '@' in email:
                ext_value['email'] = six.text_type(email)
            else:
                ext_value['email'] = email + u'@nti.com'
            if not is_test_user:
                ext_value['alias'] = six.text_type(user_tuple[1].split()[0])
            else:
                ext_value['alias'] =  six.text_type(user_tuple[1])
            args['external_value'] = ext_value
            user = User.create_user(**args)
            interface.alsoProvides(user, IRecreatableUser)
            register_user(user)

            for c in communities:
                if     (c.username == self.nti_testers and is_test_user) \
                    or (c.username != self.nti_testers and not is_test_user):
                    user.record_dynamic_membership(c)
                    user.follow(c)

            if not is_test_user:
                self._add_friendslists_to_user(user)

        map(create_add_user, USERS)

    def evolve(self, context, unused_generation):
        conn = context.connection
        root = conn.root()
        root = root['nti.dataserver']

        # Add a missing community, if needed
        mathcountsCommunity = Community(u'MathCounts')
        mathcountsCommunity.realname = mathcountsCommunity.username
        mathcountsCommunity.alias = u'MathCounts'
        if mathcountsCommunity.username not in root['users']:
            logger.info("Creating MathCounts community")
            root['users'][mathcountsCommunity.username] = mathcountsCommunity
