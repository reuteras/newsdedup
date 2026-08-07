import pytest

from newsdedup import read_configuration


def test_read_configuration_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit):
        read_configuration(str(tmp_path / "missing.toml"))


def test_read_configuration_empty_file_exits(tmp_path):
    config_file = tmp_path / "empty.toml"
    config_file.write_text("")

    with pytest.raises(SystemExit):
        read_configuration(str(config_file))


def test_read_configuration_invalid_toml_exits(tmp_path):
    config_file = tmp_path / "invalid.toml"
    config_file.write_text("this is not [ valid toml")

    with pytest.raises(SystemExit):
        read_configuration(str(config_file))


def test_read_configuration_returns_parsed_dict(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[miniflux]\nhostname = "https://example.com"\napi_token = "abc"\n')

    config = read_configuration(str(config_file))

    assert config["miniflux"]["hostname"] == "https://example.com"
    assert config["miniflux"]["api_token"] == "abc"
