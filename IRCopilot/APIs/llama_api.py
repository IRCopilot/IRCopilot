import dataclasses
import os
import time
from typing import Any, Dict, List, Optional

import dotenv
import loguru
import groq
from groq import Groq

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()


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


class LlamaAPI(LLMAPI):
    """
    基于 Groq 官方 SDK 的 Llama 接口封装类。
    """

    def __init__(self, config_class):
        self.name = str(config_class.model)
        dotenv.load_dotenv()

        # 获取 API Key
        # 优先从 config 获取 (可能叫 openai_key 因为复用了 BaseConfig)，其次环境变量
        api_key = getattr(config_class, "openai_key", None) or os.getenv("GROQ_API_KEY")
        
        self.client = Groq(
            api_key=api_key,
        )
        
        self.model = config_class.model or "llama3-70b-8192"
        self.history_length = 5
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = float(getattr(config_class, "error_wait_time", 5.0))
        
        self.initialize_logger(config_class.log_dir)

    def initialize_logger(self, log_dir: str):
        """初始化日志"""
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        logger.add(sink=os.path.join(log_dir, "llama.log"), level="WARNING")

    def _chat_completion(
        self, 
        history: List[Dict[str, Any]], 
        model: Optional[str] = None, 
        temperature: float = 0.5, 
        image_url: Optional[str] = None
    ) -> str:
        """
        核心方法：调用 Groq API。
        包含重试机制。
        """
        target_model = model if model else self.model
        
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=target_model,
                    messages=history,
                    temperature=temperature,
                    max_tokens=2048,
                )
                
                # 解析响应
                # Groq SDK 返回的对象通常可以直接访问 choices
                if response.choices:
                    return response.choices[0].message.content
                return ""

            except groq.APIConnectionError as e:
                logger.warning(f"Groq Connection Error. Waiting {self.error_wait_time}s. ({e})")
                time.sleep(self.error_wait_time)

            except groq.RateLimitError as e:
                logger.warning(f"Groq Rate Limit. Waiting {self.error_wait_time}s. ({e})")
                time.sleep(self.error_wait_time)
            
            except groq.BadRequestError as e:
                logger.error(f"Groq Bad Request: {e}")
                raise e

            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(self.error_wait_time)

            attempt += 1
            
        raise Exception("Groq chat completion failed after retries.")


if __name__ == "__main__":
    # 模拟 Config
    class MyLlamaConfig:
        model = "llama3-70b-8192"
        log_dir = "logs"
        error_wait_time = 5
        openai_key = os.getenv("GROQ_API_KEY")

    print("--- Test Start ---")
    try:
        config = MyLlamaConfig()
        llama_api = LlamaAPI(config)

        # 示例：发送 user 消息
        conversation_history = [
            {"role": "user", "content": "Hello Llama, introduce yourself briefly."}
        ]

        print("Sending request...")
        result = llama_api._chat_completion(history=conversation_history)
        print(f"Llama Response: {result}")

    except Exception as e:
        print(f"Test failed (Expected if API Key is missing): {e}")