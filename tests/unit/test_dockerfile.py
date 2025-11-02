from pathlib import Path


def test_dockerfile_copies_source_before_editable_install():
    dockerfile = Path(__file__).resolve().parents[2] / "Dockerfile"
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
