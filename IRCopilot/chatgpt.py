# -*- coding: utf-8 -*-
# 用于与ChatGPT进行交互的模块。它提供了多个类和函数来发送消息、管理对话、处理响应和提取代码片段

import dataclasses
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid1

import loguru
import openai
import requests

from IRCopilot.config.chat_config import ChatGPTConfig

# 初始化日志记录器
logger = loguru.logger
logger.remove()
# logger.add(level="ERROR", sink="logs/chatgpt.log")


# 一个示例的 ChatGPTConfig 类结构。所有字段都可以从浏览器的cookie中获取。
# 特别是 cf_clearance、__Secure-next-auth.session-token、_puid 是必须的。
# 更新：当前登录不可用，解决方案是粘贴完整的cookie。

# @dataclasses.dataclass
# class ChatGPTConfig:
#     model: str = "text-davinci-002-render-sha"
#     _puid: str = ""
#     cf_clearance: str = ""
#     session_token: str = ""
#     error_wait_time: float = 20
#     is_debugging: bool = False


@dataclasses.dataclass
class Message:
    ask_id: str = None  # 消息ID
    ask: dict = None  # 请求数据
    answer: dict = None  # 回应数据
    answer_id: str = None  # 回应消息ID
    request_start_timestamp: float = None  # 请求开始时间戳
    request_end_timestamp: float = None  # 请求结束时间戳
    time_escaped: float = None  # 请求花费的时间


@dataclasses.dataclass
class Conversation:
    title: str = None
    conversation_id: str = None
    message_list: List[Message] = dataclasses.field(default_factory=list)

    def __hash__(self):
        return hash(self.conversation_id)

    def __eq__(self, other):
        if not isinstance(other, Conversation):
            return False
        return self.conversation_id == other.conversation_id


def chatgpt_completion(history: List) -> str:
    # 使用 OpenAI 的 ChatCompletion 创建方法从历史消息生成响应
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=history,
    )
    return response.choices[0].message.content


class ChatGPTAPI:
    def __init__(self, config: ChatGPTConfig):
        self.config = config
        openai.api_key = chatgpt_config.openai_key
        openai.proxy = config.proxies

    def send_message(self, message):
        history = [{"role": "user", "content": message}]
        return chatgpt_completion(history)

    def extract_code_fragments(self, text):
        return re.findall(r"```(.*?)```", text, re.DOTALL)


class ChatGPT:
    def __init__(self, config: ChatGPTConfig):
        self.config = config
        self.model = config.model
        self.proxies = config.proxies
        self.log_dir = config.log_dir

        # 配置日志记录器
        logger.add(sink=os.path.join(self.log_dir, "chatgpt.log"), level="ERROR")
        # self._puid = config._puid
        # self.cf_clearance = config.cf_clearance
        # self.session_token = config.session_token
        # conversation_id: message_id

        # 确保cookie已经配置
        if "cookie" not in vars(self.config):
            raise Exception("Please update cookie in config/chat_config.py")
        self.conversation_dict: Dict[str, Conversation] = {}
        self.headers = {
            "Accept": "*/*",
            "Cookie": self.config.cookie,
            "User-Agent": self.config.userAgent,
        }
        self.headers["authorization"] = self.get_authorization()

    def refresh(self) -> str:
        """
        刷新并更新使用中的cookie和authorization，以保持会话的有效性
        """
        # 定期刷新cookie，避免过期
        curl_str = Path(Path(self.config.curl_file)).read_text()
        # 查找包含"cookie:"的行
        cookie_line = re.findall(r"cookie: (.*?)\n", curl_str)[0]
        valid_cookie = cookie_line.split(" ")[2:]
        # 将它们拼接在一起
        self.headers["Cookie"] = " ".join(valid_cookie)
        self.headers["authorization"] = self.get_authorization()
        return self.headers["Cookie"]

    def get_authorization(self):
        # 获取授权令牌
        try:
            url = "https://chat.openai.com/api/auth/session"
            r = requests.get(url, headers=self.headers, proxies=self.proxies)
            authorization = r.json()["accessToken"]
            # authorization = self.config.accessToken
            return f"Bearer {authorization}"
        except requests.exceptions.JSONDecodeError as e:
            logger.error(e)
            logger.error(
                "You encounter an error when communicating with ChatGPT. The most likely reason is that your cookie expired."
            )
            return None

    def get_latest_message_id(self, conversation_id):
        # 获取对话中的最新消息ID
        try:
            url = f"https://chat.openai.com/backend-api/conversation/{conversation_id}"
            r = requests.get(url, headers=self.headers, proxies=self.proxies)
            return r.json()["current_node"]
        except requests.exceptions.JSONDecodeError as e:
            logger.error(e)
            logger.error(
                "You encounter an error when communicating with ChatGPT. The most likely reason is that your cookie expired."
            )
            return None

    def _parse_message_raw_output(self, response: requests.Response):
        # 解析消息的原始输出
        last_line = None
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if len(decoded_line) == 12:
                    break
                if "data:" in decoded_line:
                    last_line = decoded_line
        return json.loads(last_line[5:])

    def send_new_message(self, message, model=None, gen_title=False):
        """
        发送一个新的消息并可能初始化一个新会话，返回响应的文本和会话ID
        """

        if model is None:
            model = self.model
        logger.info("send_new_message")
        url = "https://chat.openai.com/backend-api/conversation"

        message_id = str(uuid1())  # 生成一个新的消息ID
        # 构造请求数据
        data = {
            "action": "next",
            "messages": [
                {
                    "id": message_id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [message]},
                }
            ],
            "parent_message_id": str(uuid1()),
            "model": model,
        }

        # 记录请求开始的时间
        start_time = time.time()
        # 创建一个消息对象
        message: Message = Message()
        message.ask_id = message_id
        message.ask = data
        message.request_start_timestamp = start_time

        r = requests.post(
            url, headers=self.headers, json=data, proxies=self.proxies, stream=True
        )

        if r.status_code != 200:
            # 如果状态码不是200，等待20秒并记录错误
            logger.error(r.text)
            return None, None

        # 解析响应数据
        result = self._parse_message_raw_output(r)
        text = "\n".join(result["message"]["content"]["parts"])
        rsp_message_id = result["message"]["id"]
        conversation_id = result["conversation_id"]
        answer_id = result["message"]["id"]

        # 记录响应时间和生成的会话信息
        end_time = time.time()
        message.answer_id = answer_id
        message.answer = result
        message.request_end_timestamp = end_time
        message.time_escaped = end_time - start_time
        # 创建或更新会话记录
        conversation: Conversation = Conversation()
        conversation.conversation_id = conversation_id
        conversation.message_list.append(message)

        # 如果生成标题，生成会话标题并将其添加到会话中
        if gen_title:
            title = self.gen_conversation_title(conversation_id, rsp_message_id)
            conversation.title = title

        self.conversation_dict[conversation_id] = conversation

        return text, conversation_id  # 返回文本内容和会话ID

    def send_message(self, message, conversation_id):
        """
        发送消息到现有对话中并返回响应文本
        """
        logger.info("send_message")
        url = "https://chat.openai.com/backend-api/conversation"

        # 从对话ID中获取消息
        if conversation_id not in self.conversation_dict:
            # 如果对话ID不在会话字典中，说明需要获取最新的消息ID
            logger.info(f"conversation_id: {conversation_id}")
            message_id = self.get_latest_message_id(conversation_id)
            logger.info(f"message_id: {message_id}")
        else:
            # 如果对话ID已存在，获取该对话中最后一个消息的回答ID作为父消息ID
            message_id = (
                self.conversation_dict[conversation_id].message_list[-1].answer_id
            )

        new_message_id = str(uuid1())  # 生成一个新的消息ID
        # 构造请求数据
        data = {
            "action": "next",  # 动作类型
            "messages": [
                {
                    "id": new_message_id,  # 新消息ID
                    "role": "user",  # 角色类型
                    "content": {"content_type": "text", "parts": [message]},
                }
            ],
            "conversation_id": conversation_id,  # 对话ID
            "parent_message_id": message_id,  # 父消息ID
            "model": self.model,  # 使用的模型
        }

        # 记录请求开始的时间
        start_time = time.time()
        # 创建一个消息对象
        message: Message = Message()
        message.ask_id = new_message_id
        message.ask = data
        message.request_start_timestamp = start_time

        r = requests.post(
            url, headers=self.headers, json=data, proxies=self.proxies, stream=True
        )
        if r.status_code != 200:
            # 发送消息阻塞时等待20秒从新发送
            logger.warning(f"chatgpt failed: {r.text}")
            return None, None

        # 解析响应数据
        result = self._parse_message_raw_output(r)
        text = "\n".join(result["message"]["content"]["parts"])
        conversation_id = result["conversation_id"]
        answer_id = result["message"]["id"]

        # 记录请求结束的时间
        end_time = time.time()
        message.answer_id = answer_id
        message.answer = result
        message.request_end_timestamp = end_time
        message.time_escaped = end_time - start_time

        # 添加重新加载的附加逻辑
        if conversation_id not in self.conversation_dict:
            conversation: Conversation = Conversation()
            conversation.conversation_id = conversation_id
            self.conversation_dict[conversation_id] = conversation
        conversation: Conversation = self.conversation_dict[conversation_id]
        conversation.message_list.append(message)
        return text

    def get_conversation_history(self, limit=20, offset=0):
        # Get the conversation id in the history
        url = "https://chat.openai.com/backend-api/conversations"
        query_params = {
            "limit": limit, # 查询结果的限制条数
            "offset": offset, # 查询结果的偏移量
        }
        r = requests.get(
            url, headers=self.headers, params=query_params, proxies=self.proxies
        )
        if r.status_code == 200:
            json_data = r.json()
            return {item["id"]: item["title"] for item in json_data["items"]}
        else:
            logger.error("Failed to retrieve history")
            return None

    def get_cached_conversation(self, conversation_id: str) -> Conversation:
        # 从缓存中获取指定的对象
        return self.conversation_dict.get(conversation_id)

    def gen_conversation_title(self, conversation_id: str, rsp_message_id: str):
        # 生成对话标题
        if not conversation_id:
            return
        # 构建生成对话标题的URL
        url = f"https://chat.openai.com/backend-api/conversation/gen_title/{conversation_id}"
        data = {
            "message_id": rsp_message_id,  # 包含响应消息ID的数据
        }
        # 发送POST请求以生成标题
        r = requests.post(url, headers=self.headers, json=data, proxies=self.proxies)

        if r.status_code != 200:
            return None

        # 从响应中提取生成的标题
        title = r.json()["title"]

        # 记录日志，更新对话的标题
        logger.info(f"update conversation {conversation_id} title to {title}")
        return title

    def delete_conversation(self, conversation_id=None):
        # 删除指定UUID的对话
        if not conversation_id:
            return
        # 构建删除对话的URL
        url = f"https://chat.openai.com/backend-api/conversation/{conversation_id}"
        data = {
            "is_visible": False,  # 将对话标记为不可见
        }
        # 发送PATCH请求以更新对话的可见性
        r = requests.patch(url, headers=self.headers, json=data, proxies=self.proxies)

        # 在本地删除对话ID
        if conversation_id in self.conversation_dict:
            del self.conversation_dict[conversation_id]

        if r.status_code == 200:
            return True
        # 如果删除失败，记录错误日志
        logger.error("Failed to delete conversation")
        return False

    def extract_code_fragments(self, text):
        # 提取文本中的代码片段
        return re.findall(r"```(.*?)```", text, re.DOTALL)


if __name__ == "__main__":
    chatgpt_config = ChatGPTConfig() # 初始化 ChatGPT 配置
    chatgpt = ChatGPT(chatgpt_config) # 使用配置初始化 ChatGPT 实例

    # 发送新消息并返回响应文本和会话ID
    text, conversation_id = chatgpt.send_new_message(
        "I am a new tester for RESTful APIs."
    )
    print(text, conversation_id)

    # 在现有对话中发送另一条消息并返回结果
    result = chatgpt.send_message(
        "generate: {'post': {'tags': ['pet'], 'summary': 'uploads an image', 'description': '', 'operationId': 'uploadFile', 'consumes': ['multipart/form-data'], 'produces': ['application/json'], 'parameters': [{'name': 'petId', 'in': 'path', 'description': 'ID of pet to update', 'required': True, 'type': 'integer', 'format': 'int64'}, {'name': 'additionalMetadata', 'in': 'formData', 'description': 'Additional data to pass to server', 'required': False, 'type': 'string'}, {'name': 'file', 'in': 'formData', 'description': 'file to upload', 'required': False, 'type': 'file'}], 'responses': {'200': {'description': 'successful operation', 'schema': {'type': 'object', 'properties': {'code': {'type': 'integer', 'format': 'int32'}, 'type': {'type': 'string'}, 'message': {'type': 'string'}}}}}, 'security': [{'petstore_auth': ['write:pets', 'read:pets']}]}}",
        conversation_id, # 使用先前创建的会话ID
    )
    # 使用日志记录从结果中提取的代码片段
    logger.info(chatgpt.extract_code_fragments(result))
