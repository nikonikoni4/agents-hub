import os
from pathlib import Path

base = Path(r"D:\desktop\软件开发\agents-hub\explore\skill-link-test")
src = base / "global_skill"
dst = base / "role_skills" / "py_symlink"
print("python os.symlink:", end=" ")
try:
    os.symlink(src, dst, target_is_directory=True)
    print("OK", "is_symlink=", dst.is_symlink(), "exists=", dst.exists())
    print("  read skill.json=", (dst / "skill.json").read_text(encoding="utf-8"))
except Exception as e:
    print(type(e).__name__, e)
