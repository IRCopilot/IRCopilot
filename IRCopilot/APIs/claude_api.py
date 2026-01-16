import dataclasses
import os
import time
from typing import Any, Dict, List, Optional

import anthropic
import dotenv
import loguru

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/claude.log")

@dataclasses.dataclass
class Message:
    """定义单条消息的数据结构"""
    ask_id: Optional[str] = None
    ask: Optional[List[Dict[str, Any]]] = None          # 请求内容
    answer: Optional[List[Dict[str, Any]]] = None       # 回答内容
    answer_id: Optional[str] = None
    request_start_timestamp: float = 0.0    # 请求开始时间戳
    request_end_timestamp: float = 0.0      # 请求结束时间戳
    time_escaped: float = 0.0               # 请求耗时


@dataclasses.dataclass
class Conversation:
    """存储完整对话历史的结构"""
    conversation_id: Optional[str] = None
    message_list: List[Message] = dataclasses.field(default_factory=list)

    def __hash__(self):
        return hash(self.conversation_id)

    def __eq__(self, other):
        if not isinstance(other, Conversation):
            return False
        return self.conversation_id == other.conversation_id


class ClaudeAPI(LLMAPI):
    """
    基于 Anthropic 官方 SDK 的 Claude 接口封装类。
    """

    def __init__(self, config_class):
        self.name = str(config_class.model)
        dotenv.load_dotenv()

        # 优先从 Config 获取 Key (兼容 module_import.py 中的 openai_key 字段), 其次尝试标准环境变量
        # 注意: 这里保留了读取 "OPENAI_API_KEY" 的逻辑以兼容你的 Config 类定义，
        # 但实际使用 Anthropic SDK 时，这应该是一个有效的 Anthropic Key 或 Proxy Key。
        api_key = (
            getattr(config_class, "openai_key", None) 
            or os.getenv("ANTHROPIC_API_KEY") 
            or os.getenv("OPENAI_API_KEY")
        )
        
        base_url = getattr(config_class, "api_base", None)

        self.client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
        )
        
        self.model = config_class.model or "claude-3-5-sonnet-20240620"
        self.history_length = 5
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = float(getattr(config_class, "error_wait_time", 5.0))
        
        self.initialize_logger(config_class.log_dir)

    def initialize_logger(self, log_dir: str):
        """初始化日志记录器"""
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        # log_path = os.path.join(log_dir, "claude.log") if log_dir else "claude.log"
        # logger.add(sink=log_path, level="WARNING") 
        # (保持原注释状态，按需开启)

    def _chat_completion(
        self, 
        history: List[Dict[str, Any]], 
        model: Optional[str] = None, 
        temperature: float = 0.5, 
        image_url: Optional[str] = None
    ) -> str:
        """
        核心方法：调用 Anthropic Messages API。
        包含重试机制。
        """
        target_model = model if model else self.model

        # Anthropic 的 System Prompt 通常是顶级参数，不是 messages 列表的一部分。
        # 如果 history 中包含 role='system'，Anthropic SDK 可能会报错 (取决于版本和 strict mode)。
        # 为了不改变原有逻辑结构，这里保持直接传递 history，但建议上层调用者将 system prompt 分离。
        
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                response = self.client.messages.create(
                    model=target_model,
                    max_tokens=4096,  # Claude 3.5 Sonnet 支持较大的输出 
                    temperature=temperature,
                    messages=history
                    # system="You are a helpful assistant." # 如果需要 system prompt，应在此处添加
                )
                
                # 修正解析逻辑：Anthropic SDK 返回的是对象，不是字典
                # 正确获取文本内容的方式是 response.content[0].text
                if response.content and len(response.content) > 0:
                    return response.content[0].text
                return ""

            except anthropic.APIConnectionError as e:
                logger.warning(f"Anthropic Connection Error. Waiting {self.error_wait_time}s. ({e})")
                time.sleep(self.error_wait_time)

            except anthropic.RateLimitError as e:
                logger.warning(f"Anthropic Rate Limit. Waiting {self.error_wait_time}s. ({e})")
                time.sleep(self.error_wait_time)
            
            except anthropic.BadRequestError as e:
                logger.error(f"Anthropic Bad Request: {e}")
                # 400 错误通常不可重试（如参数错误），直接抛出
                raise e

            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(self.error_wait_time)
            
            attempt += 1
            
        raise Exception("Claude chat completion failed after maximum retries.")


if __name__ == "__main__":
    # 模拟测试配置类
    class MyClaudeConfig:
        model = "claude-3-5-sonnet-20240620"
        # 假设这里配置的是一个代理地址，或者留空使用官方地址
        api_base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        log_dir = "logs"
        error_wait_time = 2
        # 模拟从 BaseConfig 继承来的字段
        openai_key = os.getenv("ANTHROPIC_API_KEY", "sk-ant-xxx") 

    print("--- Test Start ---")
    try:
        local_config = MyClaudeConfig()
        claude_api = ClaudeAPI(local_config)

        # 示例：发送简单的 user 消息
        # 注意：Anthropic messages 列表必须以 user 开头 (Claude 2.x/3.x 限制)
        conversation_history = [
            {"role": "user", "content": "Hello Claude, concise reply only: What version are you?"}
        ]

        print("Sending request...")
        result = claude_api._chat_completion(history=conversation_history)
        print(f"Claude Response: {result}")

    except Exception as e:
        print(f"Test failed (Expected if API Key is missing): {e}")