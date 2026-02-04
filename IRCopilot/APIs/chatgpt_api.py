import dataclasses
import os
import time
from typing import Any, Dict, List, Optional, Union

import dotenv
import loguru
import openai
from openai import OpenAI

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/chatgpt.log")


@dataclasses.dataclass
class Message:
    ask_id: Optional[str] = None
    ask: Optional[List[Dict[str, Any]]] = None          # 请求内容 (OpenAI 消息格式)
    answer: Optional[List[Dict[str, Any]]] = None       # 回答内容 (OpenAI 消息格式)
    answer_id: Optional[str] = None
    request_start_timestamp: float = 0.0    # 请求开始时间戳
    request_end_timestamp: float = 0.0      # 请求结束时间戳
    time_escaped: float = 0.0    # 请求耗时


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


class ChatGPTAPI(LLMAPI):
    """
    基于 OpenAI 官方 SDK 的 ChatGPT 接口封装类。
    支持自动重试、错误处理和多模态输入（图片）。
    """

    def __init__(self, config_class):
        super().__init__(config_class)  # 确保父类被正确初始化
        self.name = str(config_class.model)
        
        # 加载环境变量
        dotenv.load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY") or getattr(config_class, "api_key", None)
        
        # 初始化 OpenAI 客户端
        self.client = OpenAI(api_key=api_key, base_url=config_class.api_base)
        self.model = config_class.model or "gpt-4o-2024-05-13"
        
        self.history_length = 5
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = float(getattr(config_class, "error_wait_time", 2.0))
        self.request_timeout = float(getattr(config_class, "request_timeout", 60))
        self.retry_attempts = int(getattr(config_class, "retry_attempts", 3))
        self.retry_wait = float(getattr(config_class, "retry_wait", 2))
        
        self.initialize_logger(config_class.log_dir)

    def initialize_logger(self, log_dir: str):
        """初始化日志记录器"""
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        logger.add(sink=os.path.join(log_dir, "chatgpt.log"), level="WARNING")

    def _chat_completion(
        self, 
        history: List[Dict[str, Any]], 
        model: Optional[str] = None, 
        temperature: float = 0.5, 
        image_url: Optional[str] = None
    ) -> str:
        """
        核心方法：调用 OpenAI Chat Completion API。
        包含重试机制以处理连接错误、速率限制和 Token 超限。
        """
        # 确定使用的模型
        target_model = model if model else self.model

        # 最大重试次数
        max_retries = self.retry_attempts
        current_attempt = 0

        while current_attempt < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=target_model,
                    messages=history,
                    temperature=temperature,
                    timeout=self.request_timeout,
                )
                
                # 检查响应有效性 (OpenAI SDK v1 返回对象，非 tuple)
                if not response or not response.choices:
                    raise ValueError("Empty response from OpenAI API")

                return response.choices[0].message.content

            except openai.APIConnectionError as e:
                logger.warning(f"API Connection Error. Waiting {self.error_wait_time}s. Detail: {e}")
                time.sleep(self.error_wait_time)
                
            except openai.RateLimitError as e:
                logger.warning(f"Rate limit reached. Waiting {self.error_wait_time}s. Detail: {e}")
                time.sleep(self.error_wait_time)

            except getattr(openai, "APITimeoutError", Exception) as e:
                logger.warning(f"Request timeout. Waiting {self.retry_wait}s. Detail: {e}")
                time.sleep(self.retry_wait)
                
            except openai.BadRequestError as e:
                # 专门处理 Context Length Exceeded (Token 超限)
                if "context_length_exceeded" in str(e):
                    logger.warning("Token limit reached. Attempting to compress history.")
                    
                    # 1. 压缩最后一条消息 (调用父类 LLMAPI 的方法)
                    if hasattr(self, "_token_compression"):
                        history[-1]["content"] = self._token_compression(history)
                    
                    # 2. 减少历史记录长度
                    if self.history_length > 2:
                        self.history_length -= 1
                    history = history[-self.history_length:]
                    
                    # 不增加 attempt 计数，立即重试
                    continue 
                else:
                    # 其他类型的 BadRequest 直接抛出
                    logger.error(f"Bad Request: {e}")
                    raise e

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                # 对于未知错误，稍微等待后重试
                time.sleep(self.error_wait_time)

            current_attempt += 1

        raise Exception(f"Failed to get response after {max_retries} attempts.")
