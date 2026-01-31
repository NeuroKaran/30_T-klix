
import sys
import os
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from config import get_config, reload_config

def test_config_paths_are_absolute():
    """Verify that critical paths in config are absolute."""
    config = reload_config()
    
    assert config.project_root.is_absolute(), "project_root should be absolute"
    assert os.path.isabs(config.mem0_qdrant_path), "mem0_qdrant_path should be absolute"

def test_qdrant_path_is_shared():
    """
    Verify that the Qdrant path is the same regardless of CWD.
    This simulates running from root vs running from Nemo/ subdir.
    """
    # 1. Get config from Root
    original_cwd = os.getcwd()
    os.chdir(project_root)
    config_root = reload_config()
    path_from_root = config_root.mem0_qdrant_path
    
    # 2. Get config from Nemo subdir
    nemo_dir = project_root / "Nemo"
    os.makedirs(nemo_dir, exist_ok=True)
    os.chdir(nemo_dir)
    config_nemo = reload_config()
    path_from_nemo = config_nemo.mem0_qdrant_path
    
    # Restore CWD
    os.chdir(original_cwd)
    
    # Assertions
    print(f"\nPath from Root: {path_from_root}")
    print(f"Path from Nemo: {path_from_nemo}")
    
    assert path_from_root == path_from_nemo, "Qdrant paths should be identical from different CWDs"
    assert Path(path_from_root) == (project_root / ".qdrant_data").resolve(), "Path should resolve to project_root/.qdrant_data"

if __name__ == "__main__":
    # Allow running directly
    try:
        test_config_paths_are_absolute()
        test_qdrant_path_is_shared()
        print("✅ Config tests passed!")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
