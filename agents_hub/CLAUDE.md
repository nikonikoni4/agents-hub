# 后端通用规则

1. 数据路径使用，统一使用配置模块的config.data_path
```python
from agents_hub.config import config
config.data_path
```
2. 编写错误处理里必须查看docs\coding-rules\backend-style.md