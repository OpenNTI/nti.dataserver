#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import only_contains

import simplejson as json

from six.moves.urllib_parse import quote
UQ = quote

from zope import interface

from nti.appserver.policies import censor_policies

from nti.appserver.policies.site_policies import GenericSitePolicyEventListener
from nti.appserver.policies.site_policies import UsernameCannotContainNextthoughtCom

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.chatserver.messageinfo import MessageInfo
from nti.chatserver.presenceinfo import PresenceInfo

from nti.contentrange import contentrange

from nti.coremetadata.interfaces import IExemptUsernameUser

from nti.dataserver import contenttypes

from nti.externalization.externalization import to_external_object

from nti.ntiids.oids import to_external_ntiid_oid

from nti.socketio import session_consumer
from nti.socketio import interfaces as sio_interfaces

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.webtest import TestApp

from nti.dataserver.tests import mock_dataserver

# class TestApplicationAssessment(ApplicationTestBase):
#	child_ntiid =  'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'

bad_val      = u'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' ).decode( 'utf-8' )
censored_val = u'This is ******* stupid, you ************ *******'

bad_word      = 'shpxvat'.encode( 'rot13' ).decode( 'utf-8' )
censored_word = u'*******'

class CensorTestMixin(object):

	def _do_test_censor_note( self, containerId, censored=True, extra_ifaces=(), environ=None,
							  bad_val=bad_val, censored_val=censored_val,
							  bad_word=bad_word, censored_word=censored_word,
							  create_user=True):

		with mock_dataserver.mock_db_trans( self.ds ):
			if create_user:
				user = self._create_user()
				for iface in extra_ifaces:
					interface.alsoProvides( user, iface )
			else:
				from nti.dataserver.users import User
				user = User.get_user(self.extra_environ_default_user)

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = containerId
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )

		data = json.dumps( {'body': [bad_val],
							'title': bad_val,
							'tags': [bad_word]} )

		path = b'/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		path = UQ( path )
		extra_environ = self._make_extra_environ()
		if environ:
			extra_environ.update( environ )
		res = testapp.put( path, data, extra_environ=extra_environ )
		assert_that( res.status_int, is_( 200 ) )

		exp_val = censored_val if censored else bad_val
		exp_word = censored_word if censored else bad_word
		__traceback_info__ = res.json_body
		assert_that( res.json_body,
					 has_entries( 'body', only_contains( exp_val ),
								  'title', exp_val,
								  'tags', only_contains( exp_word )) )
_CensorTestMixin = CensorTestMixin

from nti.app.testing.application_webtest import ApplicationLayerTest

class TestApplicationCensoring(CensorTestMixin, ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_censor_note_not_in_library_disabled_by_default(self):
		#"If we post a note to a container we don't recognize, we don't get censored."
		self._do_test_censor_note( 'tag:not_in_library', censored=False )

	@WithSharedApplicationMockDS
	def test_censoring_disabled_by_default( self ):
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology", censored=False )

	@WithSharedApplicationMockDS
	def test_censoring_enabled_in_mathcounts_site(self):
		#"Regardless of who you are this site censors"
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology",
								   censored=True,
								   environ={b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'})
		# Single word body
		data = {'body': ['fuvg'.decode('rot13')],
				'title': 'crap',
				'tags': ['crap'],
				'ContainerId': "tag:nextthought.com,2011-10:mathcounts-HTML-testmathcounts2013.warm_up_1",
				'MimeType': "application/vnd.nextthought.note"}
		extra_environ = self._make_extra_environ()
		extra_environ.update({b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'})
		testapp = TestApp(self.app)
		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Pages', data, extra_environ=extra_environ )

		assert_that( res.json_body,
					 has_entries( 'body', only_contains( '****' ),
								  'title', '****',
								  'tags', only_contains( '****' )) )

		# Single word body, as posted by the app
		data = {"MimeType":"application/vnd.nextthought.note",
				"references":[],
				"applicableRange":{"start":{"role":"start",
											"elementTagName":"IMG",
											"elementId":"e9503dbcfdcbe526b2c5c2ae28dc0567",
											"Class":"ElementDomContentPointer",
											"MimeType":"application/vnd.nextthought.contentrange.elementdomcontentpointer"},
								   "end":{"role":"end",
										  "elementTagName":"IMG",
										  "elementId":"e9503dbcfdcbe526b2c5c2ae28dc0567",
										  "Class":"ElementDomContentPointer",
										  "MimeType":"application/vnd.nextthought.contentrange.elementdomcontentpointer"},
								   "ancestor":{"role":"ancestor",
											   "elementTagName":"DIV",
											   "elementId":"NTIContent",
											   "Class":"ElementDomContentPointer",
											   "MimeType":"application/vnd.nextthought.contentrange.elementdomcontentpointer"},
								   "Class":"DomContentRangeDescription",
								   "MimeType":"application/vnd.nextthought.contentrange.domcontentrangedescription"},
				"body":[b"\xc3\xa2\xe2\x82\xac\xe2\x80\xb9" + bytes(b"fuvg".decode('rot13'))],
				"style":"suppressed",
				"sharedWith":[],
				"ContainerId":"tag:nextthought.com,2011-10:mathcounts-HTML-mathcounts2012.mathcounts_2011_2012_school_handbook"}
		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Pages', data, extra_environ=extra_environ )

		assert_that( res.json_body,
					 has_entries( 'body', only_contains( u'\xe2\u20ac\u2039****' ) ) )

	@WithSharedApplicationMockDS
	def test_create_chat_object_events_copy_owner_from_session(self):

		@interface.implementer(sio_interfaces.ISocketSession)
		class Session(object):
			owner = u'me'

		chat_message = MessageInfo()
		chat_message.body = 'a body'
		# ContainerIDs are required or censoring by default kicks in (depending on config)
		chat_message.containerId = u'tag:foo'

		with mock_dataserver.mock_db_trans(self.ds): # for the entity lookup
			args = session_consumer._convert_message_args_to_objects( None, Session(), { 'args': [to_external_object( chat_message )] } )

		assert_that( args[0], is_( MessageInfo ) )
		assert_that( args[0], has_property( 'creator', Session.owner ) )
		args[0].creator = self

		assert_that(censor_policies.creator_and_location_censor_policy('', args[0]),
					is_( none() ) )

	@WithSharedApplicationMockDS
	def test_chat_message_uses_sites_from_session(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			@interface.implementer(sio_interfaces.ISocketSession)
			class Session(object):
				owner = user.username
				originating_site_names = ('mathcounts.nextthought.com','')

			chat_message = MessageInfo()
			chat_message.containerId = u'tag:foo'
			chat_message.body = [bad_val]

			args = session_consumer._convert_message_args_to_objects( None, Session(), { 'args': [to_external_object( chat_message )] } )

			assert_that( args[0], is_( MessageInfo ) )
			assert_that( args[0], has_property( 'creator', Session.owner ) )

			# nti.contentfragments.censor.censor_assign( [bad_val], args[0], 'body' )

			assert_that( args[0], has_property( 'body', only_contains( censored_val ) ) )

	@WithSharedApplicationMockDS
	def test_exempt_nextthought_usernames(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(external_value={u'realname':'aizen nezai'})
			policy = GenericSitePolicyEventListener()
			with self.assertRaises(UsernameCannotContainNextthoughtCom):
				policy.user_will_create(user, None)
			interface.alsoProvides(user, IExemptUsernameUser)
			policy.user_will_create(user, None)

	@WithSharedApplicationMockDS
	def test_presenceinfo_uses_sites_from_session(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()

			@interface.implementer(sio_interfaces.ISocketSession)
			class Session(object):
				owner = user.username
				originating_site_names = ('mathcounts.nextthought.com', '')

			presence = PresenceInfo()
			presence.status = IPlainTextContentFragment(bad_val)

			args = session_consumer._convert_message_args_to_objects(None, Session(), { 'args': [to_external_object(presence)] })

			assert_that(args[0], is_(PresenceInfo))
			assert_that(args[0], has_property('status', censored_val))
