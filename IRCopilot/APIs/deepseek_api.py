import dataclasses
import os
import time
from typing import Any, Dict, List, Optional

import dotenv
import loguru
import openai
from openai import OpenAI

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/deepseek.log")


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


class DeepSeekAPI(LLMAPI):
    """
    基于 OpenAI SDK (兼容接口) 的 DeepSeek 接口封装类。
    """

    def __init__(self, config_class):
        self.name = str(config_class.model)
        dotenv.load_dotenv()
        
        # 获取 API Key 和 Base URL
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        self.client = OpenAI(
            api_key=api_key, 
            base_url=config_class.api_base
        )
        
        self.model = config_class.model or "deepseek-chat"
        self.history_length = 5
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = float(getattr(config_class, "error_wait_time", 5.0))
        
        self.initialize_logger(config_class.log_dir)

    def initialize_logger(self, log_dir: str):
        """初始化日志记录器"""
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        logger.add(sink=os.path.join(log_dir, "deepseek.log"), level="WARNING")

    def _chat_completion(
        self, 
        history: List[Dict[str, Any]], 
        model: Optional[str] = None, 
        temperature: float = 1.0, 
        image_url: Optional[str] = None
    ) -> str:
        """
        核心方法：调用 DeepSeek API (通过 OpenAI SDK)。
        包含自动重试机制。
        """
        target_model = model if model else self.model

        max_retries = 2  # 相当于原逻辑：失败后重试一次
        attempt = 0

        while attempt < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=target_model,
                    messages=history,
                    temperature=temperature,
                )

                # 检查响应有效性 (保留原有的 tuple 检查逻辑，虽然 v1 sdk 通常返回对象)
                if isinstance(response, tuple):
                    logger.warning("Response is invalid (tuple). Waiting and retrying...")
                    raise ValueError("Invalid response type: tuple")

                return response.choices[0].message.content

            except openai.APIConnectionError as e:
                logger.warning(f"API Connection Error. Waiting {self.error_wait_time}s. ({e})")
                time.sleep(self.error_wait_time)

            except openai.RateLimitError as e:
                logger.warning(f"Rate limit reached. Waiting 5s. ({e})")
                time.sleep(self.error_wait_time)

            except openai.BadRequestError as e:
                # 处理 Token 超限 (原代码此处捕获的是 RateLimitError，但这通常是 BadRequest)
                # 检查是否为 Context Length Exceeded
                if "context_length_exceeded" in str(e) or "token" in str(e).lower():
                    logger.warning("Token size limit reached. Compressing message...")
                    
                    # 1. 压缩最后一条消息
                    if hasattr(self, "_token_compression"):
                        history[-1]["content"] = self._token_compression(history)
                    
                    # 2. 减少历史记录
                    if self.history_length > 2:
                        self.history_length -= 1
                    history = history[-self.history_length:]
                    
                    # 立即重试
                    continue
                else:
                    # 其他 BadRequest 直接抛出
                    logger.error(f"Bad Request: {e}")
                    raise e

            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                # 最后一次尝试如果失败，则抛出异常
                if attempt == max_retries - 1:
                    raise Exception(f"DeepSeek API failed: {e}")
                time.sleep(self.error_wait_time)

            attempt += 1

        raise Exception("DeepSeek completion failed after retries.")


if __name__ == "__main__":
    # 模拟配置类
    class MyDeepSeekConfig:
        model = "deepseek-chat"
        api_base = "https://api.deepseek.com"
        log_dir = "logs"
        error_wait_time = 5
        # 模拟环境变量读取
        openai_key = os.getenv("DEEPSEEK_API_KEY")

    print("--- Test Start ---")
    try:
        local_config = MyDeepSeekConfig()
        deepseek_api = DeepSeekAPI(local_config)

        # 示例：发送 user 消息
        conversation_history = [
            {"role": "user", "content": "你好，DeepSeek，简短介绍一下你自己。"}
        ]

        print("Sending request...")
        result = deepseek_api._chat_completion(history=conversation_history)
        print(f"DeepSeek Response: {result}")

    except Exception as e:
        print(f"Test failed (Expected if API Key is missing): {e}")