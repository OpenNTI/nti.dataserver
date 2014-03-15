#!/Sr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import contains_string
from hamcrest import not_none
from hamcrest import is_
from hamcrest import contains


from nti.app.testing.layers  import AppLayerTest
from .._default_template_mailer import create_simple_html_text_email
from .._default_template_mailer import _pyramid_message_to_message
from .._default_template_mailer import _principal_ids_from_addr

from ..interfaces import IEmailAddressable
from zope.security.interfaces import IPrincipal

from zope import interface
from zope.publisher.interfaces.browser import IBrowserRequest



class TestEmail(AppLayerTest):

	def test_create_mail_message_with_non_ascii_name(self):
		class User(object):
			username = 'the_user'

		class Profile(object):
			realname = 'Suzë Schwartz'


		@interface.implementer(IBrowserRequest)
		class Request(object):
			context = None
			response = None
			application_url = 'foo'


		user = User()
		profile = Profile()
		request = Request()
		request.context = user

		msg = create_simple_html_text_email('new_user_created',
											subject='Hi there',
											recipients=['jason.madden@nextthought.com'],
											template_args={'user': user, 'profile': profile, 'context': user },
											package='nti.appserver',
											request=request)
		assert_that( msg, is_( not_none() ))

		base_msg = _pyramid_message_to_message(msg, ['jason.madden@nextthought.com'], None)

		base_msg_string = str(base_msg)
		# quoted-prinatble encoding of iso-8859-1 value of umlaut-e
		assert_that( base_msg_string, contains_string('Hi=20Suz=EB=20Schwartz') )

		# Because we can't get to IPrincial, no VERP info
		assert_that( msg.sender, is_('"NextThought" <no-reply@nextthought.com>') )


	def test_create_email_with_verp(self):
		@interface.implementer(IPrincipal, IEmailAddressable)
		class User(object):
			username = 'the_user'
			id = 'the_user'
			email = 'thomas.stockdale@nextthought.com' # this address encodes badly to simple base64

		class Profile(object):
			realname = 'Suzë Schwartz'


		@interface.implementer(IBrowserRequest)
		class Request(object):
			context = None
			response = None
			application_url = 'foo'


		user = User()
		profile = Profile()
		request = Request()
		request.context = user

		msg = create_simple_html_text_email('new_user_created',
											subject='Hi there',
											recipients=[user],
											template_args={'user': user, 'profile': profile, 'context': user },
											package='nti.appserver',
											request=request)
		assert_that( msg, is_( not_none() ))
		#import pyramid_mailer
		#from pyramid_mailer.interfaces import IMailer
		#from zope import component
		#mailer = pyramid_mailer.Mailer.from_settings( {'mail.queue_path': '/tmp/ds_maildir', 'mail.default_sender': 'no-reply@nextthought.com' } )
		#component.provideUtility( mailer, IMailer )
		#component.provideUtility(mailer.queue_delivery)
		#from .._default_template_mailer import _send_mail
		#_send_mail(msg, [user], None)
		#import transaction
		#transaction.commit()

		_pyramid_message_to_message(msg, [user], None)

		# we can get to IPrincipal, so we have VERP
		# The first part will be predictable, the rest won't
		assert_that( msg.sender, contains_string('"NextThought" <no-reply+dGhlX3Vz') )

	def test_pids_from_verp_email(self):
		fromaddr = 'no-reply+a2FsZXkud2hpdGVAbmV4dHRob3VnaHQuY29tLjV4cXAyeTRoVURlMGVvOGtoXzM5SURZNlR4aw@nextthought.com'

		pids = _principal_ids_from_addr(fromaddr, 'alpha.nextthought.com')
		assert_that( pids, contains('kaley.white@nextthought.com'))

		fromaddr = 'no-reply+TGV4aVpvbGwuLWJOUlNZVS1ZV3FEanFvUi10dGRkLV82R01z@nextthought.com'
		pids = _principal_ids_from_addr(fromaddr, 'mathcounts.nextthought.com')
		assert_that( pids, contains('LexiZoll'))

		pids = _principal_ids_from_addr(fromaddr)
		assert_that( pids, is_(()))
