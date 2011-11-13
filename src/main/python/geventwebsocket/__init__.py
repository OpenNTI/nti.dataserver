
version_info = (0, 2, 3, 'nti')
__version__ =  ".".join(map(str, version_info))

try:
    from geventwebsocket.websocket import *
except ImportError:
    import traceback
    traceback.print_exc()
