from dropwheel.utils import unique_path


def test_unique_path_free(tmp_path):
    p = tmp_path / "a.png"
    assert unique_path(p) == p


def test_unique_path_collision(tmp_path):
    (tmp_path / "a.png").touch()
    (tmp_path / "a (1).png").touch()
    assert unique_path(tmp_path / "a.png").name == "a (2).png"
