from pathlib import Path


def _get_repo_root() -> Path:
    """Locate the repository root relative to the tests directory."""
    for parent in Path(__file__).resolve().parents:
        if parent.name == "tests":
            return parent.parent
    raise RuntimeError("Unable to locate repository root from tests directory.")


def test_dockerfile_copies_source_before_editable_install():
    dockerfile = _get_repo_root() / "Dockerfile"
    content = dockerfile.read_text().splitlines()

    try:
        install_index = next(
            index
            for index, line in enumerate(content)
            if "pip install" in line and "-e" in line
        )
    except StopIteration:
        raise AssertionError("Dockerfile never installs the project in editable mode.")

    copy_lines = [
        (index, line.strip().lower())
        for index, line in enumerate(content)
        if line.strip().lower().startswith("copy")
    ]

    if not any(
        index < install_index
        and (
            " /app/src" in line
            or line.endswith(" .")
            or " /app/src/" in line
        )
        for index, line in copy_lines
    ):
        raise AssertionError(
            "Expected Dockerfile to copy the source tree into /app before pip install -e ."
        )
