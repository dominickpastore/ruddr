import errno

import pytest

import ruddr.configuration


class BrokenFile:
    def __iter__(self):
        raise OSError(errno.ETIMEDOUT, "timeout")


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


@pytest.fixture
def config_factory(configfile_factory):
    def factory(contents):
        configfile = configfile_factory(contents)
        config = ruddr.configuration.read_file_from_path(configfile.filename)
        config.finalize(lambda mod, typ: True, lambda mod, typ: True)
        return config
    return factory


def test_nonexistent_file(tmp_path):
    """Test opening a nonexistent path raises ConfigError"""
    with pytest.raises(ruddr.ConfigError):
        ruddr.configuration.read_file_from_path(
            tmp_path / 'nonexistent_config.ini'
        )


def test_read_file_read_error():
    """Test read error for read_file"""
    f = BrokenFile()

    with pytest.raises(ruddr.ConfigError):
        ruddr.configuration.read_file(f)


def test_read_file_from_path_read_error(mocker, tmp_path):
    """Test read error for read_file_from_path"""
    mocker.patch('__main__.open', return_value=BrokenFile())

    with pytest.raises(ruddr.ConfigError):
        ruddr.configuration.read_file_from_path(tmp_path / 'config.ini')


def test_config_keys(config_factory):
    """Test that a configuration contains all the keys it is supposed to"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data

        [notifier.test_notifier]
        type = iface

        [updater.test_updater]
        type = standard
        notifier = test_notifier
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
    }
    assert config.notifiers == {"test_notifier": {
        "type": "iface",
        "datadir": "/var/lib/ruddr_data",
    }}
    assert config.updaters == {"test_updater": {
        "type": "standard",
        "notifier4": "test_notifier",
        "notifier6": "test_notifier",
        "datadir": "/var/lib/ruddr_data",
    }}


def test_config_keys_custom_updater_and_notifier(config_factory):
    """Test that a configuration contains all the keys it is supposed to
    when using a custom updater and notifier (that is, the "module" key is
    present)"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data

        [notifier.test_notifier]
        type = MyNotifier
        module = notifier_module

        [updater.test_updater]
        type = MyUpdater
        module = updater_module
        notifier = test_notifier
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
    }
    assert config.notifiers == {"test_notifier": {
        "type": "MyNotifier",
        "module": "notifier_module",
        "datadir": "/var/lib/ruddr_data",
    }}
    assert config.updaters == {"test_updater": {
        "type": "MyUpdater",
        "module": "updater_module",
        "notifier4": "test_notifier",
        "notifier6": "test_notifier",
        "datadir": "/var/lib/ruddr_data",
    }}


def test_no_global_section(config_factory):
    """Test that the configuration can be parsed when there's no ``[ruddr]``
    section and the datadir key has the correct default value"""
    config = config_factory(
        """
        [notifier.test_notifier]
        type = iface

        [updater.test_updater]
        type = standard
        notifier = test_notifier
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr",
    }
    assert config.notifiers['test_notifier']['datadir'] == "/var/lib/ruddr"
    assert config.updaters['test_updater']['datadir'] == "/var/lib/ruddr"


def test_no_updater(config_factory):
    """Test config without an updater triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface
            """
        )


def test_no_notifier(config_factory):
    """Test config without a notifier triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_extra_section_1(config_factory):
    """Test config with extra section [foo] triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [foo]

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_extra_section_2(config_factory):
    """Test config with extra section [foo.] triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [foo.]

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_extra_section_3(config_factory):
    """Test config with extra section [foo.bar] triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [foo.bar]

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_notifier_no_name_1(config_factory):
    """Test config with [notifier] triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier]
            type = iface

            [updater.test_updater]
            type = standard
            notifier =
            """
        )


def test_notifier_no_name_2(config_factory):
    """Test config with [notifier.] triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.]
            type = iface

            [updater.test_updater]
            type = standard
            notifier =
            """
        )


def test_updater_no_name_1(config_factory):
    """Test config with [updater] triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_updater_no_name_2(config_factory):
    """Test config with [updater.] triggers error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [updater.]
            type = standard
            notifier = test_notifier
            """
        )


def test_notifier_updater_same_name(config_factory):
    """Test notifier and updater with same name is not error"""
    config = config_factory(
        """
        [notifier.foo]
        type = iface

        [updater.foo]
        type = standard
        notifier = foo
        """
    )

    assert config.notifiers == {"foo": {
        "type": "iface",
        "datadir": "/var/lib/ruddr",
    }}
    assert config.updaters == {"foo": {
        "type": "standard",
        "notifier4": "foo",
        "notifier6": "foo",
        "datadir": "/var/lib/ruddr",
    }}


def test_two_updaters_same_name(config_factory):
    """Test two updaters with matching names is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard
            notifier = test_notifier

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_two_notifiers_same_name(config_factory):
    """Test two notifiers with matching names is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_notifier_without_type(config_factory):
    """Test notifier without a type is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_updater_without_type(config_factory):
    """Test updater without a type is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            notifier = test_notifier
            """
        )


def test_notifier_invalid_type_1(configfile_factory):
    """Test notifier type rejected is error"""
    configfile = configfile_factory(
        """
        [notifier.test_notifier]
        type = iface

        [updater.test_updater]
        type = standard
        notifier = test_notifier
        """
    )
    config = ruddr.configuration.read_file_from_path(configfile.filename)

    with pytest.raises(ruddr.ConfigError):
        config.finalize(
            lambda mod, typ: False,
            lambda mod, typ: True,
        )


def test_notifier_invalid_type_2(configfile_factory):
    """Test notifier module/type rejected is error"""
    configfile = configfile_factory(
        """
        [notifier.test_notifier]
        type = MyNotifier
        module = notifier_module

        [updater.test_updater]
        type = standard
        notifier = test_notifier
        """
    )
    config = ruddr.configuration.read_file_from_path(configfile.filename)

    with pytest.raises(ruddr.ConfigError):
        config.finalize(
            lambda mod, typ: False,
            lambda mod, typ: True,
        )


def test_updater_invalid_type_1(configfile_factory):
    """Test updater type rejected is error"""
    configfile = configfile_factory(
        """
        [notifier.test_notifier]
        type = iface

        [updater.test_updater]
        type = standard
        notifier = test_notifier
        """
    )
    config = ruddr.configuration.read_file_from_path(configfile.filename)

    with pytest.raises(ruddr.ConfigError):
        config.finalize(
            lambda mod, typ: True,
            lambda mod, typ: False,
        )


def test_updater_invalid_type_2(configfile_factory):
    """Test updater module/type rejected is error"""
    configfile = configfile_factory(
        """
        [notifier.test_notifier]
        type = iface

        [updater.test_updater]
        type = MyUpdater
        module = updater_module
        notifier = test_notifier
        """
    )
    config = ruddr.configuration.read_file_from_path(configfile.filename)

    with pytest.raises(ruddr.ConfigError):
        config.finalize(
            lambda mod, typ: True,
            lambda mod, typ: False,
        )


def test_duplicate_keys_global_section(config_factory):
    """Test duplicate keys in the [ruddr] section is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [ruddr]
            datadir = /var/lib/ruddr
            datadir = /var/lib/ruddr

            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_duplicate_keys_notifier(config_factory):
    """Test duplicate keys in a notifier is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [ruddr]
            datadir = /var/lib/ruddr

            [notifier.test_notifier]
            type = iface
            type = iface

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            """
        )


def test_duplicate_keys_updater(config_factory):
    """Test duplicate keys in an updater is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [ruddr]
            datadir = /var/lib/ruddr

            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            notifier = test_notifier
            """
        )


def test_redundant_notifier_keys(config_factory):
    """Test notifier key when notifier4 and notifier6 both present is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [ruddr]
            datadir = /var/lib/ruddr

            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard
            notifier = test_notifier
            notifier4 = test_notifier
            notifier6 = test_notifier
            """
        )


def test_redundant_notifier_keys_global(config_factory):
    """Test notifier key when notifier4 and notifier6 both present is error
    in [ruddr]"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [ruddr]
            datadir = /var/lib/ruddr
            notifier = test_notifier
            notifier4 = test_notifier
            notifier6 = test_notifier

            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard
            """
        )


def test_global_notifier(config_factory):
    """Test config with global notifier"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier = test_notifier

        [notifier.test_notifier]
        type = iface

        [updater.test_updater]
        type = standard
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier": "test_notifier",
    }
    assert config.notifiers == {"test_notifier": {
        "type": "iface",
        "datadir": "/var/lib/ruddr_data",
    }}
    assert config.updaters == {"test_updater": {
        "type": "standard",
        "notifier4": "test_notifier",
        "notifier6": "test_notifier",
        "datadir": "/var/lib/ruddr_data",
    }}


def test_global_notifier46(config_factory):
    """Test config with global notifier4 and notifier6"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier4 = test_notifier
        notifier6 = test_notifier2

        [notifier.test_notifier]
        type = iface

        [notifier.test_notifier2]
        type = iface

        [updater.test_updater]
        type = standard
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier4": "test_notifier",
        "notifier6": "test_notifier2",
    }
    assert config.notifiers == {
        "test_notifier": {
            "type": "iface",
            "datadir": "/var/lib/ruddr_data",
        },
        "test_notifier2": {
            "type": "iface",
            "datadir": "/var/lib/ruddr_data",
        },
    }
    assert config.updaters == {"test_updater": {
        "type": "standard",
        "notifier4": "test_notifier",
        "notifier6": "test_notifier2",
        "datadir": "/var/lib/ruddr_data",
    }}


def test_global_and_updater_notifier_1(config_factory):
    """Test combo 1 of notifier, notifier4, notifier6, both global and local"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier4 = test_notifier
        notifier6 = test_notifier2

        [notifier.test_notifier]
        type = iface

        [notifier.test_notifier2]
        type = iface

        [notifier.test_notifier3]
        type = iface

        [updater.test_updater]
        type = standard

        [updater.test_updater2]
        type = standard
        notifier = test_notifier3
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier4": "test_notifier",
        "notifier6": "test_notifier2",
    }
    assert config.updaters == {
        "test_updater": {
            "type": "standard",
            "notifier4": "test_notifier",
            "notifier6": "test_notifier2",
            "datadir": "/var/lib/ruddr_data",
        },
        "test_updater2": {
            "type": "standard",
            "notifier4": "test_notifier3",
            "notifier6": "test_notifier3",
            "datadir": "/var/lib/ruddr_data",
        },
    }


def test_global_and_updater_notifier_2(config_factory):
    """Test combo 2 of notifier, notifier4, notifier6, both global and local"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier6 = test_notifier2

        [notifier.test_notifier]
        type = iface

        [notifier.test_notifier2]
        type = iface

        [notifier.test_notifier3]
        type = iface

        [updater.test_updater]
        type = standard

        [updater.test_updater2]
        type = standard
        notifier = test_notifier3
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier6": "test_notifier2",
    }
    assert config.updaters == {
        "test_updater": {
            "type": "standard",
            "notifier6": "test_notifier2",
            "datadir": "/var/lib/ruddr_data",
        },
        "test_updater2": {
            "type": "standard",
            "notifier4": "test_notifier3",
            "notifier6": "test_notifier3",
            "datadir": "/var/lib/ruddr_data",
        },
    }


def test_global_and_updater_notifier_3(config_factory):
    """Test combo 3 of notifier, notifier4, notifier6, both global and local"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier6 = test_notifier2

        [notifier.test_notifier]
        type = iface

        [notifier.test_notifier2]
        type = iface

        [notifier.test_notifier3]
        type = iface

        [updater.test_updater]
        type = standard
        notifier6 = test_notifier

        [updater.test_updater2]
        type = standard
        notifier4 = test_notifier3
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier6": "test_notifier2",
    }
    assert config.updaters == {
        "test_updater": {
            "type": "standard",
            "notifier6": "test_notifier",
            "datadir": "/var/lib/ruddr_data",
        },
        "test_updater2": {
            "type": "standard",
            "notifier4": "test_notifier3",
            "datadir": "/var/lib/ruddr_data",
        },
    }


def test_global_and_updater_notifier_4(config_factory):
    """Test combo 4 of notifier, notifier4, notifier6, both global and local"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier = test_notifier2

        [notifier.test_notifier]
        type = iface

        [notifier.test_notifier2]
        type = iface

        [notifier.test_notifier3]
        type = iface

        [updater.test_updater]
        type = standard
        notifier6 = test_notifier

        [updater.test_updater2]
        type = standard
        notifier4 = test_notifier3
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier": "test_notifier2",
    }
    assert config.updaters == {
        "test_updater": {
            "type": "standard",
            "notifier6": "test_notifier",
            "datadir": "/var/lib/ruddr_data",
        },
        "test_updater2": {
            "type": "standard",
            "notifier4": "test_notifier3",
            "datadir": "/var/lib/ruddr_data",
        },
    }


def test_global_and_updater_notifier_5(config_factory):
    """Test combo 5 of notifier, notifier4, notifier6, both global and local"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier = test_notifier

        [notifier.test_notifier]
        type = iface

        [notifier.test_notifier2]
        type = iface

        [notifier.test_notifier3]
        type = iface

        [notifier.test_notifier4]
        type = iface

        [updater.test_updater]
        type = standard
        notifier = test_notifier2

        [updater.test_updater2]
        type = standard
        notifier4 = test_notifier3
        notifier6 = test_notifier4
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier": "test_notifier",
    }
    assert config.updaters == {
        "test_updater": {
            "type": "standard",
            "notifier4": "test_notifier2",
            "notifier6": "test_notifier2",
            "datadir": "/var/lib/ruddr_data",
        },
        "test_updater2": {
            "type": "standard",
            "notifier4": "test_notifier3",
            "notifier6": "test_notifier4",
            "datadir": "/var/lib/ruddr_data",
        },
    }


def test_global_and_updater_notifier_6(config_factory):
    """Test combo 6 of notifier, notifier4, notifier6, both global and local"""
    config = config_factory(
        """[ruddr]
        datadir = /var/lib/ruddr_data
        notifier4 = test_notifier
        notifier6 = test_notifier2

        [notifier.test_notifier]
        type = iface

        [notifier.test_notifier2]
        type = iface

        [notifier.test_notifier3]
        type = iface

        [notifier.test_notifier4]
        type = iface

        [updater.test_updater]
        type = standard

        [updater.test_updater2]
        type = standard
        notifier4 = test_notifier3
        notifier6 = test_notifier4
        """
    )

    assert config.main == {
        "datadir": "/var/lib/ruddr_data",
        "notifier4": "test_notifier",
        "notifier6": "test_notifier2",
    }
    assert config.updaters == {
        "test_updater": {
            "type": "standard",
            "notifier4": "test_notifier",
            "notifier6": "test_notifier2",
            "datadir": "/var/lib/ruddr_data",
        },
        "test_updater2": {
            "type": "standard",
            "notifier4": "test_notifier3",
            "notifier6": "test_notifier4",
            "datadir": "/var/lib/ruddr_data",
        },
    }


def test_missing_notifier(config_factory):
    """Test missing notifier, notifier4, and notifier6 is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """
            [ruddr]
            datadir = /var/lib/ruddr

            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard
            """
        )


def test_missing_notifier_on_one_updater(config_factory):
    """Test missing notifier on one updater when other has it is error"""
    with pytest.raises(ruddr.ConfigError):
        config_factory(
            """[ruddr]
            datadir = /var/lib/ruddr_data

            [notifier.test_notifier]
            type = iface

            [updater.test_updater]
            type = standard

            [updater.test_updater2]
            type = standard
            notifier4 = test_notifier
            """
        )
