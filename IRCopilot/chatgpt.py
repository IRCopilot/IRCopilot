# -*- coding: utf-8 -*-
# 用于与ChatGPT进行交互的模块。它提供了多个类和函数来发送消息、管理对话、处理响应和提取代码片段
import dataclasses
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid1

import loguru
import openai
import requests

from IRCopilot.config.chat_config import ChatGPTConfig

# 初始化日志记录器
logger = loguru.logger
logger.remove()

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
    """定义完整对话会话的数据结构"""
    title: Optional[str] = None
    conversation_id: Optional[str] = None
    message_list: List[Message] = dataclasses.field(default_factory=list)

    def __hash__(self):
        return hash(self.conversation_id)

    def __eq__(self, other):
        if not isinstance(other, Conversation):
            return False
        return self.conversation_id == other.conversation_id


def chatgpt_completion(history: List[Dict[str, str]]) -> str:
    """
    使用 OpenAI 官方 SDK (v1.x) 生成回复。
    """
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=history,
    )
    # 注意：需确保 openai SDK 版本兼容 v1.x 语法
    return response.choices[0].message.content


class ChatGPTAPI:
    """
    OpenAI 官方 API 的简易封装类。
    """
    def __init__(self, config: ChatGPTConfig):
        self.config = config
        # 修正：原代码此处使用了未定义的全局 chatgpt_config，改为使用传入的 config
        openai.api_key = config.openai_key
        openai.proxy = config.proxies

    def send_message(self, message: str) -> str:
        """构建单轮对话历史并发送"""
        history = [{"role": "user", "content": message}]
        return chatgpt_completion(history)

    def extract_code_fragments(self, text: str) -> List[str]:
        """提取 Markdown 代码块内容"""
        return re.findall(r"```(.*?)```", text, re.DOTALL)


class ChatGPT:
    """
    ChatGPT 网页版 (Backend API) 的逆向交互类。
    通过模拟浏览器请求与 ChatGPT 后端交互。
    """
    def __init__(self, config: ChatGPTConfig):
        self.config = config
        self.model = config.model
        self.proxies = config.proxies
        self.log_dir = config.log_dir

        # 配置日志文件路径
        log_path = os.path.join(self.log_dir, "chatgpt.log")
        logger.add(sink=log_path, level="ERROR")
        # self._puid = config._puid
        # self.cf_clearance = config.cf_clearance
        # self.session_token = config.session_token
        # conversation_id: message_id

        # 检查必要的 Cookie 配置
        if not getattr(self.config, "cookie", None):
            raise ValueError("Config Error: 'cookie' is missing in config/chat_config.py")

        self.conversation_dict: Dict[str, Conversation] = {}

        # 初始化请求头
        self.headers = {
            "Accept": "*/*",
            "Cookie": self.config.cookie,
            "User-Agent": getattr(self.config, "userAgent", "Mozilla/5.0"),  # 增加默认值防止报错
        }

        # 获取初始 Authorization
        auth = self.get_authorization()
        if auth:
            self.headers["authorization"] = auth

    def refresh(self) -> str:
        """刷新并更新使用中的 cookie 和 authorization"""
        try:
            curl_str = Path(self.config.curl_file).read_text(encoding='utf-8')
            cookie_line = re.search(r"cookie: (.*?)\n", curl_str).group(1)
            valid_cookie = cookie_line.split(" ")[2:]
            self.headers["Cookie"] = " ".join(valid_cookie)
            self.headers["authorization"] = self.get_authorization()
            return self.headers.get("Cookie", "")
        except Exception as e:
            logger.error(f"Refresh failed: {e}")
            return ""

    def get_authorization(self) -> Optional[str]:
        """调用 session 接口获取 accessToken"""
        url = "https://chat.openai.com/api/auth/session"
        try:
            r = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=10)
            r.raise_for_status()
            authorization = r.json().get("accessToken")
            # authorization = self.config.accessToken
            if authorization:
                return f"Bearer {authorization}"
        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            logger.error(f"Authorization error: {e}")
            logger.warning("Cookie implies expiration. Please update.")
        return None

    def get_latest_message_id(self, conversation_id: str) -> Optional[str]:
        """获取指定会话的当前节点 ID (current_node)"""
        url = f"https://chat.openai.com/backend-api/conversation/{conversation_id}"
        try:
            r = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=10)
            r.raise_for_status()
            return r.json().get("current_node")
        except Exception as e:
            logger.error(f"Failed to get latest message ID: {e}")
            return None

    def _parse_message_raw_output(self, response: requests.Response) -> Dict[str, Any]:
        """
        解析流式响应 (SSE)。
        ChatGPT 返回的数据流以 'data: ' 开头，以 '[DONE]' 结束。
        """
        last_line = None
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                # 原逻辑：长度为12时中断 (通常是 'data: [DONE]')
                if len(decoded_line) == 12:
                    break
                if "data:" in decoded_line:
                    last_line = decoded_line

        if last_line:
            # 去除 'data: ' 前缀 (5个字符) 并解析 JSON
            return json.loads(last_line[5:])
        return {}

    def _build_payload(self, message: str, parent_id: str, conversation_id: Optional[str] = None,
                       model: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        [Helper] 构建统一的请求载荷
        Returns: (new_message_id, payload_dict)
        """
        new_message_id = str(uuid1())
        payload = {
            "action": "next",
            "messages": [
                {
                    "id": new_message_id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [message]},
                }
            ],
            "parent_message_id": parent_id,
            "model": model or self.model,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        return new_message_id, payload

    def _post_stream_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        [Helper] 发送流式请求并处理基础响应
        """
        url = "https://chat.openai.com/backend-api/conversation"
        try:
            r = requests.post(url, headers=self.headers, json=payload, proxies=self.proxies, stream=True)
            if r.status_code != 200:
                logger.error(f"ChatGPT API Error ({r.status_code}): {r.text}")
                return None
            return self._parse_message_raw_output(r)
        except Exception as e:
            logger.error(f"Request Exception: {e}")
            return None

    def send_new_message(self, message: str, model: Optional[str] = None, gen_title: bool = False) -> Tuple[
        Optional[str], Optional[str]]:
        """
        发送新消息（初始化新会话）。
        """
        logger.info("Function: send_new_message")

        # 1. 准备数据 (新会话 parent_id 为随机 UUID)
        parent_id = str(uuid1())
        msg_id, payload = self._build_payload(message, parent_id, model=model)

        start_time = time.time()

        # 2. 发送请求
        result = self._post_stream_request(payload)
        if not result:
            return None, None

        # 3. 解析结果
        text = "\n".join(result["message"]["content"]["parts"])
        conversation_id = result["conversation_id"]
        answer_id = result["message"]["id"]

        # 4. 记录数据
        end_time = time.time()
        msg_obj = Message(
            ask_id=msg_id,
            ask=payload,
            answer=result,
            answer_id=answer_id,
            request_start_timestamp=start_time,
            request_end_timestamp=end_time,
            time_escaped=end_time - start_time
        )

        conversation = Conversation(
            conversation_id=conversation_id,
            message_list=[msg_obj]
        )
        if gen_title:
            conversation.title = self.gen_conversation_title(conversation_id, answer_id)

        self.conversation_dict[conversation_id] = conversation

        return text, conversation_id

    def send_message(self, message: str, conversation_id: str) -> Optional[str]:
        """
        在现有会话中继续发送消息。
        """
        logger.info("Function: send_message")

        # 1. 获取上下文 (parent_id)
        if conversation_id not in self.conversation_dict:
            logger.info(f"Conversation {conversation_id} not in memory, fetching remote head.")
            parent_id = self.get_latest_message_id(conversation_id)
        else:
            parent_id = self.conversation_dict[conversation_id].message_list[-1].answer_id

        if not parent_id:
            logger.error("Failed to determine parent message ID.")
            return None

        # 2. 准备数据
        msg_id, payload = self._build_payload(message, parent_id, conversation_id=conversation_id)

        start_time = time.time()

        # 3. 发送请求
        result = self._post_stream_request(payload)
        if not result:
            return None

        # 4. 解析结果
        text = "\n".join(result["message"]["content"]["parts"])

        # 5. 记录数据
        end_time = time.time()
        msg_obj = Message(
            ask_id=msg_id,
            ask=payload,
            answer=result,
            answer_id=result["message"]["id"],
            request_start_timestamp=start_time,
            request_end_timestamp=end_time,
            time_escaped=end_time - start_time
        )

        # 确保本地缓存存在
        if conversation_id not in self.conversation_dict:
            self.conversation_dict[conversation_id] = Conversation(conversation_id=conversation_id)

        self.conversation_dict[conversation_id].message_list.append(msg_obj)

        return text

    def get_conversation_history(self, limit: int = 20, offset: int = 0) -> Optional[Dict[str, str]]:
        """获取历史会话列表 {id: title}"""
        url = "https://chat.openai.com/backend-api/conversations"
        params = {"limit": limit, "offset": offset}
        try:
            r = requests.get(url, headers=self.headers, params=params, proxies=self.proxies)
            if r.status_code == 200:
                data = r.json()
                return {item["id"]: item["title"] for item in data.get("items", [])}
            logger.error(f"Failed to retrieve history: {r.status_code}")
        except Exception as e:
            logger.error(f"Error getting history: {e}")
        return None

    def get_cached_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """从本地缓存获取会话对象"""
        return self.conversation_dict.get(conversation_id)

    def gen_conversation_title(self, conversation_id: str, rsp_message_id: str) -> Optional[str]:
        """请求 ChatGPT 为会话生成标题"""
        if not conversation_id:
            return None

        url = f"https://chat.openai.com/backend-api/conversation/gen_title/{conversation_id}"
        data = {"message_id": rsp_message_id}

        try:
            r = requests.post(url, headers=self.headers, json=data, proxies=self.proxies)
            if r.status_code == 200:
                title = r.json().get("title")
                logger.info(f"Updated conversation {conversation_id} title to: {title}")
                return title
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
        return None

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除（隐藏）指定会话"""
        if not conversation_id:
            return False

        url = f"https://chat.openai.com/backend-api/conversation/{conversation_id}"
        data = {"is_visible": False}

        try:
            r = requests.patch(url, headers=self.headers, json=data, proxies=self.proxies)

            # 无论远端是否成功，都在本地移除以保持一致性
            if conversation_id in self.conversation_dict:
                del self.conversation_dict[conversation_id]

            if r.status_code == 200:
                return True
            logger.error(f"Failed to delete conversation remotely: {r.status_code}")
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
        return False

    def extract_code_fragments(self, text: str) -> List[str]:
        """从响应文本中提取代码块"""
        return re.findall(r"```(.*?)```", text, re.DOTALL)


if __name__ == "__main__":
    try:
        config = ChatGPTConfig()
        chatgpt = ChatGPT(config)

        # 1. 测试发送新消息
        print("Sending new message...")
        resp_text, conv_id = chatgpt.send_new_message("I am a new tester for RESTful APIs.")
        if conv_id:
            print(f"Response: {resp_text}\nConversation ID: {conv_id}")

            # 2. 测试现有会话消息
            print("\nSending follow-up message...")
            payload_msg = (
                "generate: {'post': {'tags': ['pet'], 'summary': 'uploads an image', ...}}"
                # (省略长字符串以保持整洁)
            )
            result = chatgpt.send_message(payload_msg, conv_id)

            # 3. 提取代码块测试
            if result:
                fragments = chatgpt.extract_code_fragments(result)
                logger.info(f"Extracted {len(fragments)} code fragments.")
        else:
            print("Failed to start conversation.")

    except Exception as e:
        logger.error(f"Main execution failed: {e}")
