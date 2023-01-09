import pytest

import doubles

@pytest.fixture
def notifier_factory():
    """Fixture creating a factory for fake :class:`~ruddr.Notifier`"""
    class NotifierFactory:
        def __init__(self):
            self._count = 0

        def __call__(self, **kwargs):
            self._count += 1
            config = kwargs
            return doubles.FakeNotifier(f'fake_notifier_{self._count}', config)
    return NotifierFactory()


@pytest.fixture
def updater_factory():
    """Fixture creating a factory for mock :class:`~ruddr.Updater`"""
    class UpdaterFactory:
        def __init__(self):
            self._count = 0

        def __call__(self, **kwargs):
            self._count += 1
            config = kwargs
            return doubles.MockBaseUpdater(f'mock_updater_{self._count}')
    return UpdaterFactory()


@pytest.fixture
def mock_updater(updater_factory):
    """Fixture creating a mock :class:`~ruddr.Updater` that keeps a list of
    IP addresses it receives"""
    return updater_factory()


