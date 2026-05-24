skill_manager 主要功能，管理skill文件，主要位置： `local_data_path / skills`
    1. 预设一些skill文件，注意role的skill不属于skill_manager的职能范围
    2. 讲`local_data_path / skills`复制给各个role，前端表现为在role的配置界面添加skill
    3. 提供网络搜索skills并下载的功能[p2]，暂时不是实现
这个不一定以类或模块的形式出现，只是业务中的一个部分