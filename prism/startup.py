"""Bounded model initialization that recovers after dependency startup failures."""
from threading import Lock
from time import monotonic, perf_counter
import os


def initialize_models():
    from prism.explain.attribution import _explainer, BACKGROUND, MODEL
    _explainer(MODEL.stat().st_mtime_ns, BACKGROUND.stat().st_mtime_ns)
    if os.environ.get('PRISM_DIAGNOSIS_STORE') == 'neo4j':
        from prism.explain.reference_input import diagnostic_view
        diagnostic_view()


class ModelWarmup:
    def __init__(self, initialize=None, clock=monotonic, cooldown=5):
        self.initialize = initialize or initialize_models
        self.clock = clock
        self.cooldown = cooldown
        self.last_attempt = float('-inf')
        self.lock = Lock()
        self.state = {'status': 'not_requested', 'elapsed_ms': 0}

    def attempt(self):
        if self.state['status'] == 'ready' or not self.lock.acquire(blocking=False):
            return self.state
        try:
            now = self.clock()
            if now - self.last_attempt < self.cooldown:
                return self.state
            self.last_attempt = now
            self.state.update(status='unavailable', elapsed_ms=0)
            started = perf_counter()
            try:
                self.initialize()
            except Exception:
                # Service exceptions may contain credentials; expose status only.
                self.state.update(status='unavailable', elapsed_ms=(perf_counter()-started)*1000)
            else:
                self.state.update(status='ready', elapsed_ms=(perf_counter()-started)*1000)
            return self.state
        finally:
            self.lock.release()
