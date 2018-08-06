#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for the sending of bulk emails using `Amazon SES`_.

General Comments
================

The sending of bulk or mass emails is different than the sending of
individual email in a few important ways, mostly related to spam
blocking and the handling of bounced or undeliverable email.

Fighting Spam
-------------

Because of the volume and the standardized text of these emails, they
are more likely to be classified as spam than individual emails. To that
end, we must be sure to take special steps to help avoid that, not only
for the bulk email, but to prevent follow-on effects from damaging the spam
scores applied to our entire domain. These steps include:

* Being sure that DKIM is used for the domain sending email (easily done with
  `SES and Route 53 <http://docs.aws.amazon.com/ses/latest/DeveloperGuide/dkim.html>`_);
* Setting up `SPF <http://openspf.org>`_ for the domain sending email
  (also easily done with 
  `SES and Route 53 <http://docs.aws.amazon.com/ses/latest/DeveloperGuide/spf.html>`_
  --- note that the ``Return-Path`` header is set by SES, no matter if using the SMTP
  or HTTP interface, to an ``amazonses.com`` address, and it is this
  domain that is verified for SPF);
* Using a separate domain for the ``From`` address so as to not "poison"
  the primary domain in spam rankings (in this case, ``alerts.nextthought.com``).

Bounces and Tracking
--------------------

To better be able to understand and track the bounce behaviour of bulk emails,
and to be able to independently control our reaction to bounces (e.g., whether
or not to force users to reset email addresses) we take two important steps.

First, we configure SES to use a separate `Amazon SNS`_ topic for the domain
sending bulk emails. We call this topic ``BulkSESFeedback``, and it feeds a
`Amazon SQS`_ queue also called ``BulkSESFeedback.`` This queue can be polled for
messages separately from ``SESFeedback`` and it may or may not be configured to
send email alerts.

Second, for each email we send, we use a distinct ``From`` address, encoding
some information about the target and purpose of the email. The exact format
is dependent upon the mailer in use, but is encoded in the typical VERP form
as a label.

Process
=======

The basic outline of the process is as follows.

#. In a transaction, gather the set of email addresses to send bulk email to:

	* This may or may not include additional information needed in the email template;
	  if it does, it may mean the remainder of the process is entirely independent of
	  the database (depending on process implementation);
	* Put this information in a specially named Redis set; also
	  put some metadata related to the process in Redis.

#. Next, potentially not in a transaction and probably in a background greenlet:

	* Pop an item off the Redis source set;
	* Construct the email using the desired templates;
	* Use Boto's support for SES to send the raw message; note that this is
	  not done with either :mod:`pyramid_mailer` or :mod:`repoze.sendmail`
	* Place the item from the source set, along with the tracking information
	  from the SES result, in a Redis destination set;
	* Throttle.

The use of the raw SES API is important as we must be careful to stay
within the SES rate limits, which restricts us to sending no more than
5 emails a second (and 10,000 emails in a given 24-hour period)
initially (this grows over time; as of this writing on March 2014 our
limits are 14 emails a second and 50,000 emails/24-hours). If we were
queuing to :mod:`repoze.sendmail`, the queue processor might try to
send too many messages too fast and there is no way to control that.
(However, the flip side is that if this process is consuming the full
rate limit, the background queue processor might fail, so we have to
be conservative.)

.. note::
	We will limit the second step to being non-concurrent
	through Redis locks. In order to properly use the template system
	and site configurations it will run within a configured
	application worker (using a background greenlet)

Transparency
============

The use of the two Redis sets is designed to allow for monitoring and
resumability. A status page can:

* Show the count of messages sent and still to send;
* Allow initiating the entire process;
* Allow starting a sending process (step two);
* Allow resetting both queues so the process can be re-initiated

.. _Amazon SES: http://aws.amazon.com/documentation/ses/
.. _Amazon SNS: http://aws.amazon.com/documentation/sqs/
.. _Amazon SQS: http://aws.amazon.com/documentation/sns/

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
