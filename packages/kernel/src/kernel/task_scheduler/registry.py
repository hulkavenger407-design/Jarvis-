# A minimal internal registry.
# The original implementation kept all internal lists/dictionaries directly
# on the TaskScheduler instance itself (e.g. self._waiting, self._completed).
# To strictly avoid inventing new architecture or redesigning, this file is left
# as a minimal stub, maintaining the architecture exactly as it was.
