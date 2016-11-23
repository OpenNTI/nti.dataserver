=======
 Store
=======

This document talks about how the nextthought store is implemented.

Model
=====

The implementation of the API and storage lives in the
``nti.store`` package.

.. automodule:: nti.store.interfaces

.. automodule:: nti.store.payments

.. automodule:: nti.store.payments.interfaces


Payments
========

This package defines the different ways we implement the purchase of an
content item

Currently there is only one way to process the purchase of an item and it
is done through stripe

Views
=====

The implementation of the external interface for payment lives
in the ``nti.store.payments.pyramid_views`` module.

Payments
--------

In order to accept a paymet through stripe
(see :func:`nti.store.pyramid_views.StripePayment`),
the client application sends a in the POST request the following
token: Hash computed by stripe of the credit card info
ntiid: NTIID of the item to purchase
amount: Amount to charge
currency: Currency amount ISO code (Default to USD)
description: An optional description of the item purchased
If the transaction is successful the TransactionID will be sent
back to the client


.. automodule:: nti.store.payments.pyramid_views
	:members:
	:private-members:
