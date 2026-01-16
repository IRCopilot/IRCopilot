import dataclasses
import json
import os
import time
from typing import Any, Dict, List, Optional

import boto3
import loguru
from tenacity import retry, stop_after_attempt, wait_fixed

from IRCopilot.utils.llm_api import LLMAPI

logger = loguru.logger
logger.remove()


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


class TitanAPI(LLMAPI):
    """
    基于 AWS Bedrock (Titan 模型) 的接口封装类。
    """

    def __init__(self, config_class, use_langfuse_logging=False):
        self.name = str(config_class.model)
        self.model = config_class.model or "amazon.titan-tg1-large"
        self.log_dir = getattr(config_class, "log_dir", "logs")
        
        self.history_length = 5
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = 3

        # 初始化 Bedrock Runtime 客户端
        # 注意: invoke_model 需要 'bedrock-runtime'，而非 'bedrock'
        region_name = os.getenv("AWS_REGION", "us-west-2")
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name,
        )

        self.initialize_logger(self.log_dir)

    def initialize_logger(self, log_dir: str):
        """初始化日志"""
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        logger.add(sink=os.path.join(log_dir, "titan.log"), level="WARNING")

    def _format_prompt(self, history: List[Dict[str, Any]]) -> str:
        """
        辅助方法：将聊天历史 (List of Dicts) 转换为 Titan 的文本 Prompt。
        格式:
        User: <input>
        Bot: <response>
        ...
        User: <current_input>
        Bot:
        """
        prompt = ""
        for msg in history:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            if role == "user":
                prompt += f"User: {content}\n"
            elif role in ["assistant", "model", "bot"]:
                prompt += f"Bot: {content}\n"
            elif role == "system":
                prompt += f"System: {content}\n"
        
        # 确保以 Bot: 结尾引导生成
        if not prompt.strip().endswith("Bot:"):
            prompt += "Bot:"
        
        return prompt

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _chat_completion(
        self, 
        history: List[Dict[str, Any]], 
        model: Optional[str] = None, 
        temperature: float = 0.5
    ) -> str:
        """
        核心方法：调用 Bedrock Runtime 执行推理。
        """
        target_model = model if model else self.model
        
        # 1. 转换 Prompt
        # Titan 是文本补全模型，不直接支持 Chat 结构的 JSON
        input_text = self._format_prompt(history)

        # 2. 构建 Payload (Titan Express/Lite 标准格式)
        # Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-text.html
        payload = {
            "inputText": input_text,
            "textGenerationConfig": {
                "maxTokenCount": 2048,
                "stopSequences": ["User:"],  # 防止模型自言自语生成下一轮 User 内容
                "temperature": temperature,
                "topP": 0.9,
            },
        }
        
        body = json.dumps(payload)

        try:
            # 3. 调用 API
            response = self.bedrock_runtime.invoke_model(
                body=body,
                modelId=target_model,
                accept="application/json",
                contentType="application/json",
            )
            
            # 4. 解析响应
            response_body = json.loads(response.get("body").read())
            
            # Titan 返回结构: {"inputTextTokenCount": ..., "results": [{"tokenCount": ..., "outputText": "..."}]}
            results = response_body.get("results")
            if results and len(results) > 0:
                output_text = results[0].get("outputText")
                return output_text.strip()
            
            return ""

        except Exception as e:
            logger.error(f"Bedrock invocation failed: {e}")
            # log detailed error for debugging
            logger.debug(f"Payload: {body}")
            raise e


if __name__ == "__main__":
    # 模拟测试
    class MockConfig:
        # 确保你有权限访问此模型 ID
        model = "amazon.titan-text-express-v1" 
        log_dir = "logs"

    print("--- Test Start ---")
    try:
        config = MockConfig()
        # 注意：运行此测试需要本地配置了 AWS Credentials (~/.aws/credentials)
        titan = TitanAPI(config)

        # 构造测试历史
        history = [
            {"role": "user", "content": "Hello, explain AWS in one sentence."}
        ]

        print(f"Invoking model: {titan.model}...")
        result = titan._chat_completion(history)
        print(f"Titan Response: {result}")

    except Exception as e:
        print(f"Test failed (Expected if AWS creds missing): {e}")