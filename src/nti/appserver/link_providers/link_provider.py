#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Link providers

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.annotation.interfaces import IAnnotations

from nti.appserver._util import link_belongs_to_user

from nti.appserver.link_providers.interfaces import IDeletableLinkProvider
from nti.appserver.link_providers.interfaces import IAuthenticatedUserLinkProvider

from nti.containers.dicts import LastModifiedDict

from nti.links.links import Link

#: The name of a view. We will construct links to it, with the actual link name
#: in the sub-path
VIEW_NAME_NAMED_LINKS = 'NamedLinks'

#: Containing a mapping
_GENERATION_LINK_KEY = __name__ + '.LinkGenerations'


def _make_link(user, link_rel, field=None, view_named=None, mime_type=None):
    if field:
        elements = ("++fields++" + field,)
    elif view_named:
        elements = ("@@" + view_named,)
    else:
        # We must handle it
        elements = ("@@" + VIEW_NAME_NAMED_LINKS, link_rel)
    link = Link(user,
                rel=link_rel,
                elements=elements,
                target_mime_type=mime_type)
    link_belongs_to_user(link, user)
    return link
make_link = _make_link


@interface.implementer(IAuthenticatedUserLinkProvider)
class LinkProvider(object):
    """
    A basic named link provider that can provide a single link.
    The link can represent a named pyramid view, a field on the user,
    an external URL, or something stateful managed within this package.

    Meant to be configured declaratively.
    """

    __slots__ = ('user', 'request', '__name__', 'field',
                 'view_named', 'url', 'mime_type')

    def __init__(self, user, request, name=None, **kwargs):
        self.user = user
        self.request = request
        self.__name__ = name
        for k in LinkProvider.__slots__:
            if getattr(self, k, None) is None:
                setattr(self, k, kwargs.pop(k, None))
        if kwargs:
            raise TypeError("Unknown keyword args", kwargs)

    def get_links(self):
        link = self._make_link_with_rel(self.__name__)
        return (link,)

    def _make_link_with_rel(self, rel):
        link = _make_link(self.user, rel, self.field,
                          self.view_named, self.mime_type)
        link._v_provided_by = self
        return link

    def __repr__(self):
        return "<%s %s %s>" % (self.__class__.__name__, 
                               self.__name__, self.url)


@interface.implementer(IDeletableLinkProvider)
class GenerationalLinkProvider(LinkProvider):
    """
    A stateful link provider that tracks some value for a user. If the user's
    current value is less than the required value, the link is provided.
    When "deleted", the user's value is set to the current minimum so that in the
    future, when a new minimum is established, the user again receives the link.

    Meant to be configured declaratively.
    """

    __slots__ = ('minGeneration',)

    def __init__(self, *args, **kwargs):
        self.minGeneration = kwargs.pop('minGeneration')
        super(GenerationalLinkProvider, self).__init__(*args, **kwargs)

    def get_links(self):
        link_dict = IAnnotations(self.user).get(_GENERATION_LINK_KEY, {})
        if link_dict.get(self.__name__, '') < self.minGeneration:
            # They either don't have it, or they have less than needed
            return super(GenerationalLinkProvider, self).get_links()
        # They have it and its up to date!
        return ()

    def delete_link(self, link_name):
        assert link_name == self.__name__
        link_dict = IAnnotations(self.user).get(_GENERATION_LINK_KEY)
        if link_dict is None:
            link_dict = LastModifiedDict()
            IAnnotations(self.user)[_GENERATION_LINK_KEY] = link_dict
        link_dict[self.__name__] = self.minGeneration
