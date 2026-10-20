from pathlib import Path

import pytest

from dropwheel.converters import registry


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY", {})


def test_register_and_targets():
    @registry.register(["aaa"], "bbb")
    def f(src, dst):
        dst.write_text("ok")

    assert registry.targets_for(Path("x.AAA")) == ["bbb"]
    assert registry.targets_for(Path("x.zzz")) == []


def test_same_format_not_registered():
    registry.register(["png"], "png")(lambda s, d: None)
    assert registry.targets_for(Path("x.png")) == []


def test_common_targets():
    registry.register(["a"], "x")(lambda s, d: None)
    registry.register(["a"], "y")(lambda s, d: None)
    registry.register(["b"], "y")(lambda s, d: None)
    assert registry.common_targets([Path("1.a"), Path("2.b")]) == ["y"]


def test_convert_writes_next_to_source(tmp_path):
    registry.register(["aaa"], "bbb")(lambda s, d: d.write_text("hi"))
    src = tmp_path / "f.aaa"
    src.touch()
    out = registry.convert(src, "bbb")
    assert out == tmp_path / "f.bbb" and out.read_text() == "hi"


def test_unsupported(tmp_path):
    with pytest.raises(registry.UnsupportedConversion):
        registry.convert(tmp_path / "f.aaa", "bbb")
