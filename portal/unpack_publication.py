"""Read the workflow's Pages tar using the same narrow publication allowlist."""
import sys
import tarfile
from pathlib import Path

from build import PUBLIC_FILES, check_publication


def unpack(archive, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be empty')
    files = {}
    with tarfile.open(archive) as tar:
        for member in tar:
            name = member.name.removeprefix('./')
            if member.isdir() and name in ('', '.', 'ja'):
                continue
            if not member.isfile() or name not in PUBLIC_FILES or name in files or member.size > 1_000_000:
                raise ValueError('Unexpected publication archive member')
            files[name] = tar.extractfile(member).read()
    if set(files) != PUBLIC_FILES:
        raise ValueError('Incomplete publication archive')
    # Never extract archive paths or links; write only validated filenames.
    for name, content in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    check_publication(output)


if __name__ == '__main__':
    unpack(Path(sys.argv[1]), Path(sys.argv[2]))
