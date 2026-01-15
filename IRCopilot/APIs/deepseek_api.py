import dataclasses
import os
import time
import dotenv
from typing import Dict, List

import loguru
import openai
from openai import OpenAI

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/chatgpt.log")


@dataclasses.dataclass
class Message:
    ask_id: str = None
    ask: dict = None
    answer: dict = None
    answer_id: str = None
    request_start_timestamp: float = None
    request_end_timestamp: float = None
    time_escaped: float = None


@dataclasses.dataclass
class Conversation:
    conversation_id: str = None
    message_list: List[Message] = dataclasses.field(default_factory=list)

    def __hash__(self):
        return hash(self.conversation_id)

    def __eq__(self, other):
        if not isinstance(other, Conversation):
            return False
        return self.conversation_id == other.conversation_id


class DeepSeekAPI(LLMAPI):
    def __init__(self, config_class):
        self.name = str(config_class.model)  # <--GPT4ConfigClass
        dotenv.load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", None)  # 从环境变量中获取OpenAI的API密钥
        self.client = OpenAI(api_key=api_key, base_url=config_class.api_base)  # 创建一个OpenAI客户端实例
        self.model = config_class.model
        self.history_length = 5  # 维护历史记录中的5条消息
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = config_class.error_wait_time
        self.initialize_logger(config_class.log_dir)

    def initialize_logger(self, log_dir):
        logger.add(sink=os.path.join(log_dir, "deepseek.log"), level="WARNING")

    def _chat_completion(
        self, history: List, model=None, temperature=1.0, image_url: str = None
    ) -> str:
    # def _chat_completion(
    #     self, history: List, model=None, image_url: str = None
    # ) -> str:
        # 如果没有指定模型，使用实例变量self.model；如果self.model也未设置，使用默认模型
        if model is None:
            if self.model is None:
                model = "deepseek-chat"
            else:
                model = self.model

        try:
            response = self.client.chat.completions.create(  # 使用OpenAI的API生成聊天回复
                model=model, messages=history,
                temperature=temperature,
            )
        except openai._exceptions.APIConnectionError as e:  # 处理API连接错误
            logger.warning("API Connection Error. Waiting for {} seconds".format(self.error_wait_time))
            logger.log("Connection Error: ", e)
            time.sleep(self.error_wait_time)
            response = openai.chat.completions.create(
                model=model,
                messages=history,
                temperature=temperature,
            )
        except openai._exceptions.RateLimitError as e:  # 处理API速率限制错误
            logger.warning("Rate limit reached. Waiting for 5 seconds")
            logger.error("Rate Limit Error: ", e)
            time.sleep(self.error_wait_time)
            response = openai.chat.completions.create(
                model=model,
                messages=history,
                temperature=temperature,
            )
        except openai._exceptions.RateLimitError as e:  # 处理API令牌限制错误
            logger.warning("Token size limit reached. The recent message is compressed")
            logger.error("Token size error; will retry with compressed message ", e)
            # 压缩消息以尝试再次发送
            # 1. compress the last message
            history[-1]["content"] = self._token_compression(history)
            # 2. reduce the number of messages in the history. Minimum is 2
            if self.history_length > 2:
                self.history_length -= 1
            history = history[-self.history_length :]
            response = openai.chat.completions.create(
                model=model,
                messages=history,
                temperature=temperature,
            )

        # 检查响应是否有效
        if isinstance(response, tuple):
            logger.warning("Response is invalid. Waiting for 5 seconds")
            try:
                time.sleep(self.error_wait_time)
                response = openai.chat.completions.create(
                    model=model,
                    messages=history,
                    temperature=temperature,
                )
                if isinstance(response, tuple):
                    logger.error("Response is invalid. ")
                    raise Exception("Response is invalid. ")
            except Exception as e:
                logger.error("Response is invalid. ", e)
                raise Exception(
                    "Response is invalid. The most likely reason is the connection to OpenAI is not stable. "
                )

        return response.choices[0].message.content


if __name__ == "__main__":
    # 假设你有一个和 GPT4ConfigClass 类似的配置类
    class MyDeepSeekConfig:
        model = "deepseek-chat"
        api_base = "https://api.deepseek.com"
        log_dir = "logs"
        error_wait_time = 5


    local_config_class = MyDeepSeekConfig()
    claude_api = DeepSeekAPI(local_config_class)

    # 示例：发送一条简单的 "user" 消息
    conversation_history = [
        {"role": "user", "content": "你好，DeepSeek，你能为我做什么？"}
    ]

    result = claude_api._chat_completion(history=conversation_history)
    print("DeepSeek 回复:")
    print(result)
