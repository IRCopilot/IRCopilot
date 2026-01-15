import json
import os
import sys
import textwrap
import time
import traceback
from pathlib import Path

import loguru
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import confirm
from rich.console import Console
from rich.spinner import Spinner

from IRCopilot.config.chat_config import ChatGPTConfig
from IRCopilot.prompts.prompt_class_IRCopilot_en import IRCopilotPrompt
from IRCopilot.utils.APIs.module_import import dynamic_import
from IRCopilot.utils.chatgpt import ChatGPT
from IRCopilot.utils.prompt_select import prompt_ask, prompt_select
from IRCopilot.utils.task_handler import (
    localTaskCompleter,
    mainTaskCompleter,
    task_entry,
)
from IRCopilot.utils.RAG2prompt import rag2prompt

logger = loguru.logger


class IRCopilot:
    # 定义一些响应模板
    postfix_options = {
        "tool": "The input content is from a security testing tool. You need to list down all the points that are interesting to you; you should summarize it as if you are reporting to a senior penetration tester for further guidance.\n",
        "user-comments": "The input content is from user comments.\n",
        "web": "The input content is from web pages. You need to summarize the readable-contents, and list down all the points that can be interesting for penetration testing.\n",
        "default": "The user did not specify the input source. You need to summarize based on the contents.\n",
    }
    # tool: "输入内容来自安全测试工具。
    #   你需要列出所有对你来说有趣的点；你应该总结它，就像你在向一位高级渗透测试人员报告以寻求进一步指导一样。\n"
    # user-comments: "输入内容来自用户评论。\n"
    # web: "输入内容来自网页。你需要总结可读内容，并列出所有可能对渗透测试有趣的点。\n"
    # default: "用户未指定输入来源。你需要根据内容进行总结。\n"

    # 选项描述，用于 UI 提示
    options_desc = {
        "tool": " Paste the output of the security test tool used", # 粘贴所使用的安全测试工具的输出
        "user-comments": "",
        "web": " Paste the relevant content of a web page", # 粘贴相关网页的内容
        "default": " Write whatever you want, the tool will handle it", # 随意写入你想要的内容，工具会处理的
    }

    def __init__(
        self,
        log_dir="logs",
        reasoning_model="gpt-4-turbo",  # 实验设置
        parsing_model="gpt-4-turbo",
        useAPI=True,
    ):
        self.log_dir = log_dir  # 设置日志目录
        logger.add(sink=os.path.join(log_dir, "IRCopilot.log"))
        self.save_dir = "test_history"
        self.task_log = ({})
        self.useAPI = useAPI  # 标记是否使用API
        self.parsing_char_window = 16000  # 解析时的块大小（按字符数计）。
        # 动态导入model
        reasoning_model_object = dynamic_import(
            reasoning_model, self.log_dir
        )
        generation_model_object = dynamic_import(
            reasoning_model, self.log_dir
        )

        # todo
        reflection_model_object = dynamic_import(
            reasoning_model,self.log_dir
        )
        # extractor_model_object = dynamic_import(
        #     parsing_model,self.log_dir
        # )
        # parsing_model_object = dynamic_import(
        #     parsing_model, self.log_dir
        # )

        # 根据 API 使用标志初始化 ChatGPT 代理
        if useAPI is False:  # 已废弃的 cookie 使用方式
            self.parsingAgent = ChatGPT(ChatGPTConfig(log_dir=self.log_dir))
            self.reasoningAgent = ChatGPT(ChatGPTConfig(model=reasoning_model, log_dir=self.log_dir))
        else:
            self.generationAgent = generation_model_object
            self.reasoningAgent = reasoning_model_object
            # todo
            self.reflectionAgent = reflection_model_object
            # self.extractorAgent = extractor_model_object
            # self.parsingAgent = parsing_model_object

        self.prompts = IRCopilotPrompt  # 设置提示模板
        # 初始化控制台和旋转器
        self.console = Console()  # rich.console.Console
        self.spinner = Spinner("line", "Processing") # rich.spinner
        # 初始化会话 ID
        self.test_generation_session_id = None
        self.test_reasoning_session_id = None
        # todo
        self.reflection_session_id = None
        # self.extractor_session_id = None
        # self.input_parsing_session_id = None
        self.chat_count = 0  # 聊天计数器s
        self.step_reasoning = None  # Planner的tasks and decisions
        self.decision_response = None  # Planner的决策结果
        # todo
        self.history = {  # 初始化历史记录字典
            "user": [],
            "IRCopilot": [],
            "reasoning": [],
            "generation": [],
            "reflection": [],
            # "extractor": [],
            # "parsing": [],
            "exception": [],
        }
        self.action_history = []  # 存储用户的操作
        self.irt_and_task_history = []  # 存储系统的响应

        # 初始化时
        self.console.print("IRCopilot, design for incident response.", style="bold #94C9B7")
        self.console.print("Settings : ")
        # self.console.print(f" - parsing model: {parsing_model_object.name}", style="bold #94C9B7")
        self.console.print(f" - reasoning model: {reasoning_model_object.name}", style="bold #94C9B7")
        self.console.print(f" - use API: {useAPI}", style="bold #94C9B7")
        self.console.print(f" - log directory: {log_dir}", style="bold #94C9B7")

    def log_conversation(self, source, text):
        """
        将对话追加到历史记录中。
        """
        timestamp = time.time()
        self.history.setdefault(source, []).append((timestamp, text))

    def refresh_session(self):
        """
        刷新当前会话。如果使用的是 API 模式，则不需要刷新会话；如果不是，则刷新会话。

        具体操作如下：
        1. 如果使用的是 API 模式，提示用户不需要刷新会话，并将提示信息记录到对话历史中。
        2. 如果不是 API 模式，提示用户确保将 curl 命令放置在配置文件中，并等待用户确认。然后刷新 parsingAgent 和 reasoningAgent 的会话。
            最后提示用户会话已刷新，并将提示信息记录到对话历史中。

        """
        # 如果使用的是 API 模式，则不需要刷新会话
        if self.useAPI:
            self.console.print("You're using API mode, so no need to refresh the session.")
            self.log_conversation("IRCopilot", "You're using API mode, so no need to refresh the session.")
        else:
            # 提示用户确保将 curl 命令放置在指定的配置文件中，并将提示信息记录到对话历史中
            self.console.print("Please ensure that you put the curl command into `config/chatgpt_config_curl.txt`", style="bold green")
            self.log_conversation("IRCopilot", "Please ensure that you put the curl command into `config/chatgpt_config_curl.txt`")
            input("Press Enter to continue...")  # 等待用户按下回车键继续
            # 刷新会话
            self.reflectionAgent.refresh()
            self.reasoningAgent.refresh()
            # todo:思考这三个要更新吗
            # self.generationAgent.refresh()  # 无需刷新 短期记忆
            # self.extractorAgent.refresh()  # 无需刷新 短期记忆
            # self.parsingAgent.refresh()

            self.console.print(
                # 提示用户会话已刷新，并将提示信息记录到对话历史中
                "Session refreshed. If you receive the same session refresh request, please refresh the ChatGPT page and paste the new curl request again.",
                style="bold green",
            )
            self.log_conversation("IRCopilot", "Session refreshed.")
            return "Session refreshed."

    def _feed_init_prompts(self):
        """
        触发渗透测试的初始对话流程，通过用户输入构建起渗透测试的任务描述，并与内部的推理和生成模块交互。

        步骤：
        1. 从用户处获取渗透测试的基本信息，如目标 IP、任务类型等，通过 `prompt_ask` 函数实现，该函数允许用户输入一行描述。
        2. 将获取到的任务描述与预设的任务描述提示符合并，直接用作推理会话的输入，用于构建初始的渗透测试任务树。
        3. 将推理会话的输出传递给生成会话，用以进一步生成详细的任务指令，最后在控制台展示这些初始的任务指令。

        操作：
        - 使用 `prompt_ask` 收集用户输入。
        - 调用推理和生成会话处理任务描述，并在控制台上显示处理结果。
        - 记录所有相关输出到会话历史中，以供后续使用。
        """

        # 1. 获取用户输入的任务描述
        init_description = prompt_ask(
            "Please describe the incident response task, including the system, task, incident type, etc.\n1 > ",
            multiline=True,
        )
        self.log_conversation("user", init_description)  # 记录用户提供的任务描述
        self.task_log["task description"] = init_description  # 保存任务描述到任务日志中

        # 2. 构建初始IRT的输入
        prefixed_init_description = self.prompts.task_description + init_description
        # 任务描述(生成ir树) + 用户提供的信息
        with self.console.status(
            "[bold #94C9B7] Constructing Initial Incident Response Tree..."
        ) as status:
            # 推理会话处理 prefixed_init_description
            _reasoning_response = self.reasoningAgent.send_message(
                prefixed_init_description, self.test_reasoning_session_id
            )
            _task_selection_response = self.reasoningAgent.send_message(
                self.prompts.task_selection, self.test_reasoning_session_id
            )
            _reasoning_response = (_reasoning_response + "\n" +
            "----------------------------------------------------------------------------------------------------------"
                                   + "\n" + _task_selection_response)

        # 3. 生成会话 处理 推理会话的结果，获取任务的进一步细节
        # 注意，生成会话不用于任务初始化。
        with self.console.status("[bold #94C9B7] Generating Initial Task") as status:
            # 生成会话处理任务细节
            _generation_response = self.generationAgent.send_message(
                self.prompts.todo_to_command + _reasoning_response,
                self.test_generation_session_id,
            )
            # todo RAG

        # 在控制台显示初始任务生成结果
        response = f"{_reasoning_response}\n{_generation_response}"
        self.console.print("IRCopilot output: ", style="bold #94C9B7")
        self.console.print(response)
        self.log_conversation("IRCopilot", f"IRCopilot output: {response}")

    def initialize(self, previous_session_ids=None):
        """
        初始化核心会话并测试与 ChatGPT 的连接。

        功能：
        1. 定义三个会话：测试生成会话、推理会话和输入解析会话。
            - 如果提供了之前的会话ID，尝试恢复这些会话。
            - 如果没有提供之前的会话ID，或会话ID无效，则创建新的会话。
        2. 初始化会话后，调用 `_feed_init_prompts` 函数来启动渗透测试的提示流程。

        参数:
        - previous_session_ids: dict, 可选
            一个包含之前会话ID的字典，包括 "test_generation", "reasoning" 和 "parsing" 的会话ID。

        """

        # 定义三个会话：生成会话、推理会话和解析会话
        if previous_session_ids is not None and self.useAPI is False:
            # todo
            self.test_generation_session_id = previous_session_ids.get("test_generation", None)
            self.test_reasoning_session_id = previous_session_ids.get("reasoning", None)
            self.reflection_session_id = previous_session_ids.get("reflection", None)
            # self.input_parsing_session_id = previous_session_ids.get("parsing", None)
            # self.extractor_session_id = previous_session_ids.get("extractor", None)

            # todo 调试输出 个会话的ID
            print(f"Previous session ids: {str(previous_session_ids)}")
            print(f"Generation session id: {str(self.test_generation_session_id)}")
            print(f"Reasoning session id: {str(self.test_reasoning_session_id)}")
            print(f"Reflection session id: {str(self.reflection_session_id)}")
            # print(f"Parsing session id: {str(self.input_parsing_session_id)}")
            # print(f"Extractor session id:{str(self.extractor_session_id)}")

            print("-----------------")

            self.task_log = previous_session_ids.get("task_log", {})
            self.console.print(f"Task log: {str(self.task_log)}", style="bold green")
            print("You may use 'discuss' to remind the task.")  # 您可以使用讨论功能来提醒自己关于任务的内容。

            # todo
            if None in (self.test_generation_session_id, self.test_reasoning_session_id, self.reflection_session_id):
                # 如果有一个会话非空
                self.console.print("[bold red] Error: the previous session ids are invalid. Loading new sessions")
                self.initialize()

        else:
            with self.console.status(
                "[bold #94C9B7] Initialize ChatGPT Sessions..."
            ) as status:
                try:
                    # 创建并启动三个会话
                    self.test_generation_session_id = \
                    self.generationAgent.send_new_message(self.prompts.Generator_init)[1]
                    self.console.print(f"Generation session : {self.test_generation_session_id}", style="bold #94C9B7")

                    self.test_reasoning_session_id = \
                    self.reasoningAgent.send_new_message(self.prompts.Planner_init)[1]
                    self.console.print(f"Reasoning session : {self.test_reasoning_session_id}", style="bold #94C9B7")

                    # Reflection 会话
                    self.reflection_session_id = self.reflectionAgent.send_new_message(self.prompts.Reflector_init)[1]
                    self.reflectionAgent.send_message(self.prompts.bad_example, self.reflection_session_id)
                    self.console.print(f"Reflection session: {self.reflection_session_id}", style="bold #94C9B7")

                except AttributeError as ae:
                    self.console.print(f"[bold red] AttributeError: {ae} - 请检查 Agent 是否正确初始化。", style="bold red")
                    logger.error(ae)
                except KeyError as ke:
                    self.console.print(f"[bold red] KeyError: {ke} - 请检查 prompts 是否包含正确的键。", style="bold red")
                    logger.error(ke)
                except Exception as e:
                    self.console.print(f"[bold red] Error: 无法请求到 GPT。详细错误：{e}", style="bold red")
                    logger.error(e)

            self.console.print("- IRCopilot Agents Initialized.", style="bold #94C9B7")
            self._feed_init_prompts()

    def save_session(self):
        """
        保存当前会话。
        """
        self.console.print("Before you quit, you may want to save the current session.", style="bold green")
        # 1. 请输入当前会话的名称。（默认为当前时间戳）
        save_name = prompt_ask(
            "Please enter the name of the current session. (Default with current timestamp)\n> ",
            multiline=False,
        )
        save_name = save_name or str(time.time())

        # 2. 保存当前会话
        save_path = Path(__file__).resolve().parent.parents[1] / self.save_dir / save_name
        save_path.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在
        with open(save_path, "w") as f:
            session_ids = {
                # todo
                "reasoning": self.test_reasoning_session_id,
                "test_generation": self.test_generation_session_id,
                "reflection": self.reflection_session_id,
                # "parsing": self.input_parsing_session_id,
                # "extractor": self.extractor_session_id,
                "task_log": self.task_log,
            }
            json.dump(session_ids, f)
        self.console.print(f"The current session is saved as {save_name}", style="bold green")
        return

    def _preload_session(self):
        """
        从保存目录预加载会话。
        """
        if continue_from_previous := confirm(
                "Do you want to continue from previous session?"
                # 您想要继续上一次的会话吗？
        ):
            # 从保存目录加载文件名
            save_dir_path = Path(__file__).resolve().parents[2] / self.save_dir
            filenames = list(save_dir_path.glob('*'))  # 获取文件名列表

            if len(filenames) == 0:
                # 如果没有找到之前的会话，提示用户并返回None
                print("No previous session found. Please start a new session.")
                return None
            else:  # 打印所有文件名
                print("Please select the previous session by its index (integer):")
                for i, filename in enumerate(filenames):
                    print(f"{str(i)}. {filename.name}")
                # 请求用户输入
                try:
                    index = int(input("Please key in your option (integer): "))
                    previous_testing_name = filenames[index]
                    print(f"You selected: {previous_testing_name.name}")
                except ValueError as e:
                    print("You input an invalid option. Will start a new session.")
                    return None

        elif continue_from_previous is False:
            return None
        else:
            # 如果输入无效，提示错误并开始新会话
            print("You input an invalid option. Will start a new session.")
            return None

        # 2. 加载之前会话的信息
        if previous_testing_name is not None:
            # 尝试使用json加载文件内容
            try:
                with open(previous_testing_name, "r") as f:
                    return json.load(f)
            except Exception as e:
                print("Error when loading the previous session. The file name is not correct")
                print(e)
                previous_testing_name = None
                return None

    def reasoning_handler(self, text):
        """
        处理推理逻辑，并根据输入文本返回处理结果。

        功能：
        1. 如果输入文本过长，会先调用输入解析处理器进行简化。
        2. 通过推理代理对处理后的文本进行推理，更新IRT。
        3. 验证IRT的正确性，并选择所有待办事项。
        4. 将推理的完整输出结果记录在对话历史中，并返回给调用方。
        """
        # if len(text) > self.parsing_char_window:
        #     # 如果文本长度超过解析字符窗口，调用input_parsing_handler()处理文本
        #     text = self.input_parsing_handler(text)

        # 1. 更新IRT
        _updated_irt_response = self.reasoningAgent.send_message(
            self.prompts.process_results + text, self.test_reasoning_session_id
        )

        # 2. 验证IRT是否正确，反思并修订IRT
        # TODO：需要实现验证逻辑

        # 3. 选择最优任务
        decision_response = self.reasoningAgent.send_message(
                        self.prompts.task_selection, self.test_reasoning_session_id
        )
        # 获取完整的输出结果：
        response = (_updated_irt_response + "\n" +
            "----------------------------------------------------------------------------------------------------------"
                                   + "\n" + decision_response)
        self.log_conversation("reasoning", response)
        return response,decision_response

    def test_generation_handler(self, text):
        """
        发送内容至 ChatGPT 的生成会话，并获取生成的响应。
        """
        # input_handler: more/tdo
        response = self.generationAgent.send_message(
            text, self.test_generation_session_id
        )
        # 记录对话
        self.log_conversation("generation", response)
        return response
    
    # 处理用户的本地输入请求，并根据用户选择的操作提供相应的响应。
    def local_input_handler(self):
        """
        请求用户输入以处理本地任务。
        """
        local_task_response = ""
        self.chat_count += 1
        local_request_option = task_entry(completer_type='local')
        self.log_conversation("user", local_request_option)

        if local_request_option == "help":
            # 显示帮助详情
            print(localTaskCompleter().task_details)

        # generation: 深入研究问题并给出潜在的答案
        elif local_request_option == "discuss":  # 分析问题
            # (1) 如果用户选择讨论，请求多行输入
            self.console.print("Please share your findings/questions with IRCopilot.(End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please share your findings/questions with IRCopilot.")
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            # (2) 将信息传递给推理会话
            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                # todo:RAG
                local_task_response = self.test_generation_handler(
                    self.prompts.local_task_prefix + user_input
                )
                # todo:对生成会话进行评估反思 循环？
                # local_task_response = self.reflect_cmd(local_task_response)

            # (3) 显示结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(local_task_response + "\n", style="yellow")
            self.log_conversation("IRCopilot", local_task_response)

        # generation: 尝试识别解决问题的所有潜在方法
        elif local_request_option == "deliberate":  # 解决问题
            # (1) 如果用户选择头脑风暴，请求多行输入
            self.console.print("Please share your concerns and questions with IRCopilot.(End with <ctrl + enter>)")
            self.log_conversation("IRCopilot", "Please share your concerns and questions with IRCopilot.")
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            # (2) 将信息传递给生成会话
            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                # todo:RAG
                local_task_response = self.test_generation_handler(
                    self.prompts.local_task_brainstorm + user_input
                )

            # (3) 显示结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(local_task_response + "\n", style="yellow")
            self.log_conversation("IRCopilot", local_task_response)

        elif local_request_option == "exit":
            # 如果用户选择继续主任务
            self.console.print("Exit the local task and continue the main task.")
            self.log_conversation("IRCopilot", "Exit the local task and continue the main task.")
            local_task_response = "exit"

        return local_task_response
    
    # 处理用户输入并基于输入调用不同的处理逻辑
    def input_handler(self) -> str:
        """
        The design details are based on IRCopilot_design.md

        Return
        -----
        response: str
            The response from the chatGPT model.
        """
        self.chat_count += 1

        request_option = task_entry(completer_type='main')
        self.log_conversation("user", request_option)

        # 检查API会话是否过期
        if not self.useAPI:
            conversation_history = self.parsingAgent.get_conversation_history()
            while conversation_history is None:
                self.refresh_session()
                conversation_history = self.parsingAgent.get_conversation_history()

        if request_option == "chat_with_Planner":
            self.console.print("Please send your thoughts to Planner. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send your thoughts to Planner.")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", thoughts)

            with self.console.status("[bold #94C9B7] IRCopilot thinking...") as status:
                response = self.reasoningAgent.send_message(thoughts, self.test_reasoning_session_id)
                self.step_reasoning_response = response

            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(response + "\n", style="green")
            self.log_conversation("IRCopilot", response)

        # 用户->解析->推理->生成
        elif request_option == "next":
            self.console.print("Your input: (End with <ctrl + right>)", style="bold green")
            # 获取用户的详细输入。
            user_input = prompt_ask("1 > ", multiline=True)
            # self.log_conversation("user", f"Source: {options[int(source)]}\n{user_input}")
            self.log_conversation("user", user_input)

            # (1) 使用input_parsing_handler()解析用户输入
            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                # parsed_input = self.input_parsing_handler(
                #     user_input, source=options[int(source)]
                # )
                # (2) 将 解析后的信息 传递给 推理会话，获取基于解析结果的推理响应。
                response, self.decision_response = self.reasoning_handler(user_input)
                self.step_reasoning_response = response

            # (3) 显示推理响应
            self.console.print(f"Based on the analysis, the following tasks are recommended: {response}\n", style="bold green")
            self.log_conversation("IRCopilot", f"Based on the analysis, the following tasks are recommended: {response}")

        elif request_option == "analyse_results":
            self.console.print("Please send the results of the guidance/command execution to IRCopilot. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send the results of the guidance/command execution to IRCopilot.")
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            self.action_history.append(user_input)  # 存储用户操作

            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                _updated_irt_response = self.reasoningAgent.send_message(
                    self.prompts.analysis_results + user_input, self.test_reasoning_session_id
                )

                decision_response = self.reasoningAgent.send_message(
                    self.prompts.task_selection, self.test_reasoning_session_id
                )

                response = (_updated_irt_response + "\n" +
                            "----------------------------------------------------------------------------------------------------------"
                            + "\n" + decision_response)
                self.irt_and_task_history.append(response)  # 存储系统响应

                # 可以再传递给generate
                self.step_reasoning_response = response

            # (3) 打印结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(response + "\n", style="green")
            self.log_conversation("IRCopilot", response)

        elif request_option == 'analyse_files':
            self.console.print("Please send the files that need to be reviewed to IRCopilot. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send the files that need to be reviewed to IRCopilot.")
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            self.action_history.append(user_input)  # 存储用户操作

            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                _updated_irt_response = self.reasoningAgent.send_message(
                    self.prompts.analysis_files + user_input, self.test_reasoning_session_id
                )

                decision_response = self.reasoningAgent.send_message(
                    self.prompts.task_selection, self.test_reasoning_session_id
                )

                response = (_updated_irt_response + "\n" +
            "----------------------------------------------------------------------------------------------------------"
                                   + "\n" + decision_response)
                self.irt_and_task_history.append(response)  # 存储系统响应

                # 可以再传递给generate
                self.step_reasoning_response = response

            # (3) 打印结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(response + "\n", style="green")
            self.log_conversation("IRCopilot", response)

        # 推理: 提出意见，更新任务
        elif request_option == "discuss_with_IRCopilot":
            # (1) 请求用户多行输入以进行讨论
            self.console.print("Please share your thoughts/questions with IRCopilot. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please share your thoughts/questions with IRCopilot.")
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)

            # (2) 将信息传递给推理会话
            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                response,self.decision_response = self.reasoning_handler(self.prompts.discussion + user_input)
                # 测试人员提供了以下思考供您参考，请给出您的意见，并在必要时更新任务。+ user_input

                # 可以再传递给generate
                self.step_reasoning_response = response

            # (3) 打印结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(response + "\n", style="yellow")
            self.log_conversation("IRCopilot", response)

        # 重新生成任务树和指导
        elif request_option == "regenerate_the_IRT":
            self.console.print("Please share your thoughts/questions to regenerate the IRT. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please share your thoughts/questions to regenerate the IRT.")
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            # (1) 请求推理会话分析当前情况并列出顶级子任务
            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                # 根据要求分析任务并再次生成任务树
                reasoning_response,self.decision_response = self.reasoning_handler(self.prompts.regenerate + user_input)

                # 重新生成指导
                message = self.prompts.todo_to_command + "\n" + reasoning_response
                generation_response = self.test_generation_handler(message)

            # (3) 打印结果
            self.console.print(f"Based on the analysis, the following tasks are recommended: \n{reasoning_response}\n",
                               style="bold green")  # reason->任务树

            self.console.print(f"You can follow the instructions below to complete the tasks. \n{generation_response}\n",
                               style="bold green")  # generation->指导

            response = reasoning_response
            self.log_conversation(
                "IRCopilot",
                f"Based on the analysis, the following tasks are recommended:{response}\n"
                "You can follow the instructions below to complete the tasks."
                f"{generation_response}"
            )

        elif request_option == "chat_with_Generator":
            self.console.print("Please send your thoughts to Generator. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send your thoughts to Generator.")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", thoughts)

            with self.console.status("[bold #94C9B7] IRCopilot thinking...") as status:
                response = self.generationAgent.send_message(thoughts, self.test_generation_session_id)
                self.step_generation_response = response

            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(response + "\n", style="green")
            self.log_conversation("IRCopilot", response)

        elif request_option == "generate_commands":
            if not hasattr(self, "step_reasoning_response"):
                self.console.print(
                    "You have not initialized the task yet. Please perform the basic testing following `next` option.",
                    style="bold red",
                )
                response = "You have not initialized the task yet. Please perform the basic testing following `next` option."
                self.log_conversation("IRCopilot", response)
                return response
            # (2) 开始本地任务生成
            # (2.1) 请求推理会话分析当前情况，并解释任务
            self.console.print("IRCopilot will generate details", style="bold #94C9B7")
            self.log_conversation( "IRCopilot", "IRCopilot will generate details.")

            # (2.2) 将子任务传递给测试生成会话
            with self.console.status("[bold #94C9B7] IRCopilot Generating...") as status:
                # todo:RAG
                # # 提取推理结果的关键词
                # question = self.extractorAgent.send_message(
                #     self.prompts.extract_keyword + self.step_reasoning_response, self.extractor_session_id
                # )
                # # 关键词->RAG->prompt
                # rag_prompt = rag2prompt(question=question)
                # # 根绝RAG检索的背景生成任务、指导、或是命令

                self.step_generation_response = self.test_generation_handler(
                    self.step_reasoning_response
                )

                # # todo:对生成会话进行评估反思 循环？
                # generation_response = self.reflect_cmd(generation_response)

            # 打印进一步的详细信息
            self.console.print(f"Below are the further details.\n{self.step_generation_response}\n",style="bold green")
            response = self.step_generation_response  # 生成会话的结果
            self.log_conversation("IRCopilot", response)

        elif request_option == "sub-task":
            if not hasattr(self, "step_generation_response"):
                self.console.print(
                    "You haven't initialized the generator yet. Please perform the basic testing following `generate` option.",
                    style="bold red",
                )
                response = "You haven't initialized the generator yet. Please perform the basic testing following `generate` option."
                self.log_conversation("IRCopilot", response)
                return response

            while True:
                _local_init_response = self.test_generation_handler(
                    self.prompts.local_task_init  # 生成会话 忽略之前的信息
                )
                local_task_response = self.local_input_handler()
                if local_task_response == "exit":
                    break
            # todo：这里子任务的response有待商榷
            response = local_task_response

        elif request_option == "chat_with_Reflector":
            self.console.print("Please send your thoughts to Reflector. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send your thoughts to Reflector.")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", thoughts)

            with self.console.status("[bold #94C9B7] IRCopilot thinking...") as status:
                response = self.reflectionAgent.send_message(thoughts, self.reflection_session_id)
                self.step_reflector_response = response

            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(response + "\n", style="green")
            self.log_conversation("IRCopilot", response)

        # 对命令的执行的结果进行反思
        elif request_option == "reflect":
            try:
                self.console.print("Please send your thoughts to GPT for reflection. (End with <ctrl + right>)")
                self.log_conversation("IRCopilot", "Please send your thoughts to GPT for reflection.")
                thoughts = prompt_ask("1 > ", multiline=True)
                self.log_conversation("user", thoughts)

                # self.console.print("Please send your feedback to GPT for reflection. (End with <ctrl + right>)")
                # self.log_conversation("IRCopilot", "Please send your feedback to GPT for reflection.")
                # feedback_input = prompt_ask("> ",multiline=True)
                # self.log_conversation("user", feedback_input)

                # 定义k值，表示希望获取的历史记录的数量
                self.console.print("Enter the number of recent conversations to include in reflection:")

                user_k = prompt_ask("num > ")
                try:
                    k = int(user_k) if user_k.strip() else 1
                except ValueError:
                    print("Invalid input. Using default value.")
                    k = 1

                # 获取最近的 k 个决策或者任务
                recent_tasks = "\n\n".join(
                    self.irt_and_task_history[-k:] if len(self.irt_and_task_history) >= k else self.irt_and_task_history)
                # 获取最近的 k 个执行结果
                recent_actions = "\n\n".join(
                    self.action_history[-k:] if len(self.action_history) >= k else self.action_history)

                # 推理(IRT)->决策->生成(命令)->执行(人工)->反思
                with self.console.status("[bold #94C9B7] IRCopilot Reflecting...") as status:
                    reflect_input = (
                        self.prompts.reflect_input
                        + "你之前设计的应急响应树(IRT)以及你在IRT基础上做出的决策" + recent_tasks + "\n\n"
                        + "应急响应步骤的结果：\n" + recent_actions + "\n\n"
                        + "分析师的想法或是你之前的反思(可以为空):\n" + thoughts
                    )
                    response = self.reflectionAgent.send_message(reflect_input,self.reflection_session_id)
                    self.step_reasoning_response = response

                self.console.print("IRCopilot:\n", style="bold #94C9B7")
                self.console.print(response + "\n", style="green")
                self.log_conversation("IRCopilot", response)

            except Exception as e:
                self.console.print(f"[red]An error occurred during reflection: {e}[/red]")
                self.log_conversation("IRCopilot", f"An error occurred during reflection: {e}")

        elif request_option == "exit_IRCopilot":
            response = False
            self.console.print("Thank you for using IRCopilot!", style="bold green")
            self.log_conversation("IRCopilot", "Thank you for using IRCopilot!")

        else:
            self.console.print("Please key in the correct options.", style="bold red")
            self.log_conversation("IRCopilot", "Please key in the correct options.")
            response = "Please key in the correct options."

        return response

    # 初始化、处理输入，并管理整个程序的执行流程
    def main(self):
        """
        IRCopilot 的主函数。设计基于 IRCopilot_design.md 文档。
        """
        # 0. 初始化核心会话并测试与 chatGPT 的连接
        loaded_ids = self._preload_session()      
        self.initialize(previous_session_ids=loaded_ids)

        # 进入主循环。
        while True:
            try:
                result = self.input_handler()  # 处理用户输入
                self.console.print(
                    "-----------------------------------------", style="bold white"
                )
                if not result:  # 结束会话
                    break
            except Exception as e:  # 捕获所有异常
                self.log_conversation("exception", str(e))
                self.console.print(f"Exception: {str(e)}", style="bold red")
                exc_type, exc_obj, exc_tb = sys.exc_info()  # 捕获异常信息
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]  # 获取异常发生的文件名
                self.console.print("Exception details are below.", style="bold red")
                # self.console.print(exc_type, fname, exc_tb.tb_lineno)  # 提供了错误的基本信息
                print(traceback.format_exc())  # 提供了更详细的调用栈信息
                break

        log_name = f"IRCopilot_log_{time.time()}.txt"
        log_path = os.path.join(self.log_dir, log_name)  # 存在日志文件夹
        with open(log_path, "w") as f:
            json.dump(self.history, f)
        self.save_session()


if __name__ == "__main__":
    IRCopilot = IRCopilot()
    IRCopilot.main()
