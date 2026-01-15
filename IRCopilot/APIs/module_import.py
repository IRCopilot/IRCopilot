import dataclasses
import importlib
import os
import sys
import dotenv

module_mapping = {
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
    "gpt-3.5-turbo-16k": {
        "config_name": "GPT35Turbo16kConfigClass",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
    "gpt-4o-2024-08-06": {
        "config_name": "GPT4o0806",
        "module_name": "chatgpt_api",
        "class_name": "ChatGPTAPI",
    },
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
        "module_name": "gemini_api",  # Assuming you'll create gemini_api.py
        "class_name": "GeminiAPI",  # Assuming class name will be GeminiAPI
    },
    "gemini-1.5": {
        "config_name": "Gemini15ConfigClass",
        "module_name": "gemini_api",  # Assuming you'll create gemini_api.py
        "class_name": "GeminiAPI",  # Assuming class name will be GeminiAPI
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
    dotenv.load_dotenv()
    api_base: str = os.getenv("OPENAI_BASEURL", None)
    openai_key = os.getenv("OPENAI_API_KEY", None)
    # openai_key = ''
    error_wait_time: float = 20
    is_debugging: bool = False
    log_dir: str = None

    def __post_init__(self):
        if self.openai_key is None:
            raise ValueError("API key not set. Please set OPENAI_API_KEY environment variable.")


@dataclasses.dataclass
class GPT4ConfigClass(BaseConfig):
    model: str = "gpt-4"


@dataclasses.dataclass
class GPT35Turbo16kConfigClass(BaseConfig):
    model: str = "gpt-3.5-turbo"


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
class GPT4ALLConfigClass(BaseConfig):
    model: str = "mistral-7b-openorca.Q4_0.gguf"


@dataclasses.dataclass
class TitanConfigClass:
    model: str = "amazon.titan-tg1-large"


@dataclasses.dataclass
class AzureGPT35ConfigClass:
    model: str = "gpt-35-turbo"
    api_type: str = "azure"
    api_base: str = "https://docs-test-001.openai.azure.com/"
    openai_key = os.getenv("OPENAI_API_KEY", None)
    # openai_key = ''
    if openai_key is None:
        print(
            "Your OPENAI_API_KEY is not set. Please set it in the environment variable."
        )
    error_wait_time: float = 20
    is_debugging: bool = False
    log_dir: str = None


@dataclasses.dataclass
class Gemini10ConfigClass:  # New dataclass for Gemini 1.0
    model: str = "gemini-1.0-pro"
    # api_base: str = "https://api.gemini.com/v1"  # Replace with actual API base URL
    gemini_key = ''

    if gemini_key is None:
        print(
            "Your GOOGLE_API_KEY is not set. Please set it in the environment variable."
        )
    error_wait_time: float = 20
    is_debugging: bool = False
    log_dir: str = None


@dataclasses.dataclass
class Gemini15ConfigClass:  # New dataclass for Gemini 1.5
    model: str = "gemini-1.5-pro-latest"
    # api_base: str = "https://api.gemini.com/v1"  # Replace with actual API base URL
    gemini_key = ''
    if gemini_key is None:
        print(
            "Your GOOGLE_API_KEY is not set. Please set it in the environment variable."
        )
    error_wait_time: float = 20
    is_debugging: bool = False
    log_dir: str = None


@dataclasses.dataclass
class ClaudeSonnet:
    model: str = "claude-3-5-sonnet-20240620"
    api_base: str = os.getenv("OPENAI_BASEURL", None)
    # base_url: str = os.getenv("OPENAI_BASEURL", None)
    openai_key = os.getenv("OPENAI_API_KEY", None)
    # api_key = os.getenv("OPENAI_API_KEY", None)
    error_wait_time: float = 20
    is_debugging: bool = False
    log_dir: str = None
    if openai_key is None:
        print(
            "Your OPENAI_API_KEY is not set. Please set it in the environment variable."
        )


@dataclasses.dataclass
class DeepSeek:
    model: str = "deepseek-chat"
    api_base: str = os.getenv("OPENAI_BASEURL", None)
    openai_key = os.getenv("OPENAI_API_KEY", None)
    error_wait_time: float = 20
    is_debugging: bool = False
    log_dir: str = None
    if openai_key is None:
        print(
            "Your OPENAI_API_KEY is not set. Please set it in the environment variable."
        )


@dataclasses.dataclass
class Llama:
    model: str = "llama3-70b-8192"
    # api_base: str = os.getenv("OPENAI_BASEURL", None)
    openai_key = os.getenv("GROQ_API_KEY", None)
    error_wait_time: float = 20
    is_debugging: bool = False
    log_dir: str = None
    if openai_key is None:
        print(
            "Your OPENAI_API_KEY is not set. Please set it in the environment variable."
        )


def dynamic_import(model_name, log_dir) -> object:
    # 检查给定的模块名称是否在预定义的模块映射字典中
    if model_name in module_mapping:
        # 从映射字典中获取模块配置名称、模块导入路径和类名称
        config_name = module_mapping[model_name]["config_name"]  # <--GPT4ConfigClass
        module_name = module_mapping[model_name]["module_name"]  # <--chatgpt_api
        class_name = module_mapping[model_name]["class_name"]  # <--ChatGPTAPI
        # 获取当前模块下的配置类实例
        module_config = getattr(sys.modules[__name__],config_name)  # <--GPT4ConfigClass
        module_config.log_dir = log_dir
        # 动态导入模块
        LLM_module = importlib.import_module(f"IRCopilot.utils.APIs.{module_name}")  # <--chatgpt_api
        LLM_class = getattr(LLM_module, class_name)  # <--ChatGPTAPI
        # 使用配置初始化类
        LLM_class_initialized = LLM_class(module_config)
        return LLM_class_initialized

    else:
        print(f"Model '{model_name}' not supported. Falling back to default model.")
        # fall back to gpt-3.5-turbo-16k
        LLM_class_initialized = dynamic_import("gpt-3.5-turbo-16k", log_dir)
        return LLM_class_initialized


if __name__ == "__main__":
    # a quick local test
    # load gpt4
    gpt4 = dynamic_import("gpt4all", "logs")
    gpt4.send_new_message("hi")
