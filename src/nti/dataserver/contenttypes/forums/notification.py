#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from pyramid.threadlocal import get_current_request

from six.moves import urllib_parse

from zope import component

from zope.i18n import translate

from nti.app.pushnotifications.digest_email import _TemplateArgs

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver.contenttypes.forums import MessageFactory as _

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.links import Link
from nti.links import render_link

from nti.mailer.interfaces import ITemplatedMailer

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def send_creation_notification_email(forum_type_obj,
                                     sender,
                                     receiver_emails,
                                     subject,
                                     message,
                                     request=None):
    from IPython.terminal.debugger import set_trace;set_trace()

    request = request if request else get_current_request()
    if not receiver_emails:
        logger.warn("Not sending an creation email because of no recipient emails")
        return False

    template_args = _TemplateArgs(request=request,
                                  remoteUser=sender,
                                  objs=[forum_type_obj])

    template = 'creation_notification_email'

    policy = component.getUtility(ISitePolicyUserEventListener)

    support_email = getattr(policy, 'SUPPORT_EMAIL', 'support@nextthought.com')
    brand = getattr(policy, 'BRAND', 'NextThought')
    package = getattr(policy, 'PACKAGE', None)

    names = IFriendlyNamed(sender)
    informal_username = names.alias or names.realname or sender.username

    href = render_link(Link(forum_type_obj))
    if href is None:
        logger.warn(u'Unable to generate href for %s' % forum_type_obj)
    forum_type_obj_url = urllib_parse.urljoin(request.application_url, href)

    msg_args = {
        'support_email': support_email,
        'resolve_url': forum_type_obj_url,
        'brand': brand,
    }

    # Tal is not very cooperative for dynamic building up this style
    # so we create and stash it here
    avatar_styles = "float:left;height:40px;width:40px;border-radius:50%%;background-image: url('%s'), url('https://s3.amazonaws.com/content.nextthought.com/images/generic/imageassets/unresolved-user-avatar.png'); background-position: center center;background-size:cover;background-repeat:no-repeat;" % template_args.creator_avatar_url
    msg_args['sender_content'] = {
        'sender': informal_username,
        'message': message,
        'avatar_styles': avatar_styles
    }

    try:
        mailer = component.getUtility(ITemplatedMailer)
        mailer.queue_simple_html_text_email(
            template,
            subject=translate(_(subject)),
            recipients=[receiver_emails],
            template_args=msg_args,
            request=request,
            package=package,
            text_template_extension='.mak')
    except Exception:
        logger.exception("Cannot send creation notification emails")
        return False
    return True
