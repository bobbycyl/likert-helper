from likert import LikertConfig
from likert.model import dump_config, parse_config


def test_scale_load_dump():
    config = LikertConfig.from_toml("./scales/CBF-PI-B.toml")
    dumped_config = dump_config(config)
    config_reload = parse_config(dumped_config)
    assert config == config_reload
