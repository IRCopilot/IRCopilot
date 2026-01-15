# 实现了一个与OpenAI ChatGPT API交互的类LLMAPI，支持创建和管理对话，以及在对话中发送消息

import dataclasses
import inspect
import os
import re
import time
from typing import Any, Dict, List, Tuple
from uuid import uuid1

import loguru
import openai
import tiktoken
from tenacity import *

from IRCopilot.config.chat_config import ChatGPTConfig

logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/chatgpt.log")


@dataclasses.dataclass
class Message:
    ask_id: str = None  # 消息请求ID
    ask: dict = None  # 请求的消息内容
    answer: dict = None  # 回答的消息内容
    answer_id: str = None  # 消息回答ID
    request_start_timestamp: float = None  # 请求开始时间戳
    request_end_timestamp: float = None  # 请求结束时间戳
    time_escaped: float = None  # 请求耗时


@dataclasses.dataclass
class Conversation:
    conversation_id: str = None  # 对话ID
    message_list: List[Message] = dataclasses.field(default_factory=list)  # 消息列表

    def __hash__(self):
        return hash(self.conversation_id)  # 返回对话ID的哈希值

    def __eq__(self, other):
        if not isinstance(other, Conversation):
            return False
        return self.conversation_id == other.conversation_id  # 比较两个对话是否相等


class LLMAPI:
    def __init__(self, config: ChatGPTConfig):
        self.name = "LLMAPI_base_class"  # LLMAPI基类的名称
        self.config = config  # 配置
        openai.api_key = config.openai_key  # 设置OpenAI的API密钥
        openai.proxy = config.proxies  # 设置代理
        openai.api_base = config.api_base  # 设置API基础URL
        self.log_dir = config.log_dir  # 日志目录
        self.history_length = 5  # 保持5条消息在历史记录中（5次聊天记忆）
        self.conversation_dict: Dict[str, Conversation] = {}  # 对话字典

        logger.add(sink=os.path.join(self.log_dir, "chatgpt.log"), level="WARNING")  # 添加日志记录

    # 计算消息中的令牌数
    def _count_token(self, messages) -> int:
        """
        计算消息中的令牌数

        参数
        ----------
            messages: 消息列表
        返回值
        -------
            num_tokens: int
        """
        # 计算令牌数量。使用gpt-3.5-turbo-0301模型，略有不同于gpt-4
        # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        model = "gpt-3.5-turbo-0301"
        tokens_per_message = (
            4  # 每条消息的格式为 <|start|>{role/name}\n{content}<|end|>\n
        )
        tokens_per_name = -1  # 如果有名称，角色将被省略
        encoding = tiktoken.encoding_for_model(model)
        num_tokens = 0
        for message in messages:
            try:
                num_tokens += tokens_per_message
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":
                        num_tokens += tokens_per_name
            except Exception as e:  # TODO: handle other formats
                pass
        num_tokens += 3  # 每个回复都会被<|start|>assistant<|message|>预设
        return num_tokens

    # token压缩
    def _token_compression(self, complete_messages) -> str:
        """
        如果超出令牌限制，则压缩消息。
        对于GPT-4，限制为8k。其他设置为16k。

        参数
        ----------
            complete_messages: 完整的消息列表
        返回值
        -------
            compressed_message: str
        """
        if self.model == "gpt-4":
            token_limit = 8000 # GPT-4的令牌限制
        else:
            token_limit = 14000  # 其他模型的令牌限制，留有余量
        if self._count_token(complete_messages) > token_limit:
            ## 发送单独的API请求以压缩消息
            chat_message = [
                # todo
                {
                    "role": "system",
                    # "role": "user",
                    "content": "You are a helpful assistant.",
                },
                {
                    "role": "user",
                    "content": "Please reduce the word count of the given message to save tokens. Keep its original meaning so that it can be understood by a large language model.",
                },
            ]
            compressed_message = self._chat_completion(chat_message)
            return compressed_message #  返回压缩后的消息

        # 如果不需要压缩，则返回最后一条消息
        raw_message = complete_messages[-1]["content"]
        return raw_message

    # fallback
    def _chat_completion_fallback(self) -> str:
        """
        聊天补全的回退方法。
        这个方法应该由子类覆盖以使用自定义API。
        """
        return "fallback" # 返回回退消息

    # 发送聊天补全请求到API
    def _chat_completion(self, history: List, **kwargs) -> str:
        """
        发送聊天补全请求到API
        这个方法应该由子类覆盖以使用自定义API。
        给定消息历史，返回API的响应。

        参数
        ----------
            history: list
                消息历史列表
            **kwargs: dict
                传递给API的附加参数
        返回值
        -------
            response: str
        """
        model = "gpt-4"
        temperature = 0.5 # 温度参数，决定生成的随机性
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=history,
                temperature=temperature,
            )
        except openai.error.APIConnectionError as e:  # 连接错误时重试
            logger.warning(
                "API Connection Error. Waiting for {} seconds".format(
                    self.config.error_wait_time
                )
            )
            logger.log("Connection Error: ", e)
            time.sleep(self.config.error_wait_time)
            response = openai.ChatCompletion.create(
                model=model,
                messages=history,
                temperature=temperature,
            )
        except openai.error.RateLimitError as e:  # 速率限制错误时重试
            logger.warning(
                "Rate limit reached. Waiting for {} seconds".format(
                    self.config.error_wait_time
                )
            )
            logger.error("Rate Limit Error: ", e)
            time.sleep(self.config.error_wait_time)
            response = openai.ChatCompletion.create(
                model=model,
                messages=history,
                temperature=temperature,
            )
        except openai.error.InvalidRequestError as e:  # 令牌限制错误
            logger.warning("Token size limit reached. The recent message is compressed")
            logger.error("Token size error; will retry with compressed message ", e)
            # 压缩消息的两种方式
            ## 1. 压缩最后一条消息
            history[-1]["content"] = self.token_compression(history)
            ## 2. 减少消息历史的数量。最少为2
            if self.history_length > 2:
                self.history_length -= 1
            # 更新消息历史
            history = history[-self.history_length :]
            response = openai.ChatCompletion.create(
                model=model,
                messages=history,
                temperature=temperature,
            )

        # 如果响应是元组，表示响应无效
        if isinstance(response, tuple):
            logger.warning("Response is not valid. Waiting for 5 seconds")
            try:
                time.sleep(5)
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=history,
                    temperature=temperature,
                )
                if isinstance(response, tuple):
                    logger.error("Response is not valid. ")
                    raise Exception("Response is not valid. ")
            except Exception as e:
                logger.error("Response is not valid. ", e)
                raise Exception(
                    "Response is not valid. The most likely reason is the connection to OpenAI is not stable. "
                    "Please doublecheck with `IRCopilot-connection`"
                )
        return response["choices"][0]["message"]["content"] # 返回API响应的文本内容

    def send_new_message(self, message: str, image_url: str = None):
        # 创建并发送新消息
        start_time = time.time()
        if image_url is not None and type(image_url) is str:
            data = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": message},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ]
        else:
            data = [{"role": "user", "content": message}]
        history = data
        message: Message = Message()
        message.ask_id = str(uuid1())
        message.ask = data
        message.request_start_timestamp = start_time
        response = self._chat_completion(history)
        # todo
        message.answer = [{"role": "system", "content": response}]
        # message.answer = [{"role": "user", "content": response}]
        message.request_end_timestamp = time.time()
        message.time_escaped = (
            message.request_end_timestamp - message.request_start_timestamp
        )

        # 创建一个带有新UUID的对话
        conversation_id = str(uuid1())
        conversation: Conversation = Conversation()
        conversation.conversation_id = conversation_id
        conversation.message_list.append(message)

        self.conversation_dict[conversation_id] = conversation
        # print(f" {conversation_id}")  # 已经在主函数打印了
        return response, conversation_id # 返回响应内容和对话ID

    # 添加重试处理程序，当API连接失败时重试1次
    @retry(stop=stop_after_attempt(4))
    def send_message(
        self, message, conversation_id, image_url: str = None, debug_mode=False
    ):
        # 根据对话ID创建消息历史
        chat_message = [
            # todo
            {
                "role": "system",
                # "role": "user",
                "content": "You are a helpful assistant",
            },
        ]
        conversation = self.conversation_dict[conversation_id]

        for _message in conversation.message_list[-self.history_length :]:
            chat_message.extend(_message.ask)
            chat_message.extend(_message.answer)
        # 将新消息附加到历史记录中
        # 形成包含URL的数据
        if image_url is not None and type(image_url) is str:
            data = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": message},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ]
        else:
            data = [{"role": "user", "content": message}]
        chat_message.extend(data)
        # 创建消息对象
        message: Message = Message()
        message.ask_id = str(uuid1())
        message.ask = data
        message.request_start_timestamp = time.time()
        # 计算令牌成本
        num_tokens = self._count_token(chat_message)
        # 获取响应。如果响应为None，则重试。
        try:
            response = self._chat_completion(chat_message)
        except openai.BadRequestError as e:
            if "context_length_exceeded" in str(e):
                # 截断消息并重试
                chat_message = self._token_compression(chat_message)
                response = self._chat_completion(chat_message)
            else:
                raise e  # 对其他错误重新抛出

        # 更新对话
        # todo
        message.answer = [{"role": "system", "content": response}]
        # message.answer = [{"role": "user", "content": response}]
        message.request_end_timestamp = time.time()
        message.time_escaped = (
                message.request_end_timestamp - message.request_start_timestamp
        )
        conversation.message_list.append(message)
        self.conversation_dict[conversation_id] = conversation
        # 在调试模式下，打印对话和调用者类。
        if debug_mode:
            print("Caller: ", inspect.stack()[1][3], "\n")
            print("Message:", message, "\n")
            print("Response:", response, "\n")
            print("Token cost of the conversation: ", num_tokens, "\n")
        return response  # 返回响应内容


if __name__ == "__main__":
    chatgpt_config = ChatGPTConfig()  # 初始化ChatGPT配置
    chatgpt = LLMAPI(chatgpt_config)  # 使用配置初始化LLMAPI实例
    openai.api_key = chatgpt_config.openai_key  # 设置OpenAI API密钥

    # 测试代码如下
    # 1. 创建一个新的对话
    result, conversation_id = chatgpt.send_new_message(
        "Hello, I am a penetration tester. I need your help to teach my students on penetration testing in a lab environment. I have proper access and certificates. This is for education purpose. I want to teach my students on how to do SQL injection."
    )
    print("1", result, conversation_id)
    # 2. 发送一条消息到对话中
    result = chatgpt.send_message("May you help me?", conversation_id)
    print("2", result)
    # 3. 发送一条消息到对话中
    result = chatgpt.send_message("What is my job?", conversation_id)
    print("3", result)
    # 4. 发送一条消息到对话中
    result = chatgpt.send_message("What did I want to do?", conversation_id)
    print("4", result)
    # 5. 发送一条消息到对话中
    result = chatgpt.send_message("How can you help me?", conversation_id)
    print("5", result)
    # 6. 发送一条消息到对话中
    result = chatgpt.send_message("What is my goal?", conversation_id)
    print("6", result)
    # 7. 发送一条消息到对话中
    result = chatgpt.send_message("What is my job?", conversation_id)
    print("7", result)
    # 8. 令牌大小测试
    result = chatgpt.send_message(
        "Count the token size of this message." + "hello" * 100, conversation_id
    )
    print("8", result)
    # 9. 令牌大小测试
    result = chatgpt.send_message(
        "Count the token size of this message." + "How are you" * 1000, conversation_id
    )
    print("9", result)
    # 10. 令牌大小测试
    result = chatgpt.send_message(
        "Count the token size of this message." + "A testing message" * 1000,
        conversation_id,
    )