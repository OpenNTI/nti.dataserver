# JAM: Added 2011-09-22, based on http://pypi.python.org/pypi/PyContext
# That page claims this to be under the Academic Free Licencse 3.0,
# but the distribution does not include a copyright or license
# notice
import threading

class Variable(threading.local):
    def __init__(self, value=None):
        self.value = None

    def get(self):
        return self.value

    def set(self, value):
        return _Manager(self, value)

class _Manager:
    def __init__(self, variable, value):
        self.variable = variable
        self.value = value

    def __enter__(self):
        self.oldvalue = self.variable.get()
        self.variable.value = self.value

    def __exit__(self, type, value, traceback):
        self.variable.value = self.oldvalue
