import os
import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).parent.parent

# The Lambda layer is inserted at the front of sys.path so its modules (e.g.
# dynamodb_utils, response_utils, auth_utils) always take priority over any
# same-named file that may exist inside a function's own subdirectory.
sys.path.insert(0, str(_SERVICE_ROOT / "layers" / "python"))

# Walk every directory under functions/ and append it to sys.path so that
# each Lambda handler and its siblings (models, services, repositories, etc.)
# are importable. Using append (not insert) keeps the layer above at higher
# priority, which matters when two directories contain the same module name
# (e.g. dynamodb_utils in utils/ vs. layers/).
for _dir in sorted((_SERVICE_ROOT / "functions").rglob("*")):
    if _dir.is_dir() and any(_dir.glob("*.py")):
        _dir_str = str(_dir)
        if _dir_str not in sys.path:
            sys.path.append(_dir_str)

# Environment variables expected by Lambda functions
os.environ.setdefault("TABLE_NAME", "UserFridgeNotificationsTable")
os.environ.setdefault("USERS_TABLE_NAME", "UsersTable")
os.environ.setdefault("DEPLOYMENT_TARGET", "local")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
