from survey_builder.domain.throttle import LoginThrottle


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_blocks_after_max_failures():
    throttle = LoginThrottle(max_failures=3, window_seconds=60, clock=Clock())
    for _ in range(2):
        throttle.record_failure("k")
    assert not throttle.is_blocked("k")
    throttle.record_failure("k")
    assert throttle.is_blocked("k")
    assert not throttle.is_blocked("other")


def test_failures_expire_after_the_window():
    clock = Clock()
    throttle = LoginThrottle(max_failures=2, window_seconds=60, clock=clock)
    throttle.record_failure("k")
    clock.now += 30
    throttle.record_failure("k")
    assert throttle.is_blocked("k")
    assert throttle.retry_after("k") == 30
    clock.now += 31
    assert not throttle.is_blocked("k")


def test_reset_clears_failures():
    throttle = LoginThrottle(max_failures=1, clock=Clock())
    throttle.record_failure("k")
    throttle.reset("k")
    assert not throttle.is_blocked("k")
    assert throttle.retry_after("k") == 0
