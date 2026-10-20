from dropwheel.utils import clamp_to_screen, reveal_in_explorer, unique_path


def test_unique_path_free(tmp_path):
    p = tmp_path / "a.png"
    assert unique_path(p) == p


def test_unique_path_collision(tmp_path):
    (tmp_path / "a.png").touch()
    (tmp_path / "a (1).png").touch()
    assert unique_path(tmp_path / "a.png").name == "a (2).png"


def test_clamp_to_screen_inside():
    # Normal inside screen (1920x1080)
    screen_rect = (0, 0, 1920, 1080)
    x, y = clamp_to_screen(500, 300, 380, 380, screen_rect)
    assert (x, y) == (500, 300)


def test_clamp_to_screen_left_top_overflow():
    screen_rect = (0, 0, 1920, 1080)
    # Cursor at (10, 10) gives ideal (-180, -180)
    x, y = clamp_to_screen(-180, -180, 380, 380, screen_rect)
    assert x == 0
    assert y == 0


def test_clamp_to_screen_right_bottom_overflow():
    screen_rect = (0, 0, 1920, 1080)
    # Beyond right and bottom edges
    x, y = clamp_to_screen(1800, 950, 380, 380, screen_rect)
    assert x == 1920 - 380  # 1540
    assert y == 1080 - 380  # 700


def test_clamp_to_screen_multi_monitor():
    # Left secondary monitor: x from -1920 to 0
    screen_rect = (-1920, 0, 1920, 1080)
    x, y = clamp_to_screen(-2000, 100, 380, 380, screen_rect)
    assert x == -1920
    assert y == 100

    x, y = clamp_to_screen(-100, 100, 380, 380, screen_rect)
    assert x == -380
    assert y == 100


def test_reveal_in_explorer_file_exists(monkeypatch, tmp_path):
    target = tmp_path / "result.txt"
    target.touch()

    called_cmds = []

    def mock_popen(cmd):
        called_cmds.append(cmd)

    monkeypatch.setattr("subprocess.Popen", mock_popen)
    monkeypatch.setattr("sys.platform", "win32")

    reveal_in_explorer(target)
    assert len(called_cmds) == 1
    assert called_cmds[0] == ["explorer", f"/select,{target.resolve()}"]


def test_reveal_in_explorer_parent_fallback(monkeypatch, tmp_path):
    non_existent = tmp_path / "deleted.txt"
    called_cmds = []

    def mock_popen(cmd):
        called_cmds.append(cmd)

    monkeypatch.setattr("subprocess.Popen", mock_popen)
    monkeypatch.setattr("sys.platform", "win32")

    reveal_in_explorer(non_existent)
    assert len(called_cmds) == 1
    assert called_cmds[0] == ["explorer", str(tmp_path.resolve())]

