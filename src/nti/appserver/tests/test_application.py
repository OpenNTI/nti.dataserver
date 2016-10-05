#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

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
from nti.testing.time import time_monotonically_increases
from nti.testing.matchers import is_empty
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

from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization.representation import to_json_representation

import webob.datetime_utils
import datetime
import time

import urllib
from nti.dataserver import users
from nti.ntiids import ntiids
from nti.dataserver_core.mixins import ZContainedMixin
from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_external_object
from nti.contentrange import contentrange
from nti.links import links

from nti.dataserver import contenttypes
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.tests import mock_dataserver
from nti.dataserver.users.user_profile import Education
from nti.dataserver.users.user_profile import ProfessionalPosition

import anyjson as json
from urllib import quote as UQ
from persistent import Persistent
from zope import interface
from zope import component

from zope.keyreference.interfaces import IKeyReference

@interface.implementer(IKeyReference) # IF we don't, we won't get intids
class ContainedExternal(ZContainedMixin):

	def __str__( self ):
		if '_str' in self.__dict__:
			return self._str
		return "<%s %s>" % (self.__class__.__name__, self.to_container_key())

	def toExternalObject( self, **kwargs ):
		return str(self)
	def to_container_key(self):
		return to_external_ntiid_oid(self, default_oid=str(id(self)))


class PersistentContainedExternal(ContainedExternal,Persistent):
	pass


from nti.app.testing.webtest import TestApp
from nti.testing.layers import find_test
from nti.app.testing.application_webtest import ApplicationTestLayer
from nti.app.testing.application_webtest import NonDevmodeApplicationTestLayer
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.application_webtest import NonDevmodeApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges


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
	def test_plone_18n_resources(self):
		# We should be able to use the zope resource namespace traversal
		res = self.testapp.get( '/dataserver2/++resource++country-flags/td.gif' )
		assert_that( res, has_property( 'content_type', 'image/gif' ) )

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
			self._create_user()

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
		#path = urllib.quote( path )
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
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
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
		assert_that( links, has_item( has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Search/RecursiveUserGeneratedData' ) ) )
		assert_that( body, has_entry( 'Items', has_length( 2 ) ) )
		for item in body['Items']:
			item_id = item['ID']
			links = item['Links']
			assert_that( links, has_item( has_entry( 'href',
													 urllib.quote( '/dataserver2/users/sjohnson@nextthought.com/Pages(%s)/RecursiveStream' % item_id ) ) ) )

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
		data = json.serialize( { 'Class': 'Highlight', 'MimeType': 'application/vnd.nextthought.highlight',
								 'ContainerId': containerId,
								 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )


		path = res.headers['Location']
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_(200) )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links',
									  has_item( all_of(
										  has_entry( 'href', contains_string( '/dataserver2/users/sjohnson%40nextthought.com/Objects/tag' ) ),
										  has_entry( 'rel', 'edit' ) ) ) ))

	@WithSharedApplicationMockDS
	def test_post_two_friendslist_same_name(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'FriendsList',  'MimeType': 'application/vnd.nextthought.friendslist',
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

		data = json.serialize( { 'Class': 'Device', 'MimeType': 'application/vnd.nextthought.device',
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

		data = json.serialize( { 'Class': 'Device',
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


		json_data = json.serialize( data )

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
		data = {u'Class': 'Canvas',
				'ContainerId': 'tag:foo:bar',
				u'MimeType': u'application/vnd.nextthought.canvas',
				'shapeList': [{u'Class': 'CanvasUrlShape',
							   u'MimeType': u'application/vnd.nextthought.canvasurlshape',
							   u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()


		json_data = json.serialize( data )

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
		canvas_data = {u'Class': 'Canvas',
					   'ContainerId': 'tag:foo:bar',
					   u'MimeType': u'application/vnd.nextthought.canvas',
					   'shapeList': [{u'Class': 'CanvasUrlShape',
									  u'MimeType': u'application/vnd.nextthought.canvasurlshape',
									  u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}
		data = {'Class': 'Note',
				'ContainerId': 'tag:foo:bar',
				u'MimeType': u'application/vnd.nextthought.note',
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


		assert_that( res.json_body, has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/FriendsLists/boom%40nextthought.com' ) )

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

		assert_that( res.json_body, has_entry( 'href', is_('/dataserver2/users/sjohnson%40nextthought.com/FriendsLists/boom%40nextthought.com' ) ))

		testapp.delete( str(res.json_body['href']), extra_environ=self._make_extra_environ() )

	@WithSharedApplicationMockDS
	def test_post_friendslist_friends_field(self):
		#"We can put to ++fields++friends"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user('troy.daley@nextthought.com')
		testapp = TestApp( self.app )
		# Make one
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["steve.johnson@nextthought.com"],"realname":"boom"}'
		path = '/dataserver2/users/sjohnson@nextthought.com'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )

		now = time.time()

		# Edit it
		data = '["troy.daley@nextthought.com"]'
		path = res.json_body['href'] + '/++fields++friends'

		res = testapp.put( str(path),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'friends', has_item( has_entry( 'Username', 'troy.daley@nextthought.com' ) ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

		# the object itself is uncachable as far as HTTP goes
		assert_that( res, has_property( 'last_modified', none() ) )
		# But the last modified value is preserved in the body, and did update
		# when we PUT
		assert_that( res.json_body, has_entry( 'Last Modified', greater_than( now ) ) )

		# We can fetch the object and get the same info
		last_mod = res.json_body['Last Modified']
		href = res.json_body['href']

		res = testapp.get( href, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body,	has_entries( 'Last Modified', last_mod, 'href', href ) )

		# And likewise for the collection
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body['Items'], has_entry( 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-MeetingRoom:Group-boom@nextthought.com',
														has_entries( 'Last Modified', last_mod,
																	 'href', href ) ) )

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

		# It is visible to the member in a few places
		resolved_member_res = testapp.get( '/dataserver2/ResolveUser/troy.daley@nextthought.com',
										extra_environ=self._make_extra_environ( username='troy.daley@nextthought.com' ) )
		resolved_member = resolved_member_res.json_body['Items'][0]

		for k in ('DynamicMemberships', 'following', 'Communities'):
			assert_that( resolved_member, has_entry( k, has_item(
														has_entry( 'Username', contains_string( 'boom@nextthought.com' ) ) ) ) )

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

		# And it is no longer visible to the ex-member
		resolved_member_res = testapp.get( '/dataserver2/ResolveUser/troy.daley@nextthought.com',
										extra_environ=self._make_extra_environ( username='troy.daley@nextthought.com' ) )
		resolved_member = resolved_member_res.json_body['Items'][0]

		for k in ('DynamicMemberships', 'following', 'Communities'):
			assert_that( resolved_member, has_entry( k, does_not( has_item(
																has_entry( 'Username', contains_string( 'boom@nextthought.com' ) ) ) ) ) )


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

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		path = urllib.quote( path )
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
		path = urllib.quote( path )
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
										'/dataserver2/Objects/' + urllib.quote( n_ext_id ) + '/@@like' ) ) ) )

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
		path = urllib.quote( path )
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

		_ = testapp.put( urllib.quote( field_path ),
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

		_ = testapp.post( urllib.quote( path ),
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

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		field_path = path + '/++fields++sharedWith' # The name of the external field

		res = testapp.put( urllib.quote( field_path ),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" } )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.json_body, has_entry( "sharedWith", has_item( "Everyone" ) ) )

		assert_that( res.json_body, has_entry( 'href', urllib.quote( path ) ) )
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
		res = testapp.get( urllib.quote( field_path ),
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( "Username", is_( username )))

		# Update to field is ignored
		res = testapp.put( urllib.quote( field_path ),
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

				res = testapp.put( urllib.quote( field_path ),
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

			res = testapp.put( urllib.quote( path ),
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

	@WithSharedApplicationMockDS(users=True,testapp=True,default_authenticate=True)
	def test_transaction_tween_abort_ioerror(self):
		# Commonly seen on socketio XHR post. If
		# the wsgi.input raises an IOError, we don't 500

		class Input(object):
			def read(self, *args):
				raise IOError("unexpected end of file while reading request at position 0")
			# Make webtest lint happy
			readline = read
			readlines = readline
			def __iter__(self):
				return []

		environ = {b'wsgi.input': Input(),
				   b'REQUEST_METHOD': 'POST',
					}
		request = self.testapp.RequestClass.blank( '/socket.io/1/xhr-polling/0x22b3caa6de7a12d2',
												   environ )
		self.testapp.do_request( request,
								 status=400, # Bad Request
								 expect_errors=False)




from pyramid import traversal

class _ApplicationLibraryTestLayer(ApplicationTestLayer):

	@classmethod
	def setUp(cls):
		# Must implement!
		pass

	@classmethod
	def tearDown(cls):
		# Must implement!
		pass

	@classmethod
	def testSetUp(cls, test=None):
		test = test or find_test()
		cls.cur_lib = test.config.registry.queryUtility(lib_interfaces.IContentPackageLibrary)
		cls.new_lib = test._setup_library()
		test.config.registry.registerUtility( cls.new_lib )

	@classmethod
	def testTearDown(cls):
		test = find_test()
		test.config.registry.unregisterUtility(cls.new_lib, lib_interfaces.IContentPackageLibrary)
		if cls.cur_lib is not None and test.config.registry is component.getGlobalSiteManager():
			test.config.registry.registerUtility(cls.cur_lib, lib_interfaces.IContentPackageLibrary)

		del cls.cur_lib
		del cls.new_lib

class TestApplicationLibraryBase(ApplicationLayerTest):
	layer = _ApplicationLibraryTestLayer

	_check_content_link = True
	_stream_type = 'Stream'
	child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='HTML' )
	child_ordinal = 0

	def _setup_library(self, content_root='/prealgebra/', lastModified=None):
		test_self = self
		@interface.implementer( lib_interfaces.IContentUnit )
		class NID(object):
			ntiid = test_self.child_ntiid
			href = 'sect_0002.html'
			ordinal = test_self.child_ordinal
			__parent__ = None
			__name__ = 'The name'
			lastModified = 1
			def __init__( self ):
				self.siblings = dict()

			def with_parent( self, p ):
				self.__parent__ = p
				return self

			def does_sibling_entry_exist( self, sib_name ):
				return self.siblings.get( sib_name )

			def __conform__( self, iface ):
				if iface == lib_interfaces.IContentUnitHrefMapper:
					return NIDMapper( self )

		@interface.implementer(lib_interfaces.IContentUnitHrefMapper)
		class NIDMapper(object):
			def __init__( self, context ):
				root_package = traversal.find_interface( context, lib_interfaces.IContentPackage )
				href = root_package.root + '/' + context.href
				href = href.replace( '//', '/' )
				if not href.startswith( '/' ):
					href = '/' + href

				self.href = href

		class LibEnt(object):
			interface.implements( lib_interfaces.IContentPackage )
			root = content_root
			ntiid = test_self.child_ntiid
			ordinal = test_self.child_ordinal
			__parent__ = None


		if lastModified is not None:
			NID.lastModified = lastModified
			LibEnt.lastModified = lastModified

		class Lib(object):
			interface.implements( lib_interfaces.IContentPackageLibrary )
			titles = ()
			contentPackages = ()

			def __getitem__(self, key):
				if key != test_self.child_ntiid:
					raise KeyError( key )
				return NID().with_parent( LibEnt() )

			def pathToNTIID( self, ntiid ):
				return [NID().with_parent( LibEnt() )] if ntiid == test_self.child_ntiid else None

		return Lib()

	@WithSharedApplicationMockDS
	def test_library_accept_json(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app, extra_environ=self._make_extra_environ() )

		for accept_type in ('application/json','application/vnd.nextthought.pageinfo','application/vnd.nextthought.pageinfo+json'):

			res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
							   headers={"Accept": accept_type} )
			assert_that( res.status_int, is_( 200 ) )

			assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
			assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
			if self._check_content_link:
				assert_that( res.json_body, has_entry( 'Links', has_item( all_of( has_entry( 'rel', 'content' ),
																				  has_entry( 'href', '/prealgebra/sect_0002.html' ) ) ) ) )

			assert_that( res.json_body, has_entry( 'Links', has_item( all_of( has_entry( 'rel', self._stream_type ),
																			  has_entry( 'href',
																						 urllib.quote(
																						 '/dataserver2/users/sjohnson@nextthought.com/Pages(' + self.child_ntiid + ')/' + self._stream_type ) ) ) ) ) )


class TestApplicationLibrary(TestApplicationLibraryBase):

	@WithSharedApplicationMockDS
	def test_library_redirect(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )
		# Unauth gets nothing
		testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, status=401 )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 303 ) )
		assert_that( res.headers, has_entry( 'Location', 'http://localhost/prealgebra/sect_0002.html' ) )

	@WithSharedApplicationMockDS
	def test_library_redirect_with_fragment(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp( self.app )


		fragment = "#fragment"
		ntiid = self.child_ntiid + fragment
		res = testapp.get( '/dataserver2/NTIIDs/' + ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 303 ) )
		assert_that( res.headers, has_entry( 'Location', 'http://localhost/prealgebra/sect_0002.html' ) )

	@WithSharedApplicationMockDS
	def test_library_accept_link(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={"Accept": "application/vnd.nextthought.link+json"},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.link+json' ) )
		assert_that( res.json_body, has_entry( 'href', '/prealgebra/sect_0002.html' ) )

	@WithSharedApplicationMockDS
	def test_directly_set_page_shared_settings_using_field(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			# First, we must put an object so we have a container
			note = contenttypes.Note()
			note.containerId = self.child_ntiid
			user.addContainedObject( note )

		# Ensure we have modification dates on our _NTIIDEntries
		# so that our trump behaviour works as expected
		self.config.registry.registerUtility( self._setup_library(lastModified=1000) )
		accept_type = 'application/json'
		testapp = TestApp( self.app )
		# To start with, there is no modification info
		res = testapp.get( str('/dataserver2/Objects/' + self.child_ntiid),
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( 1000, webob.datetime_utils.UTC ) ) )
		orig_etag = res.etag

		data = json.dumps( {"sharedWith": ["a@b"] } )
		now = datetime.datetime.now(webob.datetime_utils.UTC)
		now = now.replace( microsecond=0 )

		res = testapp.put( str('/dataserver2/Objects/' + self.child_ntiid + '/++fields++sharingPreference'),
						   data,
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
		assert_that( res.content_location, is_( UQ('/dataserver2/Objects/' + self.child_ntiid ) ))
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )
		assert_that( res.json_body, has_entry( 'href', '/dataserver2/Objects/' + self.child_ntiid ) )
		# Now there is modification
		assert_that( res.last_modified, is_( greater_than_or_equal_to( now ) ) )
		last_mod = res.last_modified
		# And it is maintained
		res = testapp.get( str('/dataserver2/NTIIDs/' + self.child_ntiid),
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( last_mod ) )

		# We can make a conditional request, and it doesn't match
		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={'Accept': accept_type, 'If-None-Match': orig_etag},
						   extra_environ=self._make_extra_environ(),
						   status=200)
		assert_that( res.etag, is_not( orig_etag ) )



class TestApplicationLibraryNoSlash(TestApplicationLibrary):

	def _setup_library(self, *args, **kwargs):
		return super(TestApplicationLibraryNoSlash,self)._setup_library( content_root="prealgebra", **kwargs )

class TestRootPageEntryLibrary(TestApplicationLibraryBase):
	child_ntiid = ntiids.ROOT
	_check_content_link = False
	_stream_type = 'RecursiveStream'


	@WithSharedApplicationMockDS
	def test_set_root_page_prefs_inherits(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp( self.app )

		# First, put to the root
		now = datetime.datetime.now(webob.datetime_utils.UTC)
		now = now.replace( microsecond=0 )

		accept_type = 'application/json'
		data = json.dumps( {"sharedWith": ["a@b"] } )
		res = testapp.put( str('/dataserver2/NTIIDs/' + ntiids.ROOT + '/++fields++sharingPreference'),
						   data,
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )
		assert_that( res.json_body, has_entry( 'href', '/dataserver2/Objects/' + ntiids.ROOT ) )

		# Then, reset the library so we have a child, and get the child
		self.child_ntiid = TestApplicationLibrary.child_ntiid
		self.config.registry.registerUtility( self._setup_library() )

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={"Accept": accept_type },
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )
		# Now there is modification
		assert_that( res.last_modified, is_( greater_than_or_equal_to( now ) ) )


import nti.appserver._util

class TestUtil(unittest.TestCase):
	def test_dump_stacks(self):
		seq = nti.appserver._util.dump_stacks()

		assert_that( seq, has_item( contains_string( 'dump_stacks' ) ) )

class TestAppUtil(ApplicationLayerTest):
	@WithSharedApplicationMockDS
	def test_database(self):
		seq = nti.appserver._util.dump_database_cache(gc=True)
		assert_that( seq, has_item( contains_string( 'Database' ) ) )
