#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import has_key
from hamcrest import greater_than_or_equal_to
from hamcrest import none
from hamcrest import is_not
does_not = is_not
from hamcrest import has_property
from hamcrest import contains_string

from zope import component
from zope.component import eventtesting

import uuid
import stripe
import anyjson as json

from quopri import decodestring

from nti.store.payments.stripe.processor.tests import create_purchase
from nti.dataserver.tests import mock_dataserver

from nti.store import interfaces as store_interfaces

from nti.testing.matchers import is_empty

from nti.app.testing.testing import ITestMailDelivery
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from . import ApplicationStoreTestLayer

class TestApplicationStoreViews(ApplicationLayerTest):
	layer = ApplicationStoreTestLayer

	def setUp(self):
		super(TestApplicationStoreViews, self).setUp()
		self.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

	def tearDown(self):
		stripe.api_key = self.api_key
		super(TestApplicationStoreViews, self).tearDown()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_get_purchasables(self):
		url = '/dataserver2/store/get_purchasables'
		res = self.testapp.get(url, status=200)
		json_body = res.json_body
		assert_that(json_body, has_key('Items'))
		assert_that(json_body, has_entry('Last Modified', 0))
		items = json_body['Items']
		assert_that(items, has_length(greater_than_or_equal_to(1)))

		item = items[0]
		assert_that(item, has_entry('NTIID', "tag:nextthought.com,2011-10:CMU-HTML-04630_main.04_630:_computer_science_for_practicing_engineers"))
		assert_that(item, has_key('StripeConnectKey'))
		sck = item['StripeConnectKey']
		assert_that(sck, has_entry('Alias', 'CMU'))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_get_stripe_key(self):
		url = '/dataserver2/store/get_stripe_connect_key'
		params = {'provider':'NTI-TEST'}
		res = self.testapp.get(url, params, status=200)
		json_body = res.json_body
		assert_that(json_body, has_entry(u'Alias', u'NTI-TEST'))
		assert_that(json_body, has_entry(u'Class', u'StripeConnectKey'))
		assert_that(json_body, has_entry(u'MimeType', u'application/vnd.nextthought.stripeconnectkey'))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_price_item(self):
		url = '/dataserver2/store/price_purchasable_with_stripe_coupon'
		params = {'purchasableID':"tag:nextthought.com,2011-10:CMU-HTML-04630_main.04_630:_computer_science_for_practicing_engineers",
				  'quantity':2}
		body = json.dumps(params)

		res = self.testapp.post(url, body, status=200)
		json_body = res.json_body
		assert_that(json_body, has_entry('Quantity', 2))
		assert_that(json_body, has_entry('Amount', 300.0))
		assert_that(json_body, has_entry('Currency', 'USD'))
		assert_that(json_body, has_entry('PurchasePrice', 600.0))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_price_with_stripe_copoun(self):
		code = str(uuid.uuid4())
		stripe.Coupon.create(percent_off=10, duration='forever', id=code)

		url = '/dataserver2/store/price_purchasable_with_stripe_coupon'
		params = {'coupon':code,
				  'purchasableID':"tag:nextthought.com,2011-10:CMU-HTML-04630_main.04_630:_computer_science_for_practicing_engineers"}
		body = json.dumps(params)

		res = self.testapp.post(url, body, status=200)
		json_body = res.json_body
		assert_that(json_body, has_entry('Quantity', 1))
		assert_that(json_body, has_entry('PurchasePrice', 270.0))
		assert_that(json_body, has_entry('NonDiscountedPrice', 300.0))
		assert_that(json_body, has_key('Coupon'))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_get_purchase_history(self):
		url = '/dataserver2/store/get_purchase_history'
		res = self.testapp.get(url, status=200)
		json_body = res.json_body
		assert_that(json_body, has_key('Items'))
		assert_that(json_body, has_entry('Last Modified', greater_than_or_equal_to(0)))
		items = json_body['Items']
		assert_that(items, has_length(greater_than_or_equal_to(0)))

	def _get_pending_purchases(self):
		url = '/dataserver2/store/get_pending_purchases'
		res = self.testapp.get(url, status=200)
		json_body = res.json_body
		assert_that(json_body, has_key('Items'))
		assert_that(json_body, has_entry('Last Modified', greater_than_or_equal_to(0)))
		items = json_body['Items']
		return items

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_get_pending_purchases(self):
		items = self._get_pending_purchases()
		assert_that(items, has_length(greater_than_or_equal_to(0)))

	def _create_stripe_token(self):
		url = '/dataserver2/store/create_stripe_token'
		params = dict(cc="5105105105105100",
					  exp_month="11",
					  exp_year="30",
					  cvc="542",
					  address="3001 Oak Tree #D16",
					  city="Norman",
					  zip="73072",
					  state="OK",
					  country="USA",
					  provider='NTI-TEST')
		body = json.dumps(params)

		res = self.testapp.post(url, body, status=200)
		json_body = res.json_body
		assert_that(json_body, has_entry('Token', is_not(none())))
		return json_body['Token']

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_post_stripe_payment(self):
		# create token
		t = self._create_stripe_token()

		url = '/dataserver2/store/post_stripe_payment'
		params = {'purchasableID':'tag:nextthought.com,2011-10:CMU-HTML-04630_main.04_630:_computer_science_for_practicing_engineers',
				  'amount': 300,
				  'token': t}
		body = json.dumps(params)

		res = self.testapp.post(url, body, status=200)

		json_body = res.json_body

		assert_that(json_body, has_key('Items'))
		assert_that(json_body, has_entry('Last Modified', greater_than_or_equal_to(0)))
		items = json_body['Items']
		assert_that(items, has_length(1))
		purchase = items[0]
		assert_that(purchase, has_key('Order'))
		assert_that(purchase['Order'], has_entry('Items', has_length(1)))

		import gevent

		items = self._get_pending_purchases()
		assert_that(items, has_length(greater_than_or_equal_to(1)))
		# And we can let the greenlet run which will empty out the queue
		gevent.sleep(0)
		items = self._get_pending_purchases()
		assert_that(items, is_empty() )

	@WithSharedApplicationMockDS
	def test_confirmation_email(self):
		from nti.appserver.interfaces import IApplicationSettings
		settings = component.getUtility(IApplicationSettings)
		settings['purchase_additional_confirmation_addresses'] = 'foo@bar.com\nbiz@baz.com'

		with mock_dataserver.mock_db_trans(self.ds):
			manager = component.getUtility(store_interfaces.IPaymentProcessor, name='stripe')
			# TODO: Is this actually hitting stripe external services? If
			# so, we need to mock that! This should be easy to do with fudge
			username, _, _, _ = create_purchase(self, item='tag:nextthought.com,2011-10:CMU-HTML-04630_main.04_630:_computer_science_for_practicing_engineers',
														  amount=300 * 5,
														  quantity=5,
														  manager=manager,
														  username='jason.madden@nextthought.com')


			assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptSuccessful),
						has_length(1))
			event = eventtesting.getEvents(store_interfaces.IPurchaseAttemptSuccessful)[0]
			purchase = event.object

			mailer = component.getUtility( ITestMailDelivery )
			assert_that( mailer.queue, has_length( 3 ) ) # One to the user, one to each additional
			msg = mailer.queue[0]

			assert_that( msg, has_property( 'body'))
			body = decodestring(msg.body)
			assert_that( body, contains_string( username ) )
			assert_that( body, contains_string( 'Activation Key' ) )
			assert_that( body, contains_string( '(1 Year License)' ) )
			assert_that( body, contains_string( '5x 04-630: Computer Science for Practicing Engineers - US$300.00 each' ) )
			assert_that( body, does_not( contains_string( '\xa4300.00' ) ) )
	#		import codecs
	#		with codecs.open('/tmp/file.html', 'w', encoding='utf-8') as f:
	#			f.write( msg.html )
	#		print(msg.body)
	#		print(msg.html)
			assert_that( msg, has_property( 'html'))
			html = decodestring(msg.html)
			assert_that( html, contains_string( username ) )
			assert_that( html, contains_string( '(1 Year License)' ) )
			assert_that( html, contains_string( '04-630: Computer Science for Practicing Engineers' ) )
			assert_that( html, contains_string( 'US$300.00' ) )

			# Send the event again, this time with a discount
			del mailer.queue[:]

			purchase.Pricing.TotalPurchasePrice = 100.0

			# The intid is bad because create_purchase actually runs its own transaction
			# so the intid utility ghosts it...fix that
			from zc.intid import IIntIds
			ids = component.getUtility(IIntIds)
			ids.refs[purchase._ds_intid] = purchase
			from ..views import _purchase_attempt_successful

			_purchase_attempt_successful(event)
			assert_that( mailer.queue, has_length( 1 ) )
			msg = mailer.queue[0]
			assert_that( msg, has_property( 'body'))
			body = decodestring(msg.body)
			assert_that( body, contains_string( 'Discount' ) )

			assert_that( msg, has_property( 'html'))
			html = decodestring(msg.html)
			assert_that( html, contains_string( 'DISCOUNTS' ) )

			import transaction
			transaction.abort()
