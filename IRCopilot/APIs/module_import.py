import dataclasses
import importlib
import os
import sys
from typing import Optional, Any

import dotenv
import loguru

logger = loguru.logger

module_mapping = {
    # OpenAI GPT-4 系列
    "gpt-4": {
        "config_name": "GPT4ConfigClass",
        "module_name": "chatgpt_api",  # <--chatgpt_api.py
        "class_name": "ChatGPTAPI",  # <--chatgpt_api.ChatGPTAPI
    },
    "gpt-4-1106-preview": {
        "config_name": "GPT4Turbo",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "gpt-4-o": {
        "config_name": "GPT4O",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "gpt-4o-2024-08-06": {
        "config_name": "GPT4o0806",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    # OpenAI GPT-3.5 系列
    "gpt-3.5-turbo-16k": {
        "config_name": "GPT35Turbo16kConfigClass",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    # OpenAI o1 系列
    "o1-preview": {
        "config_name": "GPTo1Pre",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "o1-preview-2024-09-12": {
        "config_name": "GPTo1Pre0912",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "o1-mini": {
        "config_name": "GPTo1mini",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "o1-mini-2024-09-12": {
        "config_name": "GPTo1mini0912",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "o1-2024-12-17": {
        "config_name": "GPTo11217",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "gpt-5.1-2025-11-13": {
        "config_name": "GPT51_20251113",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    # 其他模型
    "gpt4all": {
        "config_name": "GPT4ALLConfigClass",
        "module_name": "gpt4all_api",
        "class_name": "GPT4ALLAPI",
    },
    "titan": {
        "config_name": "TitanConfigClass",
        "module_name": "titan_api",
        "class_name": "TitanAPI",
    },
    "azure-gpt-3.5": {
        "config_name": "AzureGPT35ConfigClass",
        "module_name": "azure_api",
        "class_name": "AzureGPTAPI",
    },
    "gemini-1.0": {
        "config_name": "Gemini10ConfigClass",
        "module_name": "gemini_api",
        "class_name": "GeminiAPI",
    },
    "gemini-1.5": {
        "config_name": "Gemini15ConfigClass",
        "module_name": "gemini_api",
        "class_name": "GeminiAPI",
    },
    "claude-3-5-sonnet-20240620": {
        "config_name": "ClaudeSonnet",
        "module_name": "claude_api",
        "class_name": "ClaudeAPI",
    },
    "DeepSeek": {
        "config_name": "DeepSeek",
        "module_name": "deepseek_api",
        "class_name": "DeepSeekAPI",
    },
    "Llama": {
        "config_name": "Llama",
        "module_name": "llama_api",
        "class_name": "LlamaAPI",
    },
}


@dataclasses.dataclass
class BaseConfig:
    """基础配置类，包含所有通用字段"""
    model: str = ""
    api_base: Optional[str] = dataclasses.field(default_factory=lambda: os.getenv("OPENAI_BASEURL"))
    openai_key: Optional[str] = dataclasses.field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    # openai_key = ''
    error_wait_time: float = 20.0
    is_debugging: bool = False
    log_dir: Optional[str] = None

    def __post_init__(self):
        if self.openai_key is None:
            raise ValueError("API key not set. Please set OPENAI_API_KEY environment variable.")


@dataclasses.dataclass
class GPT4ConfigClass(BaseConfig):
    model: str = "gpt-4"

@dataclasses.dataclass
class GPT4Turbo(BaseConfig):
    model: str = "gpt-4-1106-preview"

@dataclasses.dataclass
class GPT4O(BaseConfig):
    model: str = "gpt-4o-2024-05-13"

@dataclasses.dataclass
class GPT4o0806(BaseConfig):
    model: str = "gpt-4o-2024-08-06"

@dataclasses.dataclass
class GPT35Turbo16kConfigClass(BaseConfig):
    model: str = "gpt-3.5-turbo"

@dataclasses.dataclass
class GPTo1Pre(BaseConfig):
    model: str = "o1-preview"

@dataclasses.dataclass
class GPTo1Pre0912(BaseConfig):
    model: str = "o1-preview-2024-09-12"

@dataclasses.dataclass
class GPTo1mini(BaseConfig):
    model: str = "o1-mini"

@dataclasses.dataclass
class GPTo1mini0912(BaseConfig):
    model: str = "o1-mini-2024-09-12"

@dataclasses.dataclass
class GPTo11217(BaseConfig):
    model: str = "o1-2024-12-17"

@dataclasses.dataclass
class GPT51_20251113(BaseConfig):
    model: str = "gpt-5.1-2025-11-13"

@dataclasses.dataclass
class GPT4ALLConfigClass(BaseConfig):
    model: str = "mistral-7b-openorca.Q4_0.gguf"
    openai_key: Optional[str] = "local"


@dataclasses.dataclass
class TitanConfigClass(BaseConfig):
    model: str = "amazon.titan-tg1-large"


@dataclasses.dataclass
class AzureGPT35ConfigClass(BaseConfig):
    model: str = "gpt-35-turbo"
    api_type: str = "azure"
    api_base: str = "https://docs-test-001.openai.azure.com/"

    def __post_init__(self):
        if not self.openai_key:
            logger.warning("Your OPENAI_API_KEY for Azure is not set.")


@dataclasses.dataclass
class GeminiBaseConfig(BaseConfig):
    """Gemini 专用基类，处理 gemini_key"""
    gemini_key: Optional[str] = dataclasses.field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))
    
    def __post_init__(self):
        if not self.gemini_key:
            logger.warning("Your GOOGLE_API_KEY is not set.")

@dataclasses.dataclass
class Gemini10ConfigClass(GeminiBaseConfig):
    model: str = "gemini-1.0-pro"

@dataclasses.dataclass
class Gemini15ConfigClass(GeminiBaseConfig):
    model: str = "gemini-1.5-pro-latest"


@dataclasses.dataclass
class ClaudeSonnet(BaseConfig):
    model: str = "claude-3-5-sonnet-20240620"
    
    def __post_init__(self):
        if not self.openai_key:
             logger.warning("Your OPENAI_API_KEY (for Claude proxy) is not set.")


@dataclasses.dataclass
class DeepSeek(BaseConfig):
    model: str = "deepseek-chat"
    
    def __post_init__(self):
        if not self.openai_key:
             logger.warning("Your OPENAI_API_KEY (for DeepSeek) is not set.")


@dataclasses.dataclass
class Llama(BaseConfig):
    model: str = "llama3-70b-8192"
    openai_key: Optional[str] = dataclasses.field(default_factory=lambda: os.getenv("GROQ_API_KEY"))

    def __post_init__(self):
        if not self.openai_key:
             logger.warning("Your GROQ_API_KEY is not set.")



def dynamic_import(model_name: str, log_dir: str) -> object:
    """
    根据模型名称动态加载对应的 API 类实例。
    """
    # 检查模型是否支持
    if model_name not in module_mapping:
        logger.warning(f"Model '{model_name}' not supported. Falling back to default model (gpt-3.5-turbo-16k).")
        return dynamic_import("gpt-3.5-turbo-16k", log_dir)

    try:
        # 从映射字典中获取模块配置名称、模块导入路径和类名称
        mapping = module_mapping[model_name]
        config_name = mapping["config_name"]    # <--GPT4ConfigClass
        module_name = mapping["module_name"]    # <--chatgpt_api
        class_name = mapping["class_name"]      # <--ChatGPTAPI

        # 1. 获取当前模块中的配置类
        if not hasattr(sys.modules[__name__], config_name):
            raise ImportError(f"Config class '{config_name}' not found in current module.")
        
        ConfigClass = getattr(sys.modules[__name__], config_name)   # <--GPT4ConfigClass
        
        # 2. 实例化配置类并设置日志目录
        # 注意：这里假设 ConfigClass 接受无参构造或所有参数都有默认值
        # dataclasses 默认生成的 __init__ 允许关键字参数
        module_config = ConfigClass()
        module_config.log_dir = log_dir

        # 3. 动态导入 API 模块
        # 假设路径结构为 IRCopilot.utils.APIs.<module_name>
        full_module_path = f"IRCopilot.utils.APIs.{module_name}"    # <--chatgpt_api
        LLM_module = importlib.import_module(full_module_path)
        
        # 4. 获取 API 类并实例化
        LLM_class = getattr(LLM_module, class_name)     # <--ChatGPTAPI
        llm_instance = LLM_class(module_config)
        
        return llm_instance

    except (ImportError, AttributeError, ValueError) as e:
        logger.error(f"Failed to initialize model '{model_name}': {e}")
        raise e
    

if __name__ == "__main__":
    # 本地测试
    # 确保有一个 fallback 或真实存在的模型用于测试
    test_model = "gpt-4" 
    print(f"Testing dynamic import for {test_model}...")
    
    # 模拟 logs 目录
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    try:
        # 注意：这需要实际的目录结构存在才能运行成功，否则会报 ModuleNotFoundError
        gpt_instance = dynamic_import(test_model, "logs")
        print(f"Successfully initialized: {gpt_instance}")
    except Exception as e:
        print(f"Test failed (Expected if files are missing): {e}")
