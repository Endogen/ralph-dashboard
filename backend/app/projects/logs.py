"""Cursor-based log reads: reconnects and tab changes never replay an append."""
from pathlib import Path
import codecs


def read_log(path: Path, offset: int | None = None, generation: str | None = None) -> dict:
    try:
        with path.open("rb") as handle:
            stat = path.stat()
            current = f"{stat.st_dev}:{stat.st_ino}"
            reset = offset is None or generation != current or offset > stat.st_size
            start = max(0, stat.st_size - 512 * 1024) if reset else max(0, offset)
            handle.seek(start)
            raw = handle.read(512 * 1024)
            decoder = codecs.getincrementaldecoder("utf-8")("replace")
            text = decoder.decode(raw, final=False)
            pending, _ = decoder.getstate()
            end = start + len(raw) - len(pending)
            return {"text": text, "offset": end, "generation": current, "reset": reset,
                    "has_more": end < stat.st_size and end > start}
    except FileNotFoundError:
        return {"text": "", "offset": 0, "generation": "", "reset": True, "has_more": False}
