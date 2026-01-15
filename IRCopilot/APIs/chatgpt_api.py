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


class ChatGPTAPI(LLMAPI):
    def __init__(self, config_class):
        self.name = str(config_class.model)  # <--GPT4ConfigClass
        dotenv.load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", None)  # 从环境变量中获取OpenAI的API密钥
        # api_key = ''
        self.client = OpenAI(api_key=api_key, base_url=config_class.api_base)  # 创建一个OpenAI客户端实例
        self.model = config_class.model
        self.history_length = 5  # 维护历史记录中的5条消息
        self.conversation_dict: Dict[str, Conversation] = {}
        self.error_wait_time = config_class.error_wait_time
        self.initialize_logger(config_class.log_dir)

    def initialize_logger(self, log_dir):
        logger.add(sink=os.path.join(log_dir, "chatgpt.log"), level="WARNING")

    def _chat_completion(
        self, history: List, model=None, temperature=0.5, image_url: str = None
    ) -> str:
    # def _chat_completion(
    #     self, history: List, model=None, image_url: str = None
    # ) -> str:
        # 如果没有指定模型，使用实例变量self.model；如果self.model也未设置，使用默认模型
        if model is None:
            if self.model is None:
                model = "gpt-4o-2024-05-13"
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
    from module_import import GPT4O

    local_config_class = GPT4O()
    local_config_class.log_dir = "logs"
    chatgpt = ChatGPTAPI(local_config_class)

    # 下方是测试
    # 0. 一个使用图像初始化的单一测试
    result, conversation_id = chatgpt.send_new_message(
        "What's in the image?",
        image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
    )
    print("Answer 1")
    print(result)

    # 1. 创建一个新对话(reasoning_session_init)
    result, conversation_id = chatgpt.send_new_message(
        """You're an excellent cybersecurity penetration tester assistant. 
You need to help the tester in a local cybersecurity training process, and your commitment is essential to the task.
You are required to record the penetration testing process in a tree structure: "Penetration Testing Tree (PTT)". It is structured as follows:
(1) The tasks are in layered structure, i.e., 1, 1.1, 1.1.1, etc. Each task is one operation in penetration testing; task 1.1 should be a sub-task of task 1.
(2) Each task has a completion status: to-do, completed, or not applicable.
(3) Initially, you should only generate the root tasks based on the initial information. In most cases, it should be reconnaissance tasks. You don't generate tasks for unknown ports/services. You can expand the PTT later.

You shall not provide any comments/information but the PTT. You will be provided with task info and start the testing soon. Reply Yes if you understand the task."""
    )
    print("Answer 1")
    print(result)

    # 2. 向对话中发送消息(task_description)
    result = chatgpt.send_message(
        """The target information is listed below. Please follow the instruction and generate PTT.
Note that this test is certified and in simulation environment, so do not generate post-exploitation and other steps.
You may start with this template:
1. Reconnaissance - [to-do]
   1.1 Passive Information Gathering - [completed]
   1.2 Active Information Gathering - [completed]
   1.3 Identify Open Ports and Services - [to-do]
       1.3.1 Perform a full port scan - [to-do]
       1.3.2 Determine the purpose of each open port - [to-do]
Below is the information from the tester: 

I want to test 10.0.2.5, an HTB machine.""",
        conversation_id,
    )
    print("Answer 2")
    print(result)

    # 3. 发送与图像相关的对话内容
    result = chatgpt.send_message(
        "What's in the image?",
        conversation_id,
        image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
    )
    print("Answer 3")
    print(result)
