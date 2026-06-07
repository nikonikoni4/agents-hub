"""
测试样例模块
用于验证前端代码预览和 diff 功能
"""

from typing import List, Optional


class DataProcessor:
    """数据处理器类"""

    def __init__(self, name: str):
        self.name = name
        self.data: List[str] = []

    def add_item(self, item: str) -> None:
        """添加数据项"""
        self.data.append(item)

    def process(self) -> List[str]:
        """处理数据并返回结果"""
        result = []
        for item in self.data:
            processed = item.strip().upper()
            result.append(processed)
        return result

    def get_summary(self) -> str:
        """获取数据摘要"""
        return f"{self.name}: {len(self.data)} items"


def calculate_sum(numbers: List[int]) -> int:
    """计算数字列表的总和"""
    total = 0
    for num in numbers:
        total += num
    return total


def find_max(numbers: List[int]) -> Optional[int]:
    """查找最大值"""
    if not numbers:
        return None
    return max(numbers)


def main():
    """主函数"""
    processor = DataProcessor("test")
    processor.add_item("hello")
    processor.add_item("world")
    result = processor.process()
    print(result)
    print(processor.get_summary())

    numbers = [1, 2, 3, 4, 5]
    print(f"Sum: {calculate_sum(numbers)}")
    print(f"Max: {find_max(numbers)}")


if __name__ == "__main__":
    main()
