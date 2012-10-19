from __future__ import print_function, unicode_literals

from zope import component
from zope.generations.utility import findObjectsProviding

from nti.dataserver.users import friends_lists
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces

def find_user_dfls(user):
    result = {}
    for obj in findObjectsProviding( user, nti_interfaces.IFriendsList):
        if isinstance(obj, friends_lists.DynamicFriendsList):
            result[obj.username] = obj
    return result

def remove_rim_catalogs(rim):
    if rim is not None:
        for key in list(rim.keys()):
            rim.pop(key, None)
        return True
    return False
            
def remove_entity_catalogs(entity):
    rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
    return remove_rim_catalogs(rim)

def get_sharedWith(obj):
    # from IPython.core.debugger import Tracer;  Tracer()() ## DEBUG ##
    adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
    result = getattr(adapted, 'get_sharedWith', None) if adapted is not None else None
    result = result() if result else ()
    return result
         
def get_catalog_and_docids(entity):
    rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
    if rim is not None:
        for catalog in rim.values():
            catfield = list(catalog.values())[0] if catalog else None
            if hasattr(catfield, "_indexed"):
                yield catalog, list(catfield._indexed())

        