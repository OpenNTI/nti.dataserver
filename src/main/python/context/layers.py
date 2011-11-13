import types, threading, operator

implicit_layers = []
implicit_layers_types = set()

def register_implicit(layer):
	implicit_layers.append(layer)
	# rely on stable sort, bringing highest priority to front
	implicit_layers.sort(key=operator.attrgetter('priority'))
	implicit_layers_types.add(type(layer))

class ContextStack(threading.local):
	initialized = False

	def _ensure_init(self):
		if self.initialized:
			return
		self.initialized = True
		self.stack = []
		self._apparent = [] # reversed order of stack, without duplicates and disabled layers

	# private
	def _update_apparent(self):
		self._apparent = apparent = []
		found = set()
		for l in reversed(self.stack):
			if isinstance(l, Disabled):
				found.add(l.klass)
				continue
			klass = l.__class__
			if klass in found:
				continue
			apparent.append(l)
			found.add(klass)

	# public interface

	def push(self, layer):
		self._ensure_init()
		self.stack.append(layer)
		self._update_apparent()

	def pop(self):
		self._ensure_init()
		self.stack.pop()
		self._update_apparent()

	def apparent(self):
		self._ensure_init()
		return self._apparent

context_stack = ContextStack()

class _Original:
	pass

class Context:
	def __init__(self, target, name, finalfunc):
		self.target = target
		self.name = name
		self.func = finalfunc
		self.proceed = self.proceed_final
		self.chain = self.layer = None

	# chain: (func, layer, proceed, chain)

	def insert(self, func, layer, proceed):
		self.chain = (self.func, self.layer, self.proceed, self.chain)
		self.func = func
		self.layer = layer
		self.proceed = proceed

	def next(self):
		self.func, self.layer, self.proceed, self.chain = self.chain

	def proceed_final(self, *args, **kw):
		return self.func(self.target, *args, **kw)

	def proceed_before(self, *args, **kw):
		self.func(self.target, self, *args, **kw)
		self.next()
		return self.proceed(*args, **kw)

	def proceed_after(self, *args, **kw):
		func = self.func
		layer = self.layer
		self.next()
		result = self.proceed(*args, **kw)
		self.layer = layer
		self.result = result
		return func(self.target, self, *args, **kw)

	def proceed_instead(self, *args, **kw):
		self.proceed = self.nested_proceed
		return self.func(self.target, self, *args, **kw)

	def nested_proceed(self, *args, **kw):
		# Save continuation so that we can restore it after proceed returns
		chain = self.chain
		func = self.func
		layer = self.layer
		proceed = self.proceed
		self.next()
		result = self.proceed(*args, **kw)
		# Return from nested proceed, restoring all context attributes
		self.chain = chain
		self.func = func
		self.layer = layer
		self.proceed = proceed
		self.result = result
		return result

def before(f):
	f.__layer__ = before
	return f

def after(f):
	f.__layer__ = after
	return f

def instead(f):
	f.__layer__ = instead
	return f


def add_dispatch(context, layer, func):
	if func is None:
		return
	if func.__layer__ is before:
		proceed = context.proceed_before
	elif func.__layer__ is after:
		proceed = context.proceed_after
	elif func.__layer__ is instead:
		proceed = context.proceed_instead
	else:
		raise NotImplementedError, func.__layer__
	context.insert(func, layer, proceed)

def dispatch(self, name, args, kw):
	#print "Invoking", name, "on", self
	layers = self.__layers__[name]
	context = Context(self, name, layers[_Original])
	# build up evaluation chain: start with implicit layers,
	# starting with highest priority, per priority in the order
	# of registration
	for layer in implicit_layers:
		# first check whether the method is layered before
		# checking whether the layer is active as the second
		# test may be computationally more expensive
		func = layers.get(type(layer))
		if func and layer.active():
			add_dispatch(context, layer, func)
	# now explicitly-activated layers; start with innermost
	# non-disabled layer
	for layer in context_stack.apparent():
		add_dispatch(context, layer, layers.get(type(layer)))
	return context.proceed(*args, **kw)


class _MetaLayer(type):
	ignored = set(['__module__'])

	def __new__(cls, name, bases, dict):
		if len(bases) < 2:
			return type.__new__(cls, name, bases, dict)
		if len(bases) != 2:
			raise TypeError, "too many base classes for layer usage"
		layer = bases[0]
		base = bases[1]
		try:
			layers = base.__layers__
		except AttributeError:
			layers = base.__layers__ = {}
		for k, v in dict.items():
			if k in cls.ignored:
				continue
			if not isinstance(v, types.FunctionType):
				raise TypeError, ("Unsupported definition %s=%sin layer" %
								  (k, repr(v)))
			if not layers.has_key(k):
				# hack to make sure the name gets bound properly
				def make_dispatch(name=k):
					def _dispatch(self, *args, **kw):
						return dispatch(self, name, args, kw)
					return _dispatch
				layers[k] = { _Original:getattr(base, k) }
				setattr( base, k, make_dispatch() )
			layers[k][layer] = v
		return None

class Layer:
	__metaclass__ = _MetaLayer
	priority = 0

	def __enter__(self):
		context_stack.push(self)

	def __exit__(self, type, value, traceback):
		context_stack.pop()

	def active(self):
		return False

class Disabled:
	def __init__(self, klass):
		self.klass = klass

	def __enter__(self):
		context_stack.push(self)

	def __exit__(self, type, value, traceback):
		context_stack.pop()
