import dataclasses
import os
import time
from typing import Any, Dict, List, Optional, Union

import loguru
import openai

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/chatgpt.log")


@dataclasses.dataclass
class Message:
    """定义单条消息的数据结构"""
    ask_id: Optional[str] = None
    ask: Optional[List[Dict[str, Any]]] = None          # 请求内容 (OpenAI 消息格式)
    answer: Optional[List[Dict[str, Any]]] = None       # 回答内容 (OpenAI 消息格式)
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


class AzureGPTAPI(LLMAPI):
    def __init__(self, config_class, use_langfuse_logging=False):
        self.name = str(config_class.model)
        
        # 配置 Azure OpenAI
        openai.api_type = "azure"
        openai.api_key = os.getenv("OPENAI_API_KEY", None)
        openai.api_base = config_class.api_base
        openai.api_version = "2023-05-15" # 建议显式指定版本，或者从 config 读取
        
        self.model = config_class.model
        self.log_dir = config_class.log_dir
        self.history_length = 5  # 保留最近 5 条历史记录
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = 3  # 错误等待时间 (秒)

        # 初始化日志
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
        logger.add(sink=os.path.join(self.log_dir, "chatgpt.log"), level="WARNING")

    def _chat_completion(
        self, history: List, model="gpt-3.5-turbo-16k", temperature=0.5
    ) -> str:
        # 如果配置的是 gpt-4，强制使用 gpt-4，否则使用默认 (通常是更便宜的模型)
        if self.model == "gpt-4":
            model = "gpt-4"

        # 最大重试次数，防止无限循环
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                response = openai.ChatCompletion.create(
                    engine=model, # Azure 使用 engine 参数而非 model (取决于 SDK 版本，通常 Azure 对应 deployment_id)
                    messages=history,
                    temperature=temperature,
                )
                
                # 检查响应是否合法 (防止极少数情况下的异常返回)
                if isinstance(response, tuple):
                    logger.warning("Response is a tuple (invalid). Retrying...")
                    raise ValueError("Invalid response type: tuple")

                return response["choices"][0]["message"]["content"]

            except (openai.error.Timeout, openai.error.APIConnectionError) as e:
                logger.warning(f"Connection Error. Waiting {self.error_wait_time}s. ({e})")
                time.sleep(self.error_wait_time)
                
            except openai.error.RateLimitError as e:
                logger.warning("Rate limit reached. Waiting 5s.")
                time.sleep(5)
                
            except openai.error.InvalidRequestError as e:
                # 处理 Token 超限错误 (Context Length Exceeded)
                if "context_length_exceeded" in str(e) or "maximum context length" in str(e):
                    logger.warning(f"Token limit reached. Compressing message... ({e})")
                    
                    # 策略 1: 压缩最后一条消息 (调用父类方法)
                    if hasattr(self, "token_compression"):
                        history[-1]["content"] = self.token_compression(history)
                    
                    # 策略 2: 减少历史记录长度
                    if self.history_length > 2:
                        self.history_length -= 1
                    history = history[-self.history_length:]
                    
                    # 不增加 attempt 计数，立即使用新 history 重试
                    continue
                else:
                    # 其他类型的 InvalidRequest (如参数错误) 不应重试
                    logger.error(f"Invalid Request Error: {e}")
                    raise e
            
            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed after {max_retries} attempts. Last error: {e}")
                time.sleep(self.error_wait_time)

            attempt += 1
            
        raise Exception("Chat completion failed after maximum retries.")