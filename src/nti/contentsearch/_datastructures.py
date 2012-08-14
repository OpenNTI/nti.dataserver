from __future__ import print_function, unicode_literals

from brownie.caching import LFUCache

class LFUMap(LFUCache):

    def __init__(self, maxsize, on_removal_callback=None):
        super(LFUMap, self).__init__(maxsize=maxsize)
        self.on_removal_callback = on_removal_callback

    def __delitem__(self, key):
        if self.on_removal_callback:
            value = dict.__getitem__(self, key)
        super(LFUMap, self).__delitem__(key)
        if self.on_removal_callback:
            self.on_removal_callback(key, value)

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def get(self, key, default=None):
        return super(CaseInsensitiveDict, self).get(key.lower(), default)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())
    
    def __delitem__(self, key):
        return super(CaseInsensitiveDict, self).__delitem__(key.lower())
