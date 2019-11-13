#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component

from zope.i18n import translate

# FIXME: break these deps
from nti.appserver.brand.utils import get_site_brand_name

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver.contenttypes.forums import MessageFactory as _

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.mailer.interfaces import ITemplatedMailer

logger = __import__('logging').getLogger(__name__)


def send_creation_notification_email(sender,
                                     receiver_emails,
                                     subject,
                                     message,
                                     forum_type_obj_url,
                                     avatar_url,
                                     request):
    if not receiver_emails:
        logger.warn("Not sending an creation email because of no recipient emails")
        return False

    template = 'creation_notification_email'

    policy = component.getUtility(ISitePolicyUserEventListener)

    support_email = getattr(policy, 'SUPPORT_EMAIL', 'support@nextthought.com')
    brand = get_site_brand_name()
    package = getattr(policy, 'PACKAGE', None)

    names = IFriendlyNamed(sender)
    informal_username = names.alias or names.realname or sender.username

    msg_args = {
        'support_email': support_email,
        'resolve_url': forum_type_obj_url,
        'brand': brand,
        'subject': subject
    }

    # Tal is not very cooperative for dynamic building up this style
    # so we create and stash it here
    avatar_styles = "float:left;height:40px;width:40px;border-radius:50%%;background-image: url('%s'), url('https://s3.amazonaws.com/content.nextthought.com/images/generic/imageassets/unresolved-user-avatar.png'); background-position: center center;background-size:cover;background-repeat:no-repeat;" % avatar_url
    msg_args['sender_content'] = {
        'sender': informal_username,
        'message': message,
        'avatar_styles': avatar_styles,
    }

    try:
        mailer = component.getUtility(ITemplatedMailer)
        mailer.queue_simple_html_text_email(
            template,
            subject=translate(_(subject)),
            recipients=receiver_emails,
            template_args=msg_args,
            request=request,
            package=package,
            text_template_extension='.mak')
    except Exception:
        logger.exception("Cannot send creation notification emails")
        return False
    return True
