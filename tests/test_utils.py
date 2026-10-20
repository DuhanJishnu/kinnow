from dropwheel.utils import (
    clamp_to_screen,
    create_shortcut,
    get_desktop_shortcut_path,
    get_start_menu_shortcut_path,
    get_startup_shortcut_path,
    is_startup_enabled,
    reveal_in_explorer,
    toggle_startup,
    unique_path,
)


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
    target = tmp_path / "folder with spaces" / "result.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()

    called_args = []

    def mock_shell_execute(hwnd, op, file, param, dir, show):
        called_args.append((op, file, param))
        return 42

    monkeypatch.setattr("ctypes.windll.shell32.ShellExecuteW", mock_shell_execute)
    monkeypatch.setattr("sys.platform", "win32")

    reveal_in_explorer(target)
    assert len(called_args) == 1
    op, file, param = called_args[0]
    assert op == "open"
    assert file == "explorer.exe"
    # Ensure /select, is NOT inside the quotes
    assert param == f'/select,"{target.resolve()}"'


def test_reveal_in_explorer_parent_fallback(monkeypatch, tmp_path):
    non_existent = tmp_path / "deleted.txt"
    called_args = []

    def mock_shell_execute(hwnd, op, file, param, dir, show):
        called_args.append((op, file, param))
        return 42

    monkeypatch.setattr("ctypes.windll.shell32.ShellExecuteW", mock_shell_execute)
    monkeypatch.setattr("sys.platform", "win32")

    reveal_in_explorer(non_existent)
    assert len(called_args) == 1
    op, file, param = called_args[0]
    assert op == "open"
    assert file == "explorer.exe"
    assert param == f'"{tmp_path.resolve()}"'


def test_shortcut_paths_windows(monkeypatch, tmp_path):
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "user"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    desktop = get_desktop_shortcut_path()
    assert desktop.name == "Kinnow.lnk"
    assert "Desktop" in str(desktop)

    start_menu = get_start_menu_shortcut_path()
    assert start_menu.name == "Kinnow.lnk"
    assert "Start Menu" in str(start_menu)

    startup = get_startup_shortcut_path()
    assert startup.name == "Kinnow.lnk"
    assert "Startup" in str(startup)


def test_toggle_startup(monkeypatch, tmp_path):
    fake_startup = tmp_path / "Startup" / "Kinnow.lnk"
    fake_startup.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("dropwheel.utils.get_startup_shortcut_path", lambda: fake_startup)
    monkeypatch.setattr("dropwheel.utils.create_shortcut", lambda target, lnk: lnk.touch() or True)

    assert not is_startup_enabled()
    assert toggle_startup(True)
    assert is_startup_enabled()

    assert toggle_startup(False)
    assert not is_startup_enabled()


