# 实现了一个与OpenAI ChatGPT API交互的类LLMAPI，支持创建和管理对话，以及在对话中发送消息
# -*- coding: utf-8 -*-
import dataclasses
import inspect
import os
import time
from typing import Any, Dict, List, Optional, Union, Tuple
from uuid import uuid1

import loguru
import openai
import tiktoken
from tenacity import retry, stop_after_attempt

from IRCopilot.config.chat_config import ChatGPTConfig

# 配置日志
logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/chatgpt.log")


@dataclasses.dataclass
class Message:
    """存储单次问答的消息结构"""
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


class LLMAPI:
    """
    OpenAI ChatGPT API 交互类

    负责管理对话上下文、Token 计数、消息压缩以及 API 请求发送（含重试机制）。
    """

    def __init__(self, config: ChatGPTConfig):
        self.name = "LLMAPI_base_class"
        self.config = config

        # OpenAI 配置初始化
        openai.api_key = config.openai_key
        openai.proxy = config.proxies
        openai.api_base = config.api_base

        self.log_dir = config.log_dir
        self.history_length = 5  # 保留最近 5 轮对话记忆
        self.conversation_dict: Dict[str, Conversation] = {}

        # 显式定义模型，防止 _token_compression 调用时出错
        self.model = "gpt-4"

        # 添加文件日志
        log_path = os.path.join(self.log_dir, "chatgpt.log")
        logger.add(sink=log_path, level="WARNING")

    def _count_token(self, messages: List[Dict[str, Any]]) -> int:
        """
        计算消息列表消耗的 Token 数量。

        参考: openai-cookbook/examples/How_to_count_tokens_with_tiktoken.ipynb
        """
        model = "gpt-3.5-turbo-0301"  # 用于估算的基准模型
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens_per_message = 4  # <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # 如果有 name 字段，role 会被省略

        num_tokens = 0
        for message in messages:
            try:
                num_tokens += tokens_per_message
                for key, value in message.items():
                    # 仅计算字符串类型的值
                    if isinstance(value, str):
                        num_tokens += len(encoding.encode(value))
                    elif isinstance(value, list):
                        # 处理多模态内容（如包含图片的 content 列表）
                        for item in value:
                            if isinstance(item, dict) and "text" in item:
                                num_tokens += len(encoding.encode(item["text"]))

                    if key == "name":
                        num_tokens += tokens_per_name
            except Exception:
                # 忽略无法处理的格式，避免计数崩溃
                pass

        num_tokens += 3  # <|start|>assistant<|message|>
        return num_tokens


    def _token_compression(self, complete_messages: List[Dict[str, Any]]) -> str:
        """
        当超出 Token 限制时，尝试压缩消息。

        策略：
        1. 检查当前 Token 是否超限 (GPT-4 8k / 其他 14k)。
        2. 如果超限，调用 API 请求 AI 对内容进行摘要/缩减。
        3. 如果未超限，直接返回最后一条消息内容。
        """
        token_limit = 8000 if self.model == "gpt-4" else 14000

        if self._count_token(complete_messages) > token_limit:
            compression_prompt = [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "Please reduce the word count of the given message to save tokens. "
                               "Keep its original meaning so that it can be understood by a large language model."
                },
            ]
            # 递归调用 API 进行压缩
            compressed_message = self._chat_completion(compression_prompt)
            return compressed_message

        # 若无需压缩，返回最后一条消息的文本内容
        last_content = complete_messages[-1]["content"]
        # 处理可能的列表格式（多模态）
        if isinstance(last_content, list):
            for item in last_content:
                if item.get("type") == "text":
                    return item.get("text")
        return last_content

    def _chat_completion(self, history: List[Dict[str, Any]], **kwargs) -> str:
        """
        核心方法：发送请求到 OpenAI API。
        包含手动实现的重试逻辑（针对连接错误、速率限制、Token 超限）。
        """
        temperature = 0.5

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=history,
                temperature=temperature,
                **kwargs
            )
        except openai.error.APIConnectionError as e:
            logger.warning(f"API Connection Error. Waiting {self.config.error_wait_time}s. Error: {e}")
            time.sleep(self.config.error_wait_time)
            # Retry once
            response = openai.ChatCompletion.create(
                model=self.model, messages=history, temperature=temperature, **kwargs
            )

        except openai.error.RateLimitError as e:
            logger.warning(f"Rate limit reached. Waiting {self.config.error_wait_time}s. Error: {e}")
            time.sleep(self.config.error_wait_time)
            # Retry once
            response = openai.ChatCompletion.create(
                model=self.model, messages=history, temperature=temperature, **kwargs
            )

        except openai.error.InvalidRequestError as e:
            # 处理 Token 超限错误
            logger.warning("Token size limit reached. Compressing recent message...")
            logger.error(f"Token error details: {e}")

            # 策略1: 压缩最后一条消息
            # 注意：此处直接修改 history 可能会影响引用，但为了逻辑一致性保持原样
            # 需要先将 content 转换为 string 才能赋值回去（如果之前是 list）
            history[-1]["content"] = self._token_compression(history)

            # 策略2: 缩减历史记录长度
            if self.history_length > 2:
                self.history_length -= 1

            # 截取最新的 N 条
            history = history[-self.history_length:]

            response = openai.ChatCompletion.create(
                model=self.model, messages=history, temperature=temperature, **kwargs
            )

        # 检查非法响应 (针对某些代理或旧版接口可能返回 tuple 的情况)
        if isinstance(response, tuple):
            logger.warning("Received invalid tuple response. Retrying in 5s...")
            time.sleep(5)
            response = openai.ChatCompletion.create(
                model=self.model, messages=history, temperature=temperature, **kwargs
            )
            if isinstance(response, tuple):
                raise Exception("Response is strictly invalid (tuple received). Check OpenAI connection stability.")

        return response["choices"][0]["message"]["content"]

    def _build_user_message(self, message: str, image_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """辅助方法：根据是否有图片构建用户消息体"""
        if image_url and isinstance(image_url, str):
            return [{
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }]
        return [{"role": "user", "content": message}]

    def send_new_message(self, message: str, image_url: str = None) -> Tuple[str, str]:
        """
        开启一个全新的对话会话。

        Returns:
            (response_text, conversation_id)
        """
        start_time = time.time()

        # 构建消息
        data = self._build_user_message(message, image_url)

        # 执行请求
        response_text = self._chat_completion(data)

        # 记录数据
        msg_obj = Message(
            ask_id=str(uuid1()),
            ask=data,
            answer=[{"role": "assistant", "content": response_text}],  # 修正 role 为 assistant
            request_start_timestamp=start_time,
            request_end_timestamp=time.time()
        )
        msg_obj.time_escaped = msg_obj.request_end_timestamp - msg_obj.request_start_timestamp

        # 创建新会话
        conversation_id = str(uuid1())
        conversation = Conversation(
            conversation_id=conversation_id,
            message_list=[msg_obj]
        )
        self.conversation_dict[conversation_id] = conversation

        return response_text, conversation_id

    @retry(stop=stop_after_attempt(4))
    def send_message(self, message: str, conversation_id: str, image_url: str = None, debug_mode: bool = False) -> str:
        """
        在现有对话中发送消息（包含上下文历史）。
        使用 tenacity 进行外部重试。
        """
        conversation = self.conversation_dict[conversation_id]

        # 1. 构建系统提示和历史上下文
        chat_history = [{"role": "system", "content": "You are a helpful assistant"}]

        # 获取最近 N 条历史
        for prev_msg in conversation.message_list[-self.history_length:]:
            if prev_msg.ask:
                chat_history.extend(prev_msg.ask)
            if prev_msg.answer:
                # 注意：OpenAI 历史记录中回答的角色应为 assistant
                # 这里为了保持逻辑不便改为 assistant，但请注意标准是 assistant
                chat_history.extend(prev_msg.answer)

        # 2. 添加当前新消息
        current_data = self._build_user_message(message, image_url)
        chat_history.extend(current_data)

        # 3. 准备记录对象
        start_time = time.time()
        msg_obj = Message(
            ask_id=str(uuid1()),
            ask=current_data,
            request_start_timestamp=start_time
        )

        # Debug 信息
        num_tokens = self._count_token(chat_history)

        # 4. 发送请求
        try:
            response_text = self._chat_completion(chat_history)
        except getattr(openai, "BadRequestError", Exception) as e:
            # 兼容处理：如果安装了新版 SDK 可能会抛出 BadRequestError
            if "context_length_exceeded" in str(e):
                chat_history = self._token_compression(chat_history)
                response_text = self._chat_completion(chat_history)
            else:
                raise e

        # 5. 更新会话记录
        msg_obj.answer = [{"role": "assistant", "content": response_text}]
        msg_obj.request_end_timestamp = time.time()
        msg_obj.time_escaped = msg_obj.request_end_timestamp - msg_obj.request_start_timestamp

        conversation.message_list.append(msg_obj)
        self.conversation_dict[conversation_id] = conversation

        if debug_mode:
            print(f"Caller: {inspect.stack()[1][3]}")
            print(f"Message ID: {msg_obj.ask_id}")
            print(f"Token cost: {num_tokens}")

        return response_text


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