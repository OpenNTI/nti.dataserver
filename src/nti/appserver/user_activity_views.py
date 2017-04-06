#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to user activity.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from pyramid.view import view_config

from nti.app.renderers.interfaces import IUserActivityExternalCollection

from nti.appserver.interfaces import IUserActivityStorage
from nti.appserver.interfaces import IUserActivityProvider

from nti.appserver.ugd_query_views import _toplevel_filter
from nti.appserver.ugd_query_views import _RecursiveUGDView as RecursiveUGDQueryView

from nti.containers.datastructures import IntidContainedStorage

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.ntiids import ntiids


# The link relationship type for a link to retrieve activity
# for a particular user.
# Also serves as a view name for that same purpose
# (:class:`UserActivityGetView`).
# This permits a URL like .../users/$USER/Activity
REL_USER_ACTIVITY = "Activity"


def _always_toplevel_filter(x):
    try:
        # IInspectableWeakThreadable required for this
        return not x.isOrWasChildInThread()
    except AttributeError:
        return _toplevel_filter(x)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_READ,
             context=IUser,
             name=REL_USER_ACTIVITY,
             request_method='GET')
class UserActivityGetView(RecursiveUGDQueryView):
    """
    The /Activity view for a particular user.

    This view returns a collection of activity for the specified user, across
    the entire site (similar to a RecursiveUserGeneratedData query using the Root
    ntiid.) One difference is that this URL never returns a 404 response, even when initially
    empty. Another is that the ``MeOnly`` filter is implicit, and refers not to the calling
    user but the user who's data is being accessed.

    The contents fully support the same sorting and paging parameters as
    the UGD views with a few exceptions:

    * The definition for a ``TopLevel`` object is changed to mean one that has never been a
      child in a thread (instead of just one who is not currently a child in a thread) (where possible).

    * Assessed questions are always excluded (unless you specifically include them; their
      ACL only allows their owner/creator to see them anyway).

    """
    # We rely very much on the internal implementation
    # of the super class, specifically that it will call
    # getObjectsForId, which is where we hook in, and that it
    # will use our _NotDeleted filter. If we let it go directly
    # to the catalog, it skips us and gets the wrong answers
    # (Too much or too little data).
    _can_special_case_root = False
    result_iface = IUserActivityExternalCollection

    FILTER_NAMES = RecursiveUGDQueryView.FILTER_NAMES.copy()
    FILTER_NAMES['TopLevel'] = _always_toplevel_filter
    FILTER_NAMES['_NotDeleted'] = lambda x: not IDeletedObjectPlaceholder.providedBy(x)

    get_shared = None  # Because we are always MeOnly

    def __init__(self, request):
        self.request = request
        super(UserActivityGetView, self).__init__(request,
                                                  the_user=request.context,
                                                  the_ntiid=ntiids.ROOT)

    def _get_filter_names(self):
        filters = set(super(UserActivityGetView, self)._get_filter_names())
        filters.add('MeOnly')
        filters.add('_NotDeleted')
        return filters

    def _get_exclude_types(self):
        excludes = set(super(UserActivityGetView, self)._get_exclude_types())
        excludes.add('application/vnd.nextthought.assessment.pollsubmission')
        excludes.add('application/vnd.nextthought.assessment.surveysubmission')
        excludes.add('application/vnd.nextthought.assessment.assessedquestion')
        excludes.add('application/vnd.nextthought.assessment.assessedquestionset')
        return excludes

    def _check_for_not_found(self, items, exc_info):
        """
        Override to never throw.
        """
        return

    def getObjectsForId(self, user, ntiid):
        # Collect the UGD recursively
        result = super(UserActivityGetView, self).getObjectsForId(user, ntiid)
        result = [x for x in result if x is not ()]
        # At this point, we know we have a list of dicts-like objects
        # (btrees and other containers)

        # Add the blog (possibly missing)
        # NOTE: This is no longer necessary as the blog is being treated as a container
        # found in user.containers with an NTIID
        # result.append( frm_interfaces.IPersonalBlog( self.user, () ) )

        # However, we do need to add the activity, if it exists
        # FIXME: Note that right now, we are only querying the global store
        # (all the recursion and iteration is handled in the super). This is probably
        # easy to fix, but we are also only using the global store (see
        # forum_views)
        activity_provider = component.queryMultiAdapter((user, self.request),
                                                        IUserActivityProvider)
        if activity_provider:
            result.append(activity_provider.getActivity())
        return result


# TODO: This is almost certainly the wrong place for this
@component.adapter(IUser)
@interface.implementer(IUserActivityStorage)
class DefaultUserActivityStorage(IntidContainedStorage):
    pass
DefaultUserActivityStorageFactory = an_factory(DefaultUserActivityStorage)


@interface.implementer(IUserActivityProvider)
class DefaultUserActivityProvider(object):

    def __init__(self, user, request=None):
        self.user = user

    def getActivity(self):
        activity = IUserActivityStorage(self.user, None)
        if activity is not None:
            return activity.getContainer('', ())
