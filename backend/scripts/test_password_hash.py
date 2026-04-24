from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import hash_password, verify_password


def main() -> None:
    password = "12345678"
    hashed_value = hash_password(password)
    print(f"hashed={hashed_value}")
    print(f"verify={verify_password(password, hashed_value)}")


if __name__ == "__main__":
    main()
