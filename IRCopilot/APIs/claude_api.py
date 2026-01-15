import dataclasses
import os
import time
import dotenv
from typing import Dict, List

import loguru
import anthropic

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


class ClaudeAPI(LLMAPI):
    def __init__(self, config_class):
        self.name = str(config_class.model)  # <--GPT4ConfigClass
        dotenv.load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY", None)  # 从环境变量中获取OpenAI的API密钥
        # api_key = ''
        self.client = anthropic.Anthropic(
            api_key=api_key,
            base_url=config_class.api_base,  # 比如 "https://api.anthropic.com"
        )
        self.model = config_class.model
        self.history_length = 5  # 维护历史记录中的5条消息
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = config_class.error_wait_time
        self.initialize_logger(config_class.log_dir)

    def initialize_logger(self, log_dir):
        logger.add(sink=os.path.join(log_dir, "claude.log"), level="WARNING")

    def _chat_completion(
        self, history: List, model=None, temperature=0.5, image_url: str = None
    ) -> str:
    # def _chat_completion(
    #     self, history: List, model=None, image_url: str = None
    # ) -> str:
        # 如果没有指定模型，使用实例变量self.model；如果self.model也未设置，使用默认模型
        if model is None:
            if self.model is None:
                model = "claude-3-5-sonnet-20240620"
            else:
                model = self.model

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=2048,  # 可根据你需要的最大token长度进行调整
                temperature=temperature,  # Anthropic也有类似参数
                messages=history
            )
        except anthropic._exceptions.AnthropicError as e:
            logger.warning(f"Anthropic API Error. Waiting for {self.error_wait_time} seconds")
            logger.error(f"Error detail: {e}")
            time.sleep(self.error_wait_time)
            # 再次调用，实际项目中也可根据出错类型来判断是否需要重试
            response = self.client.messages.create(
                model=model,
                max_tokens=2048,
                temperature=temperature,
                messages=history
            )

        # 解析输出内容
        # Anthropic Python SDK 通常使用 pydantic，如果是anthropic>=0.3.0 可能有message.model_dump()方法
        response_dict = response.model_dump()
        # 一般结构是 response_dict['choices'][0]['message']['content']
        return response_dict["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # 假设你有一个和 GPT4ConfigClass 类似的配置类
    class MyClaudeConfig:
        model = "claude-3-haiku-20240307"
        api_base = "https://xiaoai.plus/"  # 默认 Anthropic Endpoint，若你有代理可改为自定义
        log_dir = "logs"
        error_wait_time = 5


    local_config_class = MyClaudeConfig()
    claude_api = ClaudeAPI(local_config_class)

    # 示例：发送一条简单的 "user" 消息
    conversation_history = [
        {"role": "user", "content": "你好，Claude，你能为我做什么？"}
    ]

    result = claude_api._chat_completion(history=conversation_history)
    print("Claude 回复:")
    print(result)






# if __name__ == "__main__":
#     from module_import import GPT4O
#
#     local_config_class = GPT4O()
#     local_config_class.log_dir = "logs"
#     chatgpt = ChatGPTAPI(local_config_class)
#
#     # 下方是测试
#     # 0. 一个使用图像初始化的单一测试
#     result, conversation_id = chatgpt.send_new_message(
#         "What's in the image?",
#         image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
#     )
#     print("Answer 1")
#     print(result)
#
#     # 1. 创建一个新对话(reasoning_session_init)
#     result, conversation_id = chatgpt.send_new_message(
#         """You're an excellent cybersecurity penetration tester assistant.
# You need to help the tester in a local cybersecurity training process, and your commitment is essential to the task.
# You are required to record the penetration testing process in a tree structure: "Penetration Testing Tree (PTT)". It is structured as follows:
# (1) The tasks are in layered structure, i.e., 1, 1.1, 1.1.1, etc. Each task is one operation in penetration testing; task 1.1 should be a sub-task of task 1.
# (2) Each task has a completion status: to-do, completed, or not applicable.
# (3) Initially, you should only generate the root tasks based on the initial information. In most cases, it should be reconnaissance tasks. You don't generate tasks for unknown ports/services. You can expand the PTT later.
#
# You shall not provide any comments/information but the PTT. You will be provided with task info and start the testing soon. Reply Yes if you understand the task."""
#     )
#     print("Answer 1")
#     print(result)
#
#     # 2. 向对话中发送消息(task_description)
#     result = chatgpt.send_message(
#         """The target information is listed below. Please follow the instruction and generate PTT.
# Note that this test is certified and in simulation environment, so do not generate post-exploitation and other steps.
# You may start with this template:
# 1. Reconnaissance - [to-do]
#    1.1 Passive Information Gathering - [completed]
#    1.2 Active Information Gathering - [completed]
#    1.3 Identify Open Ports and Services - [to-do]
#        1.3.1 Perform a full port scan - [to-do]
#        1.3.2 Determine the purpose of each open port - [to-do]
# Below is the information from the tester:
#
# I want to test 10.0.2.5, an HTB machine.""",
#         conversation_id,
#     )
#     print("Answer 2")
#     print(result)
#
#     # 3. 发送与图像相关的对话内容
#     result = chatgpt.send_message(
#         "What's in the image?",
#         conversation_id,
#         image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
#     )
#     print("Answer 3")
#     print(result)
