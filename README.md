# LLMWereWolf 大语言模型狼人杀

## 项目描述
本项目是一个简易的基于文本的狼人游戏实现，支持一名玩家与多个大型语言模型（LLM）共同游戏。由于一些原因，游戏规则可能和经典的狼人游戏规则有所出入，对于游戏规则方面的改进，您可以提交PR。


## 配置API密钥
项目使用`config.json`文件来存储API配置。请在项目根目录下创建`config.json`文件，并按照以下格式填入您的API信息：

```json
{
    "api_configs": [
        {
            "api_base": "https://example.com/api/v1",
            "model_name": "model-name",
            "api_key": "your-api-key-here"
        },
        // 更多配置...
    ]
}
```

**注意**：请勿将`config.json`文件上传到公共仓库，以保护您的API密钥安全。

## 使用示例
1. 启动游戏：
   ```bash
   python main.py
   ```
2. 跟随终端提示进行游戏操作。真人玩家将通过命令行输入参与游戏，而AI玩家将自动进行决策。


## 开源许可证
本项目采用[MIT许可证](LICENSE)，允许自由使用、修改和分发。