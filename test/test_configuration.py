import pytest

import ruddr


@pytest.fixture
def configfile_factory(tmp_path):
    """Fixture creating a factory for temporary config files"""
    class ConfigFileFactory:
        def __init__(self, contents):
            with open(self.filename, 'w') as f:
                for line in contents.splitlines():
                    print(line.strip(), file=f)

        @property
        def filename(self):
            return tmp_path / 'config.ini'
    return ConfigFileFactory


def test_nonexistent_file(tmp_path):
    """Test opening a nonexistent path raises ConfigError"""
    with pytest.raises(ruddr.ConfigError):
        ruddr.ConfigReader(tmp_path / 'nonexistent_config.ini')


def test_basic_config(configfile_factory):
    """Test a basic configuration"""
    configfile = configfile_factory(
        """[ruddr]
        addrfile = /var/lib/ruddr_addrfile
        
        [notifier.test_notifier]
        type = timed
        
        [updater.test_updater]
        type = standard
        notifier = test_notifier
        """
    )

    ruddr.ConfigReader(configfile.filename)
    # TODO check ruddr, notifier., and updater. sections


def test_default_addrfile(configfile_factory):
    """Test that addrfile key is set to default when not present"""
    # TODO


# TODO Test config without an updater triggers error


# TODO Test config without notifier triggers error


# TODO Test creating other sections (foo, foo., foo.bar) triggers error


# TODO Test notifier. without name triggers error


# TODO Test updater. without name triggers error


# TODO Test notifier.foo and updater.foo is not error (notifier and updater can
#   have same name)


# TODO Test two notifiers or two updaters with same name is error


# TODO Notifier without type is error


# TODO Updater without type is error


# TODO Double keys in any section is error


# TODO notifier key in [ruddr] when both notifier4 and notifier6 are provided is error


# TODO notifier key on updater when both notifier4 and notifier6 are provided is error


# TODO Test all combos of notifier4, notifier6, and notifier local and global