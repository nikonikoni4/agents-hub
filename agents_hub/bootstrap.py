"""资源初始化模块

启动时扫描 template 目录下所有文件，检查目标路径是否存在，不存在则复制。

- 打包环境：bundle_dir 为 PyInstaller 的 sys._MEIPASS，模板根为 bundle_dir/template/
- 非打包环境：模板根为项目根目录/template/
"""

import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def initialize_resources() -> None:
    """初始化资源文件

    扫描 template 目录下所有文件，不存在于目标路径则复制。
    """
    from agents_hub.config.config import config

    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        template_dir = bundle_dir / "template"
    else:
        template_dir = Path(__file__).resolve().parent.parent / "template"

    data_path = config.data_path

    if not template_dir.exists():
        logger.warning(f"内嵌 template 目录不存在，跳过资源初始化: {template_dir}")
        return

    for source in template_dir.rglob("*"):
        if not source.is_file():
            continue

        rel = source.relative_to(template_dir)
        target = data_path / rel

        if target.exists():
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        logger.info(f"已初始化资源文件: {target}")
