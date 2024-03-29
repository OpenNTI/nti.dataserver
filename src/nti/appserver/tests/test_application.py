#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_value
from hamcrest import less_than
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import starts_with
from hamcrest import greater_than
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import contains_string
from hamcrest import contains_inanyorder
from hamcrest import greater_than_or_equal_to
does_not = is_not

from nose.tools import assert_raises

from nti.contentlibrary.filesystem import StaticFilesystemLibrary as Library

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

from nti.app.testing.application_webtest import AppCreatingLayerHelper
from nti.app.testing.application_webtest import AppTestBaseMixin

from nti.app.testing.layers import PyramidLayerMixin

from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.testing.matchers import is_empty, validly_provides
from nti.testing.time import time_monotonically_increases

import unittest

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Moved to application_webtest",
	"nti.app.testing.application_webtest",
	"SharedApplicationTestBase" )

zope.deferredimport.deprecatedFrom(
	"Import directly",
	"nti.appserver.application",
	"createApplication" )
zope.deferredimport.deprecatedFrom(
	"Moved to application_webtest",
	"nti.app.testing.base",
	"ConfiguringTestBase",
	"SharedConfiguringTestBase")

import time
import base64
import datetime

from six.moves import urllib_parse

import simplejson as json

import webob.datetime_utils

from persistent import Persistent

from zope import component
from zope import interface

from zope.keyreference.interfaces import IKeyReference

import nti.appserver._util

from nti.contentrange import contentrange

from nti.coremetadata.mixins import ZContainedMixin

from nti.dataserver import contenttypes

from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver import users

from nti.dataserver.generations.install import ADMIN_USERNAME

from nti.dataserver.users.interfaces import IAuthToken
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.tokens import UserToken

from nti.dataserver.users.user_profile import Education
from nti.dataserver.users.user_profile import ProfessionalPosition

from nti.externalization import to_external_object

from nti.externalization.representation import to_json_representation

from nti.links import links

from nti.ntiids import ntiids

from nti.ntiids.oids import to_external_ntiid_oid

from nti.dataserver.tests import mock_dataserver


@interface.implementer(IKeyReference) # IF we don't, we won't get intids
class ContainedExternal(ZContainedMixin):

	def __str__( self ):
		if '_str' in self.__dict__:
			return self._str
		return "<%s %s>" % (self.__class__.__name__, self.to_container_key())

	def toExternalObject( self, **unused_kwargs ):
		return str(self)
	def to_container_key(self):
		return to_external_ntiid_oid(self, default_oid=str(id(self)))

class PersistentContainedExternal(ContainedExternal,Persistent):
	pass

from nti.app.testing.application_webtest import NonDevmodeApplicationTestLayer
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.application_webtest import NonDevmodeApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges

from nti.app.testing.webtest import TestApp

class NonDevmodeButAnySiteApplicationTestLayer(NonDevmodeApplicationTestLayer):

	@classmethod
	def setUp(cls):
		# Allow requests from unconfigured domains
		# XXX HACK
		from nti.appserver.tweens.zope_site_tween import _DevmodeMissingSitePolicy
		component.getGlobalSiteManager().registerUtility(_DevmodeMissingSitePolicy)

	@classmethod
	def tearDown(cls):
		from nti.appserver.tweens.zope_site_tween import _ProductionMissingSitePolicy
		component.getGlobalSiteManager().registerUtility(_ProductionMissingSitePolicy)

	@classmethod
	def testSetUp( cls ):
		pass

	@classmethod
	def testTearDown(cls):
		# Must implement
		pass

class TestApplicationNonDevmode(NonDevmodeApplicationLayerTest):

	@WithSharedApplicationMockDS(users=False,testapp=True)
	def test_non_configured_site_raises_error_in_production(self):
		res = self.testapp.get('/foo/bar',
							   extra_environ={b'HTTP_ORIGIN': b'http://foo.bar.com'},
							   status=400)
		assert_that( res.text, contains_string('Invalid site') )

class TestApplication(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_mako_renderer(self):
		from pyramid.renderers import render
		from pyramid_mako import MakoRenderingException
		value = {'world': 'you&me'} # a value to prove that HTML escapes are not done
		val = render( 'nti.appserver.tests:templates/basic_mako_template.mak',
				value,
				request=self.request )
		assert_that( val, is_( 'Hello, you&me!\n' ) )

		# strict undefined should be true
		with assert_raises(MakoRenderingException):
			render( 'nti.appserver.tests:templates/basic_mako_template.mak',
					dict(),
					request=self.request )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_unauthenticated_userid(self):
		from pyramid.interfaces import IAuthenticationPolicy
		auth_policy = component.getUtility(IAuthenticationPolicy)
		assert_that( auth_policy.unauthenticated_userid(self.request), is_( none() ) )
		self._make_extra_environ( update_request=True )
		with mock_dataserver.mock_db_trans(self.ds):
			# Until we actually begin the request, it's not even there
			assert_that( auth_policy.unauthenticated_userid(self.request),
						 is_( none() ) )
			from zope.lifecycleevent import created
			created(self.request)
			assert_that( auth_policy.unauthenticated_userid(self.request),
						 is_(self.extra_environ_default_user.lower() ) )

	def test_locale_negotionion( self ):
		from zope.i18n.interfaces import IUserPreferredLanguages
		self.request.environ['HTTP_ACCEPT_LANGUAGE'] = 'en'
		langs = IUserPreferredLanguages( self.request )
		assert_that( langs.getPreferredLanguages(), is_( ['en'] ) )

		from zope.i18n.interfaces import IUserPreferredCharsets
		chars = IUserPreferredCharsets( self.request )
		assert_that( chars.getPreferredCharsets(), is_( ['utf-8'] ) ) # default

		self.request.environ['HTTP_ACCEPT_CHARSET'] = 'iso-8859-1'
		assert_that( chars.getPreferredCharsets(), is_( ['iso-8859-1'] ) )

	@WithSharedApplicationMockDS
	def test_chameleon_caching_config(self):
		assert_that( self.app, is_( not_none() ) )
		# chameleon is imported by pyramid.
		# it is also imported by us. But depending on the order
		# of imports, chameleon may have gotten initialized too soon
		# and not be using module loaders. see nti.util
		import chameleon.config
		import chameleon.template
		import chameleon.loader
		assert_that( chameleon.config.CACHE_DIRECTORY, is_( not_none() ) )
		assert_that( chameleon.template.CACHE_DIRECTORY, is_( same_instance( chameleon.config.CACHE_DIRECTORY ) ) )
		assert_that( chameleon.template.BaseTemplate, has_property( 'loader', is_(chameleon.loader.ModuleLoader) ) )

	@WithSharedApplicationMockDS
	def test_logon_css_site_policy(self):
		testapp = TestApp(self.app)
		# No site, empty file
		res = testapp.get( '/login/resources/css/site.css' )
		assert_that( res, has_property( 'content_type', 'text/css' ) )
		assert_that( res, has_property( 'text', '' ) )

		# Configured site, redirect
		res = testapp.get( '/login/resources/css/site.css', extra_environ={b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'}, status=200 )
		assert_that( res, has_property( 'content_type', 'text/css') )
		assert_that( res, has_property( 'text', is_not( is_empty() ) ) )


	@WithSharedApplicationMockDS
	def test_webapp_strings_site_policy(self):
		testapp = TestApp(self.app)
		# No site, empty file
		res = testapp.get( '/NextThoughtWebApp/resources/strings/site.js' )
		assert_that( res, has_property( 'text', '' ) )
		assert_that( res, has_property( 'content_type', 'application/javascript' ) )

		# Configured site, content
		# XXX: Note, the name of the file is not consistent
		# and will be changing in one place or another
		res = testapp.get( '/NextThoughtWebApp/resources/strings/site.js',
						   extra_environ={b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'} )
		assert_that( res, has_property( 'content_type', 'application/javascript' ) )
		assert_that( res, has_property( 'charset', none() ) )
		# Cannot access 'text' property until charset is set;
		# should be able to decode as utf-8
		res.charset = 'utf-8'
		assert_that( res, has_property( 'text', is_not( is_empty() ) ) )

	@WithSharedApplicationMockDS
	def test_external_coppa_capabilities_mathcounts(self):
		# See also test_workspaces
		testapp = TestApp(self.app)
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user( 'coppa_user' )
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )

		mc_environ = self._make_extra_environ( user='coppa_user',
											HTTP_ORIGIN=b'http://mathcounts.nextthought.com' )

		res = testapp.get( '/dataserver2',  extra_environ=mc_environ, status=200 )
		assert_that(res.json_body, has_entry('CapabilityList', has_length(3)))
		assert_that(res.json_body, has_entry('CapabilityList',
											contains_inanyorder(
													u'nti.platform.forums.dflforums',
													u'nti.platform.forums.communityforums',
													u'nti.platform.customization.can_change_password')))

	@WithSharedApplicationMockDS
	def test_options_request( self ):
		testapp = TestApp( self.app )
		res = testapp.options( '/dataserver2/logon.ping', extra_environ=self._make_extra_environ() )
		assert_that( res.headers, has_key( 'Access-Control-Allow-Methods' ) )

	@WithSharedApplicationMockDS
	def test_logon_ping(self):
		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/logon.ping' )

		assert_that( res.json_body, has_key( 'Links' ) )

		link_rels = [l['rel'] for l in res.json_body['Links']]
		assert_that( link_rels, has_item( 'account.create' ) )
		assert_that( link_rels, has_item( 'account.preflight.create' ) )
		assert_that(link_rels, has_item(u'logon.continue-anonymously'))

	@WithSharedApplicationMockDS
	def test_logon_ping_demo_site_policy(self):
		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/logon.ping', extra_environ={b'HTTP_ORIGIN': b'http://demo.nextthought.com'} )

		assert_that( res.json_body, has_key( 'Links' ) )

		link_rels = [l['rel'] for l in res.json_body['Links']]
		assert_that( link_rels, does_not( has_item( 'account.create' ) ) )
		assert_that( link_rels, does_not( has_item( 'account.preflight.create' ) ) )

	@WithSharedApplicationMockDS
	def test_resolve_root_ntiid(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			container = IUserTokenContainer(user)
			user_token = UserToken(title=u"title",
	                               description=u"desc",
	                               scopes=(u'userdata:feed',))
			container.store_token(user_token)

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/NTIIDs/' + ntiids.ROOT,
						   headers={"Accept": 'application/json' },
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		feed_link = self.link_with_rel( res.json_body, 'alternate' )
		assert_that( feed_link, has_entry( 'type', 'application/atom+xml' ) )
		assert_that( feed_link, has_entry( 'title', 'RSS' ) )
		assert_that( feed_link, has_entry( 'href', contains_string('?token=') ) )


	@WithSharedApplicationMockDS
	def test_path_with_parens(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = ContainedExternal()
			user = self._create_user( )
			container_id = contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + container_id + ')/UserGeneratedData'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )

	@WithSharedApplicationMockDS
	def test_pages_with_only_shared_not_404(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = PersistentContainedExternal()
			contained.lastModified = 0
			user = self._create_user()
			container_id = contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )

			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )
			contained_str = str(contained)
			contained._str = contained_str

			user2 = self._create_user( username='foo@bar' )
			user2._addSharedObject( contained )
			from nti.dataserver.activitystream_change import Change
			change = Change( Change.SHARED, contained )
			change.creator = user
			user2._addToStream( change )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/foo@bar/Pages(' + container_id + ')/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))

		assert_that( res.body, contains_string( contained_str ) )

		# It should also show up in the RecursiveStream
		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/vnd.nextthought+json'))

		# And the feed
		path = path + '/feed.atom'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/atom+xml'))

	@WithSharedApplicationMockDS
	def test_deprecated_path_with_slash(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = ContainedExternal()
			user = self._create_user()
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/' + contained.containerId + '/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )


	@WithSharedApplicationMockDSHandleChanges(users=('foo@bar',), testapp=True,default_authenticate=True)
	@time_monotonically_increases
	def test_post_put_conditionalput_to_pages_collection(self):

		testapp = self.testapp
		testapp.username = 'sjohnson@nextthought.com'
		otherapp = TestApp(self.app, extra_environ=self._make_extra_environ(username='foo@bar'))
		otherapp.username = 'foo@bar'

		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_HTML, specific='1234' )
		data = { 'Class': 'Highlight',
				 'MimeType': 'application/vnd.nextthought.highlight',
				 'ContainerId': containerId,
				 'sharedWith': ['foo@bar'],
				 'selectedText': 'This is the selected text',
				 'applicableRange': {'Class': 'ContentRangeDescription'}}

		def _lm( datetime ):
			return time.mktime( datetime.timetuple() )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post_json( path, data )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		href = res.json_body['href']
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson@nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )

		# The object can be found in the UGD sub-collection
		# of the creator
		owner_res = self.fetch_user_ugd( containerId, testapp=testapp, username=testapp.username )
		assert_that( owner_res.json_body['Items'][0], has_entry( 'selectedText', data['selectedText'] ) )

		# and in the UGD sub-collection of the sharing target
		other_res = self.fetch_user_ugd( containerId, testapp=otherapp, username=otherapp.username )
		assert_that( other_res.json_body['Items'][0], has_entry( 'selectedText', data['selectedText'] ) )
		# Which has the same timestamp, but not etag
		# its actually slightly behind  due to the order of update events
		# (constant is very fragile and depends on the internal implementation of several
		# modules; CPython 2.7.9 once required 6 while PyPy 2.5.1 required 20)
		assert_that(_lm(other_res.last_modified),
					is_(greater_than_or_equal_to(_lm(owner_res.last_modified) - 20)))
		assert_that( other_res.etag, is_not( owner_res.etag ) )


		# And the feed for the other user (not ourself)
		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream/feed.atom'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/atom+xml'))
		assert_that( res.body, contains_string( "This is the selected text" ) )

		# If i edit the object, the mod time and etag changes for both views
		res = testapp.put_json( href, {'selectedText': 'New'} )
		assert_that( res.json_body, has_entry( 'selectedText', 'New' ) )

		new_owner_res = self.fetch_user_ugd( containerId, testapp=testapp, username=testapp.username )
		assert_that( new_owner_res.etag, is_not( owner_res.etag ) )
		assert_that( _lm(new_owner_res.last_modified), is_not( _lm(owner_res.last_modified ) ) )

		new_other_res = self.fetch_user_ugd( containerId, testapp=otherapp, username=otherapp.username )
		assert_that( new_other_res.etag, is_not( other_res.etag ) )
		assert_that( _lm(new_other_res.last_modified), is_(greater_than( _lm(other_res.last_modified ) ) ))

		# I can conditionally try to put based on timestamp and
		# get precondition failed
		assert_that( res.json_body['CreatedTime'], is_( less_than( res.json_body['Last Modified'] ) ) )
		since = datetime.datetime.fromtimestamp( res.json_body['CreatedTime'], webob.datetime_utils.UTC )
		http_since = webob.datetime_utils.serialize_date(since)
		testapp.put_json( href, {'selectedText': 'Conditional'},
						  headers={'If-Unmodified-Since': http_since},
						  status=412 )

		# Same thing for delete
		testapp.delete( href,
						headers={'If-Unmodified-Since': http_since},
						status=412 )

		# The pages collection should have complete URLs
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages'
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = res.json_body
		links = body['Collection']['Links']
		assert_that( links, has_item( has_entry( 'href', '/dataserver2/users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData' ) ) )
		assert_that( body, has_entry( 'Items', has_length( 2 ) ) )
		for item in body['Items']:
			item_id = item['ID']
			links = item['Links']
			assert_that( links, has_item( has_entry( 'href',
													 '/dataserver2/users/sjohnson@nextthought.com/Pages(%s)/RecursiveStream' % item_id ) ) )

		# I can now delete that item
		testapp.delete( str(href), extra_environ=self._make_extra_environ())

	@WithSharedApplicationMockDSHandleChanges(users=True,testapp=True)
	@time_monotonically_increases
	def test_transcript_caching_response(self):
		# Fetching a transcript uses an
		# etag that takes into account the flag status of all its
		# messages
		with mock_dataserver.mock_db_trans( self.ds ) as conn:
			# First, give a transcript summary

			user = users.User.get_user( self.extra_environ_default_user )
			from nti.chatserver import interfaces as chat_interfaces
			import zc.intid as zc_intid
			storage = chat_interfaces.IUserTranscriptStorage(user)

			from nti.chatserver.messageinfo import MessageInfo as Msg
			from nti.chatserver.meeting import _Meeting as Meet
			msg = Msg()
			meet = Meet()

			meet.containerId = u'tag:nti:foo'
			meet.creator = user
			meet.ID = 'the_meeting'
			msg.containerId = meet.containerId
			msg.ID = '42'
			msg.creator = user
			msg.__parent__ = meet

			component.getUtility( zc_intid.IIntIds ).register( msg )
			component.getUtility( zc_intid.IIntIds ).register( meet )
			conn.add( meet )
			storage.add_message( meet, msg )

			ntiid = to_external_ntiid_oid( meet )
			ntiid = ntiid.replace('OID', 'Transcript' )

		res = self.fetch_by_ntiid( ntiid )
		res2 = self.fetch_by_ntiid( ntiid )
		assert_that( res.last_modified, is_( res2.last_modified ) )
		assert_that( res.etag, is_( res2.etag ) )


		self.testapp.post( self.require_link_href_with_rel( res.json_body['Messages'][0], 'flag' ) )

		res2 = self.fetch_by_ntiid( ntiid )

		assert_that( res.last_modified, is_( res2.last_modified ) )
		assert_that( res.etag, is_not( res2.etag ) )

	@WithSharedApplicationMockDS
	def test_get_highlight_by_oid_has_links(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()

		testapp = TestApp( self.app )
		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		data = json.dumps({ 'Class': 'Highlight', 'MimeType': 'application/vnd.nextthought.highlight',
							'ContainerId': containerId,
							'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson@nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )


		path = res.headers['Location']
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_(200) )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links',
									  has_item( all_of(
										  has_entry( 'href', contains_string( '/dataserver2/users/sjohnson@nextthought.com/Objects/tag' ) ),
										  has_entry( 'rel', 'edit' ) ) ) ))

	@WithSharedApplicationMockDS
	def test_post_two_friendslist_same_name(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.dumps( { 'Class': 'FriendsList',  'MimeType': 'application/vnd.nextthought.friendslist',
							 'ContainerId': 'FriendsLists',
							 'ID': "Foo@bar" } )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		testapp.post( path, data, extra_environ=self._make_extra_environ() )
		# Generates a conflict the next time
		testapp.post( path, data, extra_environ=self._make_extra_environ(), status=409 )

	@WithSharedApplicationMockDS
	def test_friends_list_unmodified(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( none() ) )

	@WithSharedApplicationMockDS
	def test_post_device(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.dumps( { 'Class': 'Device', 'MimeType': 'application/vnd.nextthought.device',
							 'ContainerId': 'Devices',
							 'ID': "deadbeef" } )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.device' ) )
		# Generates a conflict the next time
		testapp.post( path, data, extra_environ=self._make_extra_environ(), status=409 )

	@WithSharedApplicationMockDS
	def test_put_device(self):
		#"Putting a non-existant device is not possible"
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.dumps( { 'Class': 'Device',
							 'ContainerId': 'Devices',
							 'ID': "deadbeef" } )
		path = '/dataserver2/users/sjohnson@nextthought.com/Devices/deadbeef'
		testapp.put( path, data, extra_environ=self._make_extra_environ(), status=404 )
		# But we can post it
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )
		# And then put
		__traceback_info__ = path
		testapp.put( path, data, extra_environ=self._make_extra_environ(), status=200 )

	@WithSharedApplicationMockDS
	def test_post_restricted_types(self):
		data = {u'Class': 'Canvas',
				'ContainerId': 'tag:foo:bar',
				u'MimeType': u'application/vnd.nextthought.canvas',
				'shapeList': [{u'Class': 'CanvasUrlShape',
							   u'MimeType': u'application/vnd.nextthought.canvasurlshape',
							   u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()


		json_data = json.dumps( data )

		testapp = TestApp( self.app )

		# Without restrictions, we can post it
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data, extra_environ=self._make_extra_environ() )

		# If we become restricted, we cannot post it
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( 'sjohnson@nextthought.com' )
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )

		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data,
					  extra_environ=self._make_extra_environ(),
					  status=403 ) # Forbidden!

	@WithSharedApplicationMockDS
	def test_post_canvas_image_roundtrip_download_views(self):
		#" Images posted as data urls come back as real links which can be fetched "
		data = {'Class': 'Canvas',
				'ContainerId': 'tag:foo:bar',
				'MimeType': 'application/vnd.nextthought.canvas',
				'shapeList': [{'Class': 'CanvasUrlShape',
							   'MimeType': 'application/vnd.nextthought.canvasurlshape',
							   'url': 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()


		json_data = json.dumps( data )

		testapp = TestApp( self.app )

		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data, extra_environ=self._make_extra_environ() )

		canvas = res.json_body
		assert_that( canvas, has_entry( 'shapeList', has_length( 1 ) ) )
		assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'Class', 'CanvasUrlShape' ) ) ) )
		assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'url', contains_string( '/dataserver2/' ) ) ) ) )
		canvas_res = res

		res = testapp.get( canvas['shapeList'][0]['url'], extra_environ=self._make_extra_environ() )
		# The content type is preserved
		assert_that( res, has_property( 'content_type', 'image/gif' ) )
		# The modified date is the same as the canvas containing it
		assert_that( res, has_property( 'last_modified', not_none() ) )
		assert_that( res, has_property( 'last_modified', canvas_res.last_modified ) )

	@WithSharedApplicationMockDS
	def test_post_canvas_in_note_image_roundtrip_download_views(self):
		#" Images posted as data urls come back as real links which can be fetched "
		canvas_data = {'Class': 'Canvas',
					   'ContainerId': 'tag:foo:bar',
					   'MimeType': 'application/vnd.nextthought.canvas',
					   'shapeList': [{'Class': 'CanvasUrlShape',
									  'MimeType': 'application/vnd.nextthought.canvasurlshape',
									  'url': 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}
		data = {'Class': 'Note',
				'ContainerId': 'tag:foo:bar',
				'MimeType': 'application/vnd.nextthought.note',
				'applicableRange': {'Class': 'ContentRangeDescription'},
				'body': [canvas_data]}

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()


		testapp = TestApp( self.app )

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )

		def _check_canvas( res ):
			canvas = res.json_body['body'][0]
			assert_that( canvas, has_entry( 'shapeList', has_length( 1 ) ) )
			assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'Class', 'CanvasUrlShape' ) ) ) )
			assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'url', contains_string( '/dataserver2/' ) ) ) ) )


			res = testapp.get( canvas['shapeList'][0]['url'], extra_environ=self._make_extra_environ() )
			# The content type is preserved
			assert_that( res, has_property( 'content_type', 'image/gif' ) )
			# The modified date is the same as the canvas containing it
			assert_that( res, has_property( 'last_modified', not_none() ) )
		#	assert_that( res, has_property( 'last_modified', canvas_res.last_modified ) )
			return canvas

		canvas = _check_canvas( res )
		canvas_oid = canvas['OID']
		file_url = canvas['shapeList'][0]['url']

		# If we "edit" the data, then nothing breaks
		edit_link = None
		for l in res.json_body['Links']:
			if l['rel'] == 'edit':
				edit_link = l['href']
				break
		res = testapp.put( edit_link.encode('ascii'), res.body, content_type='application/json', extra_environ=self._make_extra_environ() )
		assert_that( res.json_body['body'][0]['OID'], is_(canvas_oid) )
		assert_that(  res.json_body['body'][0]['shapeList'][0]['url'], is_(file_url) )
		_check_canvas( res )

		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( user.username )
			note = user.getContainedObject( res.json_body['ContainerId'], res.json_body['ID'] )
			canvas = note.body[0]
			url_shape = canvas.shapeList[0]
			# And it externalizes as a real link because it owns the file data
			assert_that( url_shape.toExternalObject()['url'], is_( links.Link ) )



	@WithSharedApplicationMockDS
	def test_create_friends_list_content_type(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
		testapp = TestApp( self.app )
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["troy.daley@nextthought.com"],"realname":"boom"}'

		path = '/dataserver2/users/sjohnson@nextthought.com/FriendsLists/'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"boom@nextthought.com"' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )


		assert_that( res.json_body, has_entry( 'href', '/dataserver2/users/sjohnson@nextthought.com/FriendsLists/boom@nextthought.com' ) )

	@WithSharedApplicationMockDS
	def test_create_friends_list_post_user(self):
		# Like the previous test, but _UGDPostView wasn't consistent with where it was setting up the phony location proxies,
		# so we could get different results depending on where we came from
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
		testapp = TestApp( self.app )
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["troy.daley@nextthought.com"],"realname":"boom"}'

		path = '/dataserver2/users/sjohnson@nextthought.com'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"boom@nextthought.com"' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

		assert_that( res.json_body, has_entry( 'href', is_('/dataserver2/users/sjohnson@nextthought.com/FriendsLists/boom@nextthought.com' ) ))

		testapp.delete( str(res.json_body['href']), extra_environ=self._make_extra_environ() )

	@WithSharedApplicationMockDS
	def test_friends_lists_collections(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			creator_username = self._create_user().username
			member_username = self._create_user( username='troy.daley@nextthought.com' ).username

		testapp = TestApp( self.app )
		ext_obj = {
			"ContainerId": "FriendsLists",
			"Username": "boom@nextthought.com",
			"friends":[member_username],
			"realname":"boom",
			'IsDynamicSharing': True }
		data = json.dumps( ext_obj )

		# Base empty case, prep our caching headers
		etags = {}
		etags[creator_username] = {}
		etags[member_username] = {}
		last_mods = {}
		last_mods[creator_username] = {}
		last_mods[member_username] = {}
		endpoints = ( 'FriendsLists', 'Groups', 'DynamicMemberships', 'Communities' )
		for username in ( creator_username, member_username ):
			user_etags = etags.get( username )
			user_last_mods = last_mods.get( username )
			for endpoint in endpoints:
				res = testapp.get( '/dataserver2/users/%s/%s' % ( username, endpoint ),
											extra_environ=self._make_extra_environ( username=username ) )
				assert_that( res.etag, not_none() )
				user_etags[ endpoint ] = res.etag
				user_last_mods[ endpoint ] = last_mod = res.json_body.get( 'Last Modified' )
				if endpoint == 'Groups':
					# No DFLs, so no last mod
					assert_that( last_mod, none() )

		def _check_update_caching( res, endpoint, username, updated=False ):
			"""
			Check our caching vals for user. If updated, assert they have changed.
			"""
			user_etags = etags.get( username )
			user_last_mods = last_mods.get( username )
			to_assert = is_not if updated else is_

			assert_that( res.etag, to_assert( user_etags.get( endpoint ) ))
			user_etags[ endpoint ] = res.etag
			new_last_mod = res.json_body.get( 'Last Modified' )
			assert_that( new_last_mod, to_assert( user_last_mods.get( endpoint ) ))
			user_last_mods[ endpoint ] = new_last_mod

		# Unchanged
		for username in ( creator_username, member_username ):
			for endpoint in endpoints:
				res = testapp.get( '/dataserver2/users/%s/%s' % ( username, endpoint ),
											extra_environ=self._make_extra_environ( username=username ) )
				_check_update_caching( res, endpoint, username )

		# The user creates DFL
		path = '/dataserver2/users/%s/FriendsLists/' % creator_username
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(),
						headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( 'boom@nextthought.com' ) )
		assert_that( res.headers, has_entry( 'Content-Type',
											contains_string( 'application/vnd.nextthought.dynamicfriendslist+json' ) ) )
		assert_that( res.json_body, has_entry( 'IsDynamicSharing', True ) )

		def _friends_list_empty_check( username, owner=False ):
			member_fl_res = testapp.get( '/dataserver2/users/%s/FriendsLists' % username,
									extra_environ=self._make_extra_environ( username=username ) )
			assert_that( member_fl_res.json_body, has_entry( 'Items',
												is_not( has_value(
															has_entry( 'Username',
																	contains_string( 'boom@nextthought.com' ) ) ) ) ) )
			# Only updated for owner
			updated = owner
			_check_update_caching( member_fl_res, 'FriendsLists', username, updated=updated )

		def _dfl_contains_check( username, owner=False ):
			to_check = ('Groups',) if owner else ( 'Groups', 'DynamicMemberships' )
			for dfl_endpoint in to_check:
				member_fl_res = testapp.get( '/dataserver2/users/%s/%s' % ( username, dfl_endpoint ),
										extra_environ=self._make_extra_environ( username=username ) )
				assert_that( member_fl_res.json_body, has_entry( 'Items',
													has_value(	has_entry( 'Username',
																		contains_string( 'boom@nextthought.com' ) ) ) ) )
				_check_update_caching( member_fl_res, dfl_endpoint, username, updated=True )

		# FL collection does not have it, DFL does. Creator and member both see.
		_friends_list_empty_check( creator_username, owner=True )
		_dfl_contains_check( creator_username, owner=True )
		_friends_list_empty_check( member_username )
		_dfl_contains_check( member_username )

		# The owner can edit it to remove the membership
		data = '[]'
		path = res.json_body['href'] + '/++fields++friends'

		res = testapp.put( str(path),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.json_body, has_entry( 'friends', [] ) )


		for dfl_endpoint in ('Groups', 'DynamicMemberships'):
			member_fl_res = testapp.get( '/dataserver2/users/%s/%s' % (member_username, dfl_endpoint),
									extra_environ=self._make_extra_environ( username='troy.daley@nextthought.com' ) )
			assert_that( member_fl_res.json_body, has_entry( 'Items',
													does_not( has_value(
															has_entry( 'Username',
																	contains_string( 'boom@nextthought.com' ) ) ) ) ) )
			_check_update_caching( member_fl_res, dfl_endpoint, member_username, updated=True )


	@WithSharedApplicationMockDS
	def test_edit_note_returns_editlink(self):
		#"The object returned by POST should have enough ACL to regenerate its Edit link"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = '{"body": ["text"]}'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % urllib_parse.quote(n_ext_id)
		res = testapp.put( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( json.loads(res.body), has_entry( 'href', path ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'edit' ) ) ) )

	@WithSharedApplicationMockDS
	def test_like_unlike_note(self):
		#"We get the appropriate @@like or @@unlike links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/Objects/%s' % n_ext_id
		# Initially, unliked, I get asked to like
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( json.loads(res.body),
					 has_entry( 'Links',
								has_item(
									has_entry(
										'href',
										'/dataserver2/Objects/%s/@@like' % urllib_parse.quote(n_ext_id) ) ) ) )

		# So I do
		res = testapp.post( path + '/@@like', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to unlike
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 1 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unlike' ) ) ) )

		# Same again
		res = testapp.post( path + '/@@like', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unlike' ) ) ) )

		# And I can unlike
		res = testapp.post( path + '/@@unlike', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )

	@WithSharedApplicationMockDS
	def test_favorite_unfavorite_note(self):
		#"We get the appropriate @@favorite or @@unfavorite links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		# Initially, unliked, I get asked to favorite
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )

		# So I do
		res = testapp.post( path + '/@@favorite', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to unlike
		assert_that( res.status_int, is_( 200 ) )
		# like count doesn't change
		assert_that( res.json_body, has_entry( 'LikeCount',  0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unfavorite' ) ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )

		# Same again
		res = testapp.post( path + '/@@favorite', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unfavorite' ) ) ) )

		# And I can unlike
		res = testapp.post( path + '/@@unfavorite', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )

	@WithSharedApplicationMockDS
	def test_edit_note_sharing_coppa_user(self):
		#"Unsigned coppa users cannot share anything after creation"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = '["Everyone"]'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		field_path = path + '/++fields++sharedWith' # The name of the external field

		_ = testapp.put( urllib_parse.quote( field_path ),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" },
						   status=403	)

	@WithSharedApplicationMockDS
	def test_create_note_sharing_coppa_user(self):
		#"Unsigned coppa users cannot share anything at creation"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )


		testapp = TestApp( self.app )
		n = contenttypes.Note()
		n.applicableRange = contentrange.ContentRangeDescription()
		n.containerId = u'tag:nti:foo'

		# Note that we externalize before we attempt to add the sharing data,
		# because the sharingTargets field is externalized in a special way
		ext_object = to_external_object( n )
		ext_object['sharedWith'] = ['Everyone']

		data  = to_json_representation( ext_object )

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/'

		_ = testapp.post( urllib_parse.quote( path ),
						   data,
						   extra_environ=self._make_extra_environ(update_request=True),
						   headers={"Content-Type": "application/json" },
						   status=403	)

	@WithSharedApplicationMockDS
	def test_edit_note_sharing_only(self):
		#"We can POST to a specific sub-URL to change the sharing"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = '["Everyone"]'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % urllib_parse.quote(n_ext_id)
		field_path = path + '/++fields++sharedWith' # The name of the external field

		res = testapp.put( field_path,
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" } )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.json_body, has_entry( "sharedWith", has_item( "Everyone" ) ) )

		assert_that( res.json_body, has_entry( 'href', path ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'edit' ) ) ) )

	@WithSharedApplicationMockDS
	def test_note_field_creator(self):
		"""
		We can fetch a creator field, but not updated it.
		"""
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			username = user.username

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		field_path = path + '/++fields++Creator' # The name of the external field

		# Fetch
		res = testapp.get( urllib_parse.quote( field_path ),
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( "Username", is_( username )))

		# Update to field is ignored
		res = testapp.put( urllib_parse.quote( field_path ),
						   '"dne_user1"',
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" } )

		assert_that( res.json_body, has_entry( "Creator", is_( username ) ) )

	def _edit_user_ext_field( self, field, data, username=None, user_ext_id=None ):
		if username is None:
			with mock_dataserver.mock_db_trans( self.ds ):
				user = self._create_user()
				username = user.username
				user_ext_id = to_external_ntiid_oid( user )

		testapp = TestApp( self.app )

		# This works for both the OID and direct username paths
		for path in ('/dataserver2/Objects/%s' % user_ext_id, '/dataserver2/users/' + username):
			# Both the classic (direct) and the namespace approach
			# ONly the namespace is supported
			for field_segment in ('++fields++' + field, ):
				field_path = path + '/' + field_segment # The name of the external field

				res = testapp.put( urllib_parse.quote( field_path ),
								   data,
								   extra_environ=self._make_extra_environ(),
								   headers={"Content-Type": "application/json" } )
				assert_that( res.status_int, is_( 200 ) )

				with mock_dataserver.mock_db_trans( self.ds ):
					user = users.User.get_user(username)
					# For the case where we change the password, we have to
					# recreate the user for the next loop iteration to work
					user.password = 'temp001'
		return res

	@WithSharedApplicationMockDS
	def test_edit_user_password_only(self):
		#"We can POST to a specific sub-URL to change the password"
		data = json.dumps( {'password': 'newp4ssw0r8', 'old_password': 'temp001' } )
		self._edit_user_ext_field( 'password', data )

	@WithSharedApplicationMockDS
	def test_edit_user_count_only(self):
		#"We can POST to a specific sub-URL to change the notification count"

		data = '5'
		self._edit_user_ext_field( 'NotificationCount', data )

	def _test_edit_user_image_url(self, name, default_status=404, default_url=None):
		data = u'"data:image/gif;base64,R0lGODlhEAAQANUAAP///////vz9/fr7/Pf5+vX4+fP2+PL19/D09uvx8+Xt797o69zm6tnk6Nfi5tLf49Dd483c4cva38nZ38jY3cbX3MTW3MPU2sLT2cHT2cDS2b3R2L3Q17zP17vP1rvO1bnN1LbM1LbL07XL0rTK0bLI0LHH0LDHz6/Gzq7Ezq3EzavDzKnCy6jByqbAyaS+yKK9x6C7xZ66xJu/zJi2wY2uukZncwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAEAAQAAAGekCAcEgsEmvIJNJmBNSEAQHh8GQWn4BBAZHAWm1MsM0AVtTEYYd67bAtGrO4lb1mOB4RyixNb0MkFRh7ADZ9bRMWGh+DhX02FxsgJIMAhhkdISUpjIY2IycrLoxhYBxgKCwvMZRCNRkeIiYqLTAyNKxOcbq7uGi+YgBBADs="'

		testapp = TestApp( self.app )
		# First, we can get the old one at a well-known location for the user
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			username = user.username
			user_ext_id = to_external_ntiid_oid( user )

		view_name = '/@@%s' % name
		attr_name = '%sURL' % name
		# We find our default generated
		res = testapp.get('/dataserver2/users/' + username + view_name, extra_environ=self._make_extra_environ(),
					status=default_status)
		assert_that( res.location, is_( default_url ) )

		# Set our new avatar
		res = self._edit_user_ext_field( attr_name, data, username, user_ext_id )
		assert_that( res.json_body, has_entry( attr_name, starts_with( '/dataserver2/' ) ) )

		res = testapp.get( res.json_body[attr_name], extra_environ=self._make_extra_environ() )
		assert_that( res.content_type, is_( 'image/gif' ) )
		# And this one is also directly available at this location
		res = testapp.get('/dataserver2/users/' + username + view_name,
						  extra_environ=self._make_extra_environ(),
						  status=302)
		assert_that( res.location, starts_with( 'http://localhost/dataserver2/' ) )

	@WithSharedApplicationMockDS
	def test_edit_user_avatar_url(self):
		"We can POST to a specific sub-URL to change the avatarURL"
		# By default, we have a gravatar url
		default_url = 'https://secure.gravatar.com/avatar/31f94302764fc0b184fd0c2e96e4084f?s=128&d=identicon'
		default_status = 302
		self._test_edit_user_image_url('avatar', default_status, default_url)

	@WithSharedApplicationMockDS
	def test_edit_user_background_url(self):
		#"We can POST to a specific sub-URL to change the backgroundURL"
		self._test_edit_user_image_url('background')

	@WithSharedApplicationMockDS
	def test_put_data_to_user( self ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			username = user.username
			user_ext_id = to_external_ntiid_oid( user )

		testapp = TestApp( self.app )

		# This works for both the OID and direct username paths
		for path in ('/dataserver2/Objects/%s' % user_ext_id, '/dataserver2/users/' + username):

			data = json.dumps( {"NotificationCount": 5 } )

			res = testapp.put( urllib_parse.quote( path ),
							   data,
							   extra_environ=self._make_extra_environ(),
							   headers={"Content-Type": "application/json" } )
			assert_that( res.status_int, is_( 200 ) )
			assert_that( res.json_body, has_entry( 'NotificationCount', 5 ) )


	@WithSharedApplicationMockDS(users=('foo@bar',),testapp=True,default_authenticate=True)
	def test_get_user(self):
		testapp = self.testapp
		othertestapp = TestApp( self.app, extra_environ=self._make_extra_environ(username='foo@bar') )
		# I can get myself
		path = '/dataserver2/users/sjohnson@nextthought.com'
		res = testapp.get( path )
		assert_that( res.json_body, has_key( 'Username' ) )
		# Another user cannot
		othertestapp.get( path, status=403 )

	@WithSharedApplicationMockDS
	def test_profile_field_put(self):
		username = 'larry.david@curb.com'
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user( username )
		testapp = TestApp( self.app )

		user_path = '/dataserver2/users/%s' % username
		extra_environ = self._make_extra_environ( username=username )
		res = testapp.get( user_path, extra_environ=extra_environ  )
		assert_that( res.json_body, has_entry( 'positions', none() ))

		start_year = 1999
		end_year = 2004
		company_name = 'The Producers'
		title = 'Producer'
		description = 'no good?'
		school = 'School of Hard Knocks'
		degree = 'CS'

		data = '''[{"MimeType": "%s",
					"startYear": "%s",
					"endYear": "%s",
					"companyName" : "%s",
					"description" : "%s",
					"title" : "%s"}]''' \
				 % ( ProfessionalPosition.mime_type, start_year,
					end_year, company_name, description, title )
		path = '/dataserver2/users/%s/++fields++positions' % username
		res = testapp.put( path,
							data,
							extra_environ=extra_environ )

		res = testapp.get( user_path, extra_environ=extra_environ  )
		assert_that( res.json_body, has_entry( 'positions',
										has_item( has_entries( 'startYear', start_year,
														 'endYear', end_year,
														 'companyName', company_name,
														 'description', description,
														 'title', title ) )) )

		# Education
		data = '''[{"MimeType": "%s",
				"startYear": "%s",
				"endYear": "%s",
				"school" : "%s",
				"description" : "%s",
				"degree" : "%s"}]''' \
				% ( Education.mime_type, start_year,
					end_year, school, description, degree )
		path = '/dataserver2/users/%s/++fields++education' % username
		res = testapp.put( path,
							data,
							extra_environ=extra_environ )

		res = testapp.get( user_path, extra_environ=extra_environ  )
		assert_that( res.json_body, has_entry( 'positions', not_none() ))
		assert_that( res.json_body, has_entry( 'education',
										has_item( has_entries( 'startYear', start_year,
														 'endYear', end_year,
														 'school', school,
														 'description', description,
														 'degree', degree ) ) ))


	@WithSharedApplicationMockDS
	def test_default_admin_user(self):
		"""
		On dataserver install, we create this user with an auth token.
		"""
		with mock_dataserver.mock_db_trans(self.ds):
			admin_user = users.User.get_user(ADMIN_USERNAME)
			assert_that(admin_user, not_none())
			token_container = IUserTokenContainer(admin_user)
			assert_that(token_container, has_length(1))
			assert_that(token_container.get_valid_tokens(), has_length(1))
			token = token_container.get_valid_tokens()[0]
			assert_that(token, validly_provides(IAuthToken))
			token_val = token.token
		encoded_token = base64.b64encode('%s:%s' % (ADMIN_USERNAME, token_val))

		# Validate full authentication
		testapp = TestApp(self.app)
		user_path = '/dataserver2/users/%s' % ADMIN_USERNAME
		headers = {b'HTTP_AUTHORIZATION': 'Bearer %s' % encoded_token}
		testapp.get(user_path, extra_environ=headers)

		def _update_token_exp(days, val=token_val):
			with mock_dataserver.mock_db_trans(self.ds):
				admin_user = users.User.get_user(ADMIN_USERNAME)
				token_container = IUserTokenContainer(admin_user)
				token = token_container.get_token_by_value(val)
				token.expiration_date = datetime.datetime.utcnow() + datetime.timedelta(days=days)

		# If token expires, we can longer authenticate
		_update_token_exp(-30)
		testapp.get(user_path, extra_environ=headers, status=401)

		# Refresh the token, using the existing token for auth
		_update_token_exp(30)
		# Bad input
		testapp.post_json('/dataserver2/RefreshToken', {'days':30},
						  extra_environ=headers, status=422)
		testapp.post_json('/dataserver2/RefreshToken', {'token': "dne_token_val"},
						  extra_environ=headers, status=404)
		testapp.post_json('/dataserver2/RefreshToken', {'token': token_val, "days": "a"},
						  extra_environ=headers, status=422)
		testapp.post_json('/dataserver2/RefreshToken',
						  {'token': token_val, "days": "-1"},
						  extra_environ=headers, status=422)

		# Good input
		res = testapp.post_json('/dataserver2/RefreshToken',
								{'token': token_val, "days": "100"},
								extra_environ=headers)
		res = res.json_body
		new_token_val = res.get('token')
		new_token_ntiid = res.get('NTIID')
		assert_that(new_token_val, not_none())
		assert_that(new_token_ntiid, not_none())
		assert_that(res.get('expiration_date'), not_none())

		# Existing header now fails
		testapp.get(user_path, extra_environ=headers, status=401)

		# New one works
		encoded_token = base64.b64encode('%s:%s' % (ADMIN_USERNAME, new_token_val))
		headers = {b'HTTP_AUTHORIZATION': 'Bearer %s' % encoded_token}
		testapp.get(user_path, extra_environ=headers)

		# Default days
		res = testapp.post_json('/dataserver2/RefreshToken',
						  		{'token': new_token_val},
						 		extra_environ=headers)
		res = res.json_body
		new_token_val = res.get('token')

		# Generic view
		_update_token_exp(1, val=new_token_val)
		encoded_token = base64.b64encode('%s:%s' % (ADMIN_USERNAME, new_token_val))
		headers = {b'HTTP_AUTHORIZATION': 'Bearer %s' % encoded_token}
		res = testapp.post('/dataserver2/RefreshAllAuthTokens',
						   extra_environ=headers)
		res = res.json_body
		tokens = res.get('Items')
		assert_that(tokens, has_length(1))
		token_ext = tokens[0]
		assert_that(token_ext.get('token'), not_none())
		assert_that(token_ext.get('EncodedToken'), not_none())

		# Also works if we have a password
		extra_environ = self._make_extra_environ(user=ADMIN_USERNAME)
		testapp.get(user_path, extra_environ=extra_environ, status=401)
		with mock_dataserver.mock_db_trans(self.ds):
			admin_user = users.User.get_user(ADMIN_USERNAME)
			admin_user.password = 'temp001'
		testapp.get(user_path, extra_environ=extra_environ)


class TestUtil(unittest.TestCase):

	def test_dump_info(self):
		string = nti.appserver._util.dump_info()
		assert_that( string, contains_string( 'dump_stacks' ) )


class TestAppUtil(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_database(self):
		seq = nti.appserver._util.dump_database_cache(gc=True)
		assert_that( seq, has_item( contains_string( 'Database' ) ) )


class UnrestrictedContentTypesApplicationLayer(ZopeComponentLayer,
									           PyramidLayerMixin,
									           GCLayerMixin,
									           ConfiguringLayerMixin,
									           DSInjectorMixin):
	features = ('all-content-types-available', )
	set_up_packages = ()  # None, because configuring the app will do this
	APP_IN_DEVMODE = True
	# We have no packages, but we will set up the listeners ourself when
	# configuring the app
	configure_events = False

	@classmethod
	def _setup_library(cls, *unused_args, **unused_kwargs):
		return Library()
	
	@classmethod
	def _extra_app_settings(cls):
		return {}

	@classmethod
	def setUp(cls):
		zope.testing.cleanup.cleanUp()
		AppCreatingLayerHelper.appSetUp(cls)

	@classmethod
	def tearDown(cls):
		AppCreatingLayerHelper.appTearDown(cls)

	@classmethod
	def testSetUp(cls, test=None):
		AppCreatingLayerHelper.appTestSetUp(cls, test)

	@classmethod
	def testTearDown(cls, test=None):
		AppCreatingLayerHelper.appTestTearDown(cls, test)

class TestUnrestrictedContentTypes(AppTestBaseMixin, unittest.TestCase):

	layer =	 UnrestrictedContentTypesApplicationLayer

	@WithSharedApplicationMockDS
	def test_post_restricted_types(self):
		"""
		The ``all-content-types-available`` zcml feature bypasses content type
		restrictions even for restricted Coppa accounts.
		"""
		data = {u'Class': 'Canvas',
				'ContainerId': 'tag:foo:bar',
				u'MimeType': u'application/vnd.nextthought.canvas',
				'shapeList': [{u'Class': 'CanvasUrlShape',
							   u'MimeType': u'application/vnd.nextthought.canvasurlshape',
							   u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()


		json_data = json.dumps( data )

		testapp = TestApp( self.app )

		# As a normal user we can post it
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data,
					  extra_environ=self._make_extra_environ() )

		# Even marked as a coppa user we can post it. Expectation is our environments
		# actually supporting coppa (legacy MC) will NOT have this flag. 
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( 'sjohnson@nextthought.com' )
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )

		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', json_data,
					  extra_environ=self._make_extra_environ() )
