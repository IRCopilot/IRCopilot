import dataclasses
import inspect
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid1

import google.generativeai as genai
from google.generativeai.types import (
    HarmBlockThreshold,
    HarmCategory,
)
import loguru
from tenacity import retry, stop_after_attempt, wait_fixed

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()


@dataclasses.dataclass
class Message:
    """定义单条消息的数据结构"""
    ask_id: Optional[str] = None
    ask: Optional[Any] = None                   # 请求内容
    answer: Optional[Any] = None                # 回答内容
    answer_id: Optional[str] = None
    request_start_timestamp: float = 0.0        # 请求开始时间戳
    request_end_timestamp: float = 0.0          # 请求结束时间戳
    time_escaped: float = 0.0                   # 请求耗时


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


class GeminiAPI(LLMAPI):
    """
    基于 Google Generative AI SDK 的 Gemini 接口封装类。
    """

    def __init__(self, config_class, use_langfuse_logging=False):
        self.name = str(config_class.model)
        
        # 配置 Google API Key
        # 优先读取 Config，其次读取环境变量
        api_key = os.getenv("GOOGLE_API_KEY") 
        if not api_key and hasattr(config_class, "gemini_key"):
             api_key = config_class.gemini_key
        
        if api_key:
            genai.configure(api_key=api_key)
        else:
            logger.warning("GOOGLE_API_KEY is not set.")

        self.model_name = config_class.model or "gemini-1.5-pro-latest"
        self.model = genai.GenerativeModel(self.model_name)
        
        self.log_dir = config_class.log_dir
        self.history_length = 5
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = 3

        # 安全设置：默认放宽限制以避免误拦截
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        }

        # Langfuse 集成
        self.langfuse = None
        if use_langfuse_logging:
            try:
                from langfuse import Langfuse
                self.langfuse = Langfuse()
            except ImportError:
                logger.warning("Langfuse not installed, skipping logging.")

        self.initialize_logger(self.log_dir)

    def initialize_logger(self, log_dir: str):
        """初始化日志"""
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        # logger.add(sink=os.path.join(log_dir, "gemini.log"), level="WARNING")

    def _chat_completion(
        self, 
        history: List[Dict[str, Any]], 
        current_message: str, 
        temperature: float = 0.5
    ) -> str:
        """
        核心方法：调用 Gemini API。
        """
        generation_start_time = datetime.now()
        
        try:
            # 启动聊天会话 (history 格式为 [{'role': 'user'|'model', 'parts': [...]}, ...])
            chat_session = self.model.start_chat(history=history)
            
            # 发送消息
            response = chat_session.send_message(
                current_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature
                ),
                safety_settings=self.safety_settings,
            )
            
            response_text = response.text

            # Langfuse Logging
            if self.langfuse:
                self._log_to_langfuse(
                    history, current_message, response, temperature, generation_start_time
                )
            
            return response_text

        except Exception as e:
            logger.error(f"Error in Gemini chat completion: {e}")
            raise e

    def _log_to_langfuse(self, history, current_msg, response, temperature, start_time):
        """Langfuse 日志记录辅助方法"""
        try:
            from langfuse.model import InitialGeneration, Usage
            
            # Gemini 的 usage 通常在 usage_metadata 中
            usage = Usage(promptTokens=0, completionTokens=0)
            if hasattr(response, "usage_metadata"):
                usage = Usage(
                    promptTokens=response.usage_metadata.prompt_token_count,
                    completionTokens=response.usage_metadata.candidates_token_count,
                )

            self.langfuse.generation(
                InitialGeneration(
                    name="gemini-completion",
                    startTime=start_time,
                    endTime=datetime.now(),
                    model=self.model_name,
                    modelParameters={"temperature": str(temperature)},
                    prompt=[*history, {"role": "user", "parts": [current_msg]}],
                    completion=response.text,
                    usage=usage,
                )
            )
        except Exception as e:
            logger.warning(f"Langfuse logging failed: {e}")

    def _construct_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """构建 Gemini 格式的历史记录"""
        history = []
        # 可选：添加 System Prompt 或 Persona (Gemini SDK 1.5+ 支持 system_instruction 参数在 Model 初始化时，此处使用 history hack)
        # history = [
        #     {"role": "user", "parts": ["You are a helpful assistant."]},
        #     {"role": "model", "parts": ["Understood. I am a helpful assistant."]}
        # ]
        
        if conversation_id in self.conversation_dict:
            conversation = self.conversation_dict[conversation_id]
            # 获取最近 N 条记录
            recent_messages = conversation.message_list[-self.history_length:]
            
            for msg in recent_messages:
                if msg.ask:
                    history.append({"role": "user", "parts": [str(msg.ask)]})
                if msg.answer:
                    history.append({"role": "model", "parts": [str(msg.answer)]})
        
        return history

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def send_new_message(self, message: str) -> Tuple[str, str]:
        """开启新对话"""
        start_time = time.time()
        
        # 1. 发送请求 (新对话 history 为空)
        response_text = self._chat_completion([], message)
        
        # 2. 记录数据
        conversation_id = str(uuid1())
        msg_obj = Message(
            ask_id=str(uuid1()),
            ask=message,
            answer=response_text,
            request_start_timestamp=start_time,
            request_end_timestamp=time.time()
        )
        msg_obj.time_escaped = msg_obj.request_end_timestamp - start_time
        
        # 3. 保存会话
        conversation = Conversation(
            conversation_id=conversation_id,
            message_list=[msg_obj]
        )
        self.conversation_dict[conversation_id] = conversation
        
        logger.info(f"New conversation created: {conversation_id}")
        return response_text, conversation_id

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def send_message(self, message: str, conversation_id: str, debug_mode: bool = False) -> str:
        """在现有对话中发送消息"""
        start_time = time.time()
        
        # 1. 构建历史记录
        history = self._construct_history(conversation_id)
        
        # 2. 发送请求
        response_text = self._chat_completion(history, message)
        
        # 3. 记录数据
        msg_obj = Message(
            ask_id=str(uuid1()),
            ask=message,
            answer=response_text,
            request_start_timestamp=start_time,
            request_end_timestamp=time.time()
        )
        msg_obj.time_escaped = msg_obj.request_end_timestamp - start_time
        
        # 4. 更新会话
        if conversation_id not in self.conversation_dict:
             self.conversation_dict[conversation_id] = Conversation(conversation_id=conversation_id)
        
        self.conversation_dict[conversation_id].message_list.append(msg_obj)
        
        if debug_mode:
            print(f"Caller: {inspect.stack()[1][3]}")
            print(f"Message: {message}")
            print(f"Response: {response_text}")

        return response_text


if __name__ == "__main__":
    # 模拟 Config
    class MockGeminiConfig:
        model = "gemini-1.5-flash"
        log_dir = "logs"
        # gemini_key = "YOUR_API_KEY" # 或者使用环境变量 GOOGLE_API_KEY

    print("--- Test Start ---")
    try:
        config = MockGeminiConfig()
        gemini = GeminiAPI(config)

        # 1. 新对话
        print("Sending new message...")
        res, conv_id = gemini.send_new_message("Hello, explain Quantum Computing in 1 sentence.")
        print(f"Response: {res}")
        print(f"Conv ID: {conv_id}")

        # 2. 后续对话
        print("\nSending follow-up...")
        res = gemini.send_message("Who invented it?", conv_id, debug_mode=True)
        print(f"Response: {res}")

    except Exception as e:
        print(f"Test failed (Expected if API Key is missing): {e}")