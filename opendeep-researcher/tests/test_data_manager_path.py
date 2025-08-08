import sys
import os
import importlib
from pathlib import Path

def test_data_directory_is_repo_local(monkeypatch, tmp_path):
    """DataManager should always use repository data directory regardless of CWD."""
    # Ensure the source path is available on sys.path
    src_dir = Path(__file__).resolve().parent.parent / "src"
    sys.path.insert(0, str(src_dir))

    # Change to a temporary directory to simulate running from elsewhere
    monkeypatch.chdir(tmp_path)

    # Import (or reload) the module after changing CWD so that any relative
    # paths would resolve incorrectly if based on the working directory.
    dm = importlib.import_module("utils.data_manager")
    importlib.reload(dm)

    expected = src_dir.parent / "data"
    assert dm.DATA_DIR.resolve() == expected.resolve()
