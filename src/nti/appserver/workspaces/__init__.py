#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Service document and user workspaces support.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier

from pyramid.threadlocal import get_current_request

from requests.structures import CaseInsensitiveDict

from six.moves import urllib_parse

from zope import component
from zope import interface

from zope.authentication.interfaces import IUnauthenticatedPrincipal

from zope.cachedescriptors.property import Lazy

from zope.container.constraints import IContainerTypesConstraint

from zope.location.interfaces import ILocation
from zope.location.interfaces import IContained

from zope.location.location import Location

from zope.mimetype.interfaces import IContentTypeAware

from zope.schema.interfaces import IVocabularyFactory

from zope.security.interfaces import IPrincipal

from nti.app.authentication import get_remote_user

from nti.app.renderers.interfaces import IExternalCollection
from nti.app.renderers.interfaces import IPreRenderResponseCacheController

from nti.appserver.interfaces import MissingRequest

from nti.appserver.interfaces import INTIIDEntry
from nti.appserver.interfaces import INamedLinkView
from nti.appserver.interfaces import INamedLinkPathAdapter
from nti.appserver.interfaces import IUserViewTokenCreator
from nti.appserver.interfaces import IPageContainerResource
from nti.appserver.interfaces import IRootPageContainerResource

from nti.appserver.workspaces.interfaces import IService
from nti.appserver.workspaces.interfaces import IWorkspace
from nti.appserver.workspaces.interfaces import ICollection
from nti.appserver.workspaces.interfaces import IUserService
from nti.appserver.workspaces.interfaces import IUserWorkspace
from nti.appserver.workspaces.interfaces import IGlobalCollection
from nti.appserver.workspaces.interfaces import IWorkspaceValidator
from nti.appserver.workspaces.interfaces import IContainerCollection
from nti.appserver.workspaces.interfaces import IUserWorkspaceLinkProvider
from nti.appserver.workspaces.interfaces import IGlobalWorkspaceLinkProvider

from nti.coremetadata.interfaces import IDeactivatedDynamicSharingTargetFriendsList

from nti.dataserver import authorization

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import EVERYONE_GROUP_NAME

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IContainerIterable
from nti.dataserver.interfaces import IFriendsListContainer
from nti.dataserver.interfaces import IHomogeneousTypeContainer
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IHiddenMembership
from nti.dataserver.users.interfaces import IDisallowMembershipOperations

from nti.dataserver.users.users import User

from nti.datastructures.datastructures import LastModifiedCopyingUserList

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.links import links

from nti.mimetype.mimetype import nti_mimetype_with_class
from nti.mimetype.mimetype import nti_mimetype_from_object

from nti.ntiids import ntiids

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.traversal.traversal import find_interface


ITEMS = StandardExternalFields.ITEMS

logger = __import__('logging').getLogger(__name__)

#: The :class:``ICatalogCollection`` popular items view.
VIEW_CATALOG_POPULAR = 'Popular'

#: The :class:``ICatalogCollection`` featured items view.
VIEW_CATALOG_FEATURED = 'Featured'


def _find_name(obj):
    return getattr(obj, 'name', None) \
        or getattr(obj, '__name__', None) \
        or getattr(obj, 'container_name', None)


class _ContainerWrapper(object):
    """
    An object wrapping a container. Location aware.

    If the container is location aware, we will default to using its
    parent and its name. If the container happens to be a
    :class:`INamedContainer` we will use that name as a
    last resort. This can be overridden.
    """

    _name_override = None

    def __init__(self, container):
        self._container = container
        self.__parent__ = getattr(container, '__parent__', None)

    def name(self):
        return self._name_override or _find_name(self._container)

    def set__name__(self, s):
        self._name_override = s
    __name__ = property(name, set__name__)
    name = property(name)


def _collections(self, containers):
    """
    A generator iterating across the containers turning
    each into an ICollection.
    """
    for x in containers or ():
        # Verify that only the first part is needed, because
        # the site manager hooks are properly installed at runtime.
        # See the test package for info.
        adapt = ICollection(x, None) or component.queryAdapter(x, ICollection)
        if not adapt:
            continue
        adapt.__parent__ = self  # Right?
        yield adapt


@interface.implementer(IWorkspace)
@component.adapter(IContainerIterable)
class ContainerEnumerationWorkspace(_ContainerWrapper):
    """
    A workspace wrapping a container. Location aware.

    If the container is location aware, we will default to using its
    parent and its name. If the container happens to be a :class:`INamedContainer`
    we will use that name as a last resort. This can be overridden.
    """

    @property
    def collections(self):
        if hasattr(self._container, "iter_containers"):
            return _collections(self, self._container.iter_containers())
        return _collections(self, self._container.itercontainers())  # legacy


@interface.implementer(IContainerCollection)
@component.adapter(IHomogeneousTypeContainer)
class HomogeneousTypedContainerCollection(_ContainerWrapper):

    @property
    def accepts(self):
        return (self._container.contained_type,)

    @property
    def container(self):
        return self._container


class _AbstractPseudoMembershipContainer(_ContainerWrapper):

    def __init__(self, user_workspace):
        super(_AbstractPseudoMembershipContainer, self).__init__(user_workspace)
        try:
            self._user = user_workspace.user
        except AttributeError:
            self._user = user_workspace.__parent__
        self.__parent__ = self._user

    @property
    def remote_user(self):
        return get_remote_user()

    @property
    def accepts(self):
        return ()

    @property
    def memberships(self):
        """
        Subclasses should override this to define membership.
        """
        return ()

    @property
    def last_modified(self):
        return None

    def selector(self, obj):
        """
        Subclasses should override this to filter membership objects.
        """
        _same_as_authenticated = _is_remote_same_as_authenticated(self._user)
        if _same_as_authenticated:
            return True
        else:
            hidden = IHiddenMembership(obj, None) or ()
            return not self in hidden

    def get_filtered_memberships(self):
        result = [x for x in self.memberships if self.selector(x)]
        return result

    def get_last_modified(self, vals):
        last_mod = self.last_modified
        if last_mod is None:
            # If we don't have a container, best guess.
            # This isn't quite right, if we lose an older
            # membership, the last mod could still stay
            # the same.
            try:
                last_mod = max(
                    x.lastModified for x in vals if getattr(x, 'lastModified', 0)
                )
            except ValueError:
                pass
        return last_mod or None

    def _caching_headers(self, result):
        # This isn't ideal.  See .externalization.py.
        # Since we don't go through the renderer, we have to specify
        # our caching here.
        request = get_current_request()
        if request is not None:
            interface.alsoProvides(result, IExternalCollection)
            IPreRenderResponseCacheController(result)(result, {'request': request})

    @property
    def container(self):
        memberships = self.get_filtered_memberships()
        result = LocatedExternalDict()
        for membership in memberships:
            result[membership.NTIID] = membership
        result.__name__ = self.name
        result.__parent__ = self._user
        result.lastModified = self.get_last_modified(memberships)
        self._caching_headers(result)
        return result
AbstractPseudoMembershipContainer = _AbstractPseudoMembershipContainer


class NameFilterableMixin(object):

    @property
    def params(self):
        request = get_current_request()
        return CaseInsensitiveDict(**request.params) if request else {}

    @Lazy
    def searchTerm(self):
        # pylint: disable=no-member
        params = self.params
        result = params.get('searchTerm') or params.get('filter')
        return urllib_parse.unquote(result).lower() if result else None

    def search_prefix_match(self, compare, search_term):
        compare = compare.lower() if compare else ''
        for k in compare.split():
            if k.startswith(search_term):
                return True
        return compare.startswith(search_term)

    def search_include(self, entity):
        result = True
        if self.searchTerm:
            op = self.search_prefix_match
            names = IFriendlyNamed(entity, None)
            result = (op(entity.username, self.searchTerm)) \
                  or (names is not None
                      and (op(names.realname, self.searchTerm)
                           or op(names.alias, self.searchTerm)))
        return result


@component.adapter(IFriendsListContainer)
class FriendsListContainerCollection(_AbstractPseudoMembershipContainer,
                                     HomogeneousTypedContainerCollection,
                                     NameFilterableMixin):
    """
    ..note:: We are correctly not sending back an 'edit' link, but the UI still presents
            them as editable. We are also sending back the correct creator.
    """

    def __init__(self, container):  # pylint: disable=useless-super-delegation
        super(FriendsListContainerCollection, self).__init__(container)

    @property
    def accepts(self):
        # Try to determine if we should be allowed to create
        # this kind of thing or not
        # This can probably be generalized up
        user = None
        user_service = find_interface(self, IUserService)
        if user_service:
            user = user_service.user
        if user:
            factory = component.getUtility(IVocabularyFactory,
                                           "Creatable External Object Types")
            vocab = factory(user)
            try:
                contained_type = self._container.contained_type
                mimeType = nti_mimetype_from_object(contained_type)
                vocab.getTermByToken(mimeType)
            except LookupError:
                # We can prove that we cannot create it, it's not in our
                # vocabulary.
                return ()
        return (self._container.contained_type, DynamicFriendsList)

    @property
    def last_modified(self):
        return self._container.lastModified

    @property
    def memberships(self):
        return self._user.friendsLists.values()

    def selector(self, obj):
        """
        Only FL objects that our remote user can see.
        """
        # In alpha, some users have timestamps in FL collection.
        return IFriendsList.providedBy(obj) \
           and not IDynamicSharingTargetFriendsList.providedBy(obj) \
           and (self.remote_user in obj or self.remote_user == obj.creator) \
           and self.search_include(obj)


def _is_remote_same_as_authenticated(user, req=None):
    # This doesn't exactly belong at this layer. Come up with
    # a better way to do this switching.
    req = get_current_request() if req is None else req
    if     req is None or req.authenticated_userid is None \
        or req.authenticated_userid != user.username:
        return False
    return True


@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
class DynamicMembershipsContainerCollection(_AbstractPseudoMembershipContainer):

    name = u'DynamicMemberships'
    __name__ = name

    @property
    def memberships(self):
        return self._user.dynamic_memberships


@component.adapter(IUser)
@interface.implementer(IContainerCollection)
def _UserDynamicMembershipsCollectionFactory(user):
    return DynamicMembershipsContainerCollection(UserEnumerationWorkspace(user))


@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
class DynamicFriendsListContainerCollection(_AbstractPseudoMembershipContainer,
                                            NameFilterableMixin):

    # Do we need to accept posts here?
    name = u'Groups'
    __name__ = name

    @property
    def memberships(self):
        # Any that we own plus any we were added to.
        return set(self._user.friendsLists.values()) | set(self._user.dynamic_memberships)

    def selector(self, obj):
        """
        DFLs we own or are a member of, even if it it's not our
        collection.
        """
        return IDynamicSharingTargetFriendsList.providedBy(obj) \
           and not IDeactivatedDynamicSharingTargetFriendsList.providedBy(obj) \
           and (self.remote_user in obj or self.remote_user == obj.creator) \
           and self.search_include(obj)


@component.adapter(IUser)
@interface.implementer(IContainerCollection)
def _UserDynamicFriendsListCollectionFactory(user):
    return DynamicFriendsListContainerCollection(UserEnumerationWorkspace(user))


@component.adapter(ICollection)
@interface.implementer(IContentTypeAware)
class CollectionContentTypeAware(object):

    mimeType = nti_mimetype_with_class('collection')

    def __init__(self, collection):
        pass


def _find_named_link_views(parent, provided=None):
    """
    Introspect the component registry to find the things that
    want to live directly beneath the given object.
    These can either be an :class:`.INamedLinkPathAdapter`, if we intend
    to continue traversing, or a named view (implementing :class:`.INamedLinkView`
    if we want to stop
    traversing (and possibly access the subpath).

    Returns a set of names.
    """
    # pylint: disable=no-member,no-value-for-parameter
    request = get_current_request() or MissingRequest()

    # Pyramid's request_iface property is a dynamically generated
    # interface class that incorporates the name of the route.
    # Some tests provide a request object without that,
    # and even then, the route that got is here isn't (yet)
    # the traversable route we want. So look for the interface by route name.
    request_iface = component.queryUtility(interface.Interface,
                                           name='objects.generic.traversal',
                                           default=interface.Interface)
    # If it isn't loaded because the app hasn't been scanned, we have no
    # way to route, and no views either. So we get None, which is a fine
    # discriminator.
    if provided is None:
        provided = interface.providedBy(parent)

    def _test(unused_name, view):
        # Views created with the @view_config decorator tend to get wrapped
        # in a pyramid proxy, which would hide anything they declare to implement
        # (at least view functions). This is done at venusian scan time, which is after
        # the module is loaded. Fortunately, the underlying view seems to be preserved
        # through all the wrappings on the topmost layer of the onion as __original_view__,
        # so check it as well

        for v in view, getattr(view, '__original_view__', None):
            # View Functions will directly provide the interface;
            # view classes, OTOH, will tend to implement it (because using
            # the @implementer() decorator is easy)
            if INamedLinkView.providedBy(v) or INamedLinkView.implementedBy(v):
                return True
    adapters = component.getSiteManager().adapters
    # Order matters. traversing wins, so views first (?)
    names = [
        name for name, view in adapters.lookupAll((IViewClassifier, request_iface, provided), IView)
        if name and _test(name, view)
    ]
    names.extend(name for name, _ in component.getAdapters((parent, request),
                                                           INamedLinkPathAdapter))

    names.extend(name for name, _ in adapters.lookupAll((provided, interface.providedBy(request)),
                                                        INamedLinkPathAdapter))
    return set(names)


def _make_named_view_links(parent, pseudo_target=False, **kwargs):
    """
    Uses :func:`._find_named_link_views` to find named views
    appropriate for the parent and returns a fresh
    list of :class:`.ILink` objects representing them.
    """
    names = _find_named_link_views(parent, **kwargs)
    _links = []
    for name in names:
        target = name
        if pseudo_target:  # Hmm...
            target = Location()
            target.__name__ = name
            target.__parent__ = parent

        link = links.Link(target, rel=name)
        link.__name__ = link.target
        link.__parent__ = parent
        interface.alsoProvides(link, ILocation)
        _links.append(link)
    return _links


@interface.implementer(IWorkspace)
@component.adapter(IDataserverFolder)
class GlobalWorkspace(object):
    """
    Represents things that are global resolvers. Typically, these
    will not be writable.
    """

    __parent__ = None

    def __init__(self, parent=None, user=None):
        super(GlobalWorkspace, self).__init__()
        if parent:
            self.__parent__ = parent
        self._user = user

    @property
    def links(self):
        # Introspect the component registry to find the things that
        # want to live directly beneath the dataserver root globally.
        result = list(_make_named_view_links(self.__parent__))
        for provider in component.subscribers((self._user,), IGlobalWorkspaceLinkProvider):
            _links = provider.links(self)
            result.extend(_links or ())
        return result

    @property
    def name(self): return 'Global'
    __name__ = name

    @property
    def collections(self):
        result = [GlobalCollection(self.__parent__, 'Objects'),
                  GlobalCollection(self.__parent__, 'NTIIDs'),
                  GlobalCollection(self.__parent__, 'LibraryPath')]
        for global_collection in component.subscribers((self,),
                                                        IGlobalCollection):
            result.append(global_collection)
        return result


@interface.implementer(ICollection)
class GlobalCollection(object):
    """
    A non-writable collection in the global namespace.
    """

    def __init__(self, container, name):
        self.__parent__ = container
        self._name = name

    @property
    def name(self):
        return self._name
    __name__ = name

    @property
    def accepts(self):
        return ()


@component.adapter(User)
@interface.implementer(IUserWorkspace)
class UserEnumerationWorkspace(ContainerEnumerationWorkspace):
    """
    Extends the user's typed collections with one
    to capture page data.
    """

    _user = alias('_container')
    user = alias('_container')
    context = alias('_container')

    def __init__(self, user):
        super(UserEnumerationWorkspace, self).__init__(user)
        self.__name__ = user.username

    @property
    def pages_collection(self):
        # Why is this here?
        for p in self.collections:
            if p.__name__ == 'Pages':
                return p

    @property
    def links(self):
        result = []
        for provider in component.subscribers((self.user,), IUserWorkspaceLinkProvider):
            _links = provider.links(self)
            result.extend(_links or ())
        return result

    @property
    def collections(self):
        """
        The returned collections are sorted by name.
        """
        result = list(super(UserEnumerationWorkspace, self).collections)
        result.extend(
            c for c in component.subscribers((self,), ICollection) if c
        )
        return sorted(result, key=lambda x: x.name)


@interface.implementer(INTIIDEntry)
class NTIIDEntry(object):

    __external_class_name__ = 'PageInfo'

    mimeType = nti_mimetype_with_class(__external_class_name__)

    link_provided = IPageContainerResource
    recursive_stream_supports_feeds = True

    extra_links = ()
    createdTime = 0
    lastModified = 0
    contentUnit = None  # Legacy field

    def __init__(self, parent, ntiid):
        self.__parent__ = parent
        self.__name__ = ''
        self.ntiid = ntiid
        self.id = ntiid

    @property
    def links(self):
        result = _make_named_view_links(self.__parent__,
                                        pseudo_target=True,  # XXX: FIXME
                                        provided=self.link_provided)
        # If we support a feed, advertise it
        # FIXME: We should probably not be doing this. We're making
        # too many assumptions. And we're also duplicating some
        # stuff that's being done for IForum and ITopic (though those
        # are less important).
        if      self.recursive_stream_supports_feeds \
            and [x for x in result if x.rel == 'RecursiveStream']:
            remote_user = get_remote_user()
            token_creator = component.queryUtility(IUserViewTokenCreator,
                                                   name='feed.atom')
            if token_creator and remote_user:
                token = token_creator.getTokenForUserId(remote_user.username,
                                                        u'userdata:feed')
                if token:
                    target = Location()
                    target.__name__ = 'RecursiveStream'
                    target.__parent__ = self.__parent__
                    link = links.Link(target,
                                      rel='alternate',
                                      target_mime_type='application/atom+xml',
                                      title='RSS',
                                      elements=('feed.atom',),
                                      params={'token': token})
                    result.append(link)

        result.extend(self.extra_links)
        return result

    def __repr__(self):
        return "<%s.%s %s at %s>" % (type(self).__module__,
                                     type(self).__name__,
                                     self.ntiid, hex(id(self)))
_NTIIDEntry = NTIIDEntry  # BWC


class RootNTIIDEntry(NTIIDEntry):
    """
    Defines the collection entry for the root pseudo-NTIID, which
    is only meant for the use of the global stream.
    """
    link_provided = IRootPageContainerResource

    def __init__(self, parent, _):
        super(RootNTIIDEntry, self).__init__(parent, ntiids.ROOT)
_RootNTIIDEntry = RootNTIIDEntry  # BWC


@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
class UserPagesCollection(Location):
    """
    Turns a User into a ICollection of data for their pages (individual containers).
    """

    name = 'Pages'
    __name__ = name
    __parent__ = None

    def __init__(self, user_workspace):
        self.__parent__ = user_workspace
        self._workspace = user_workspace

    @property
    def _user(self):
        return self._workspace.user

    @property
    def links(self):
        # These are deprecated here, as the entire pages collection is
        # deprecated. They are moved to the user's workspace
        result = []
        for provider in component.subscribers((self._user,), IUserWorkspaceLinkProvider):
            _links = provider.links(self._workspace)
            result.extend(_links or ())
        return result

    def _make_parent(self, ntiid):
        ent_parent = Location()
        ent_parent.__name__ = "%s(%s)" % (self.name, ntiid)
        ent_parent.__parent__ = self.__parent__
        return ent_parent

    def make_info_for(self, ntiid):
        factory = RootNTIIDEntry if ntiid == ntiids.ROOT else NTIIDEntry
        return factory(self._make_parent(ntiid), ntiid)

    @property
    def container(self):
        result = LastModifiedCopyingUserList()
        result.append(self.make_info_for(ntiids.ROOT))
        for ntiid in self._user.iterntiids():
            result.append(self.make_info_for(ntiid))
        return result

    @property
    def accepts(self):
        # pylint
        itc_providedBy = getattr(IContainerTypesConstraint, 'providedBy')
        # We probably need to be more picky, too. Some things like
        # devices and friendslists are sneaking in here where they
        # don't belong...even though they can be posted here (?)
        # The fix is to add the right constraints
        util_callable = component.getUtility(IVocabularyFactory,
                                             "Creatable External Object Types")
        vocab = util_callable(self._user)
        for term in vocab:
            factory = term.value
            implementing = factory.getInterfaces()
            parent = implementing.get('__parent__')
            # pylint: disable=no-value-for-parameter
            if      parent and getattr(parent, 'constraint', None) \
                and itc_providedBy(parent.constraint):
                parent_types = parent.constraint.types
                # Hmm. Ok, right now we don't have constraints correct everywhere.
                # But when we do have constraints, they are not a general object
                # type and cant be posted here.
                if parent_types:
                    continue
            else:
                yield term.token
_UserPagesCollection = UserPagesCollection


@component.adapter(IUser)
@interface.implementer(IContainerCollection)
def _UserPagesCollectionFactory(user):
    """
    Used as a shortcut from the user to the pages class sections. Deprecated.
    """
    return _UserPagesCollection(UserEnumerationWorkspace(user))


@interface.implementer(IWorkspace)
@component.adapter(IUserService)
def _user_workspace(user_service):
    # The main user workspace lives at /users/ME/
    user_workspace = UserEnumerationWorkspace(user_service.user)
    return user_workspace


@component.adapter(IService)
@interface.implementer(IWorkspace)
def _global_workspace(user_service):
    global_ws = GlobalWorkspace(parent=user_service.__parent__,
                                user=user_service.user)
    assert global_ws.__parent__
    return global_ws


@component.adapter(IUnauthenticatedPrincipal)
@interface.implementer(IService, IContentTypeAware, IContained)
class Service(object):

    user = None
    mimeType = nti_mimetype_with_class('workspace')

    __parent__ = None
    __name__ = 'service'

    def __init__(self, principal):
        self.__parent__ = component.getUtility(IDataserver).root
        self.principal = principal

    @Lazy
    def _validator(self):
        return component.queryUtility(IWorkspaceValidator)

    def _is_valid_workspace(self, workspace):
        result = workspace != None
        if result and self._validator != None:
            # pylint: disable=no-member
            result = self._validator.validate(workspace)
        return result

    @property
    def workspaces(self):
        """
        We query for all subscribers that provide IWorkspace, given an IUserService. This
        facilitates adding new workspaces from different parts of the code. It also
        facilitates giving completely different workspaces to different sites (for example,
        transaction history only if the store is enabled for a site).

        The returned list is sorted by the name of the workspace.
        """
        return sorted((workspace
                       for workspace
                       in list(component.subscribers((self,), IWorkspace))
                       if self._is_valid_workspace(workspace)),
                      key=lambda w: w.name)

    @LazyOnClass
    def __acl__(self):
        # Everyone has access to a raw service
        acl = acl_from_aces(
            ace_allowing(EVERYONE_GROUP_NAME,
                         authorization.ACT_READ,
                         Service)
        )
        return acl


@component.adapter(IUser)
@interface.implementer(IUserService, IContentTypeAware)
class UserService(Service):

    user = alias('principal')

    @property
    def user_workspace(self):
        return _user_workspace(self)

    @Lazy
    def __acl__(self):
        # The user this service doc is for can read it
        acl = acl_from_aces(
            ace_allowing(self.principal,
                         authorization.ACT_READ,
                         Service)
        )
        return acl
