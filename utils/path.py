from pathlib import Path


def resolve_path(base: str | Path, path: str | Path):
    path = Path(path)
    if path.is_absolute():
        return path.resolve()
    
    return Path(base).resolve() / path


def get_relative_path_to_cwd(path: Path, cwd: str) -> str:
    try:
        p = Path(path)
    except Exception:
        return path

    if cwd:
        try:
            rel_to_cwd = p.relative_to(cwd)
            return str(rel_to_cwd)
        except ValueError:
            pass
        
    return str(p)


def is_binary_path(path: str | Path) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except OSError:
        return False