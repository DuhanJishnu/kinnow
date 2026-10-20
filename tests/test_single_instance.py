import sys
import pytest

from dropwheel.utils import acquire_single_instance_mutex, release_single_instance_mutex


def test_single_instance_mutex():
    if sys.platform != "win32":
        pytest.skip("Windows only test")

    test_mutex_name = "KinnowUnitTestMutex_UniqueTest_123"

    # First instance acquires mutex
    h1, is_running1 = acquire_single_instance_mutex(test_mutex_name)
    assert h1 is not None
    assert is_running1 is False

    # Second instance attempts to acquire same mutex
    h2, is_running2 = acquire_single_instance_mutex(test_mutex_name)
    assert is_running2 is True

    # Cleanup
    release_single_instance_mutex(h2)
    release_single_instance_mutex(h1)

    # After releasing, acquiring should succeed again
    h3, is_running3 = acquire_single_instance_mutex(test_mutex_name)
    assert is_running3 is False
    release_single_instance_mutex(h3)
