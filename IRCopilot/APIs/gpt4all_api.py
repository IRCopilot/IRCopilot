import dataclasses
from typing import Any, Dict, List, Optional

import loguru
from gpt4all import GPT4All

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()
# logger.add(level="WARNING", sink="logs/gpt4all.log")


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


class GPT4ALLAPI(LLMAPI):
    """
    基于 GPT4All 本地模型的接口封装类。
    """

    def __init__(self, config_class, use_langfuse_logging=False):
        self.name = str(config_class.model)
        # GPT4All 本地推理资源消耗大，通常限制历史记录长度
        self.history_length = 2  
        self.conversation_dict: Dict[str, Conversation] = {}
        
        # 初始化模型 (这可能会下载模型文件，取决于 GPT4All 的配置)
        # allow_download=False 可以防止意外下载，视具体需求而定
        self.model = GPT4All(config_class.model)
        
        # 初始化日志 (如果 config_class 有 log_dir)
        if hasattr(config_class, "log_dir") and config_class.log_dir:
            import os
            if not os.path.exists(config_class.log_dir):
                os.makedirs(config_class.log_dir, exist_ok=True)
            logger.add(sink=f"{config_class.log_dir}/gpt4all.log", level="WARNING")

    def _chat_completion_fallback(self, history: List[Dict[str, Any]]) -> str:
        """
        回退方法：当主生成逻辑失败时尝试简单的生成。
        """
        try:
            # 修正：确保从字典中提取 content 字符串
            prompt_text = history[-1]["content"] if isinstance(history[-1], dict) else str(history[-1])
            response = self.model.generate(prompt=prompt_text, top_k=self.history_length)
            return response
        except Exception as e:
            logger.error(f"Fallback generation failed: {e}")
            return "Error in generating response."

    def _chat_completion(self, history: List[Dict[str, Any]]) -> str:
        """
        核心生成方法。
        注意：当前实现每次创建新的 chat_session，这意味着它主要响应最后一条消息，
        而非维护长上下文（这符合 history_length=2 的设定）。
        """
        try:
            with self.model.chat_session():
                # 提取用户最后一条输入
                latest_message = history[-1]["content"]
                
                # generate 方法在 chat_session 上下文中会自动应用对话模版
                response = self.model.generate(
                    prompt=latest_message, 
                    top_k=1  # 这里的 top_k 参数在 gpt4all 中通常控制采样多样性
                )
                return response
        except Exception as e:
            logger.error(f"GPT4All generation error: {e}")
            return self._chat_completion_fallback(history)


if __name__ == "__main__":
    # 模拟测试
    class MockConfig:
        # 确保你本地有这个模型文件，否则 GPT4All 会尝试下载
        model = "orca-mini-3b-gguf2-q4_0.gguf" 
        log_dir = "logs"

    print("--- Test Start ---")
    try:
        config = MockConfig()
        # 注意：第一次运行会加载模型，速度较慢
        gpt = GPT4ALLAPI(config)
        
        # 模拟 LLMAPI 传入的历史格式
        test_history = [{"role": "user", "content": "Hello, explain AI in 5 words."}]
        
        print("Generating...")
        result = gpt._chat_completion(test_history)
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Test failed: {e}")