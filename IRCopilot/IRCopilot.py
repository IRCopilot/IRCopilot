import json
import os
import sys
import textwrap
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import loguru
from rich.console import Console
from rich.spinner import Spinner
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import confirm

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
    """
    IRCopilot: Benchmarking and Augmenting Large Language Models for Incident Response
    """
    
    POSTFIX_OPTIONS = {
        "tool": "The input content is from a security testing tool. You need to list down all the points that are interesting to you; you should summarize it as if you are reporting to a senior penetration tester for further guidance.\n",
        "user-comments": "The input content is from user comments.\n",
        "web": "The input content is from web pages. You need to summarize the readable-contents, and list down all the points that can be interesting for penetration testing.\n",
        "default": "The user did not specify the input source. You need to summarize based on the contents.\n",
    }

    OPTIONS_DESC = {
        "tool": " Paste the output of the security test tool used",
        "user-comments": "",
        "web": " Paste the relevant content of a web page",
        "default": " Write whatever you want, the tool will handle it",
    }


    def __init__(
        self,
        log_dir="logs",
        llm_model="gpt-5.1-2025-11-13",
        useAPI=True,
    ):
        # 1. 基础配置
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(sink=self.log_dir / "IRCopilot.log")

        self.save_dir = "test_history"
        self.task_log: Dict[str, Any] = {}
        self.useAPI = useAPI
        self.parsing_char_window = 16000

        # 2. 模型加载 (动态导入)
        self.planner_agent = dynamic_import(
            llm_model, self.log_dir
        )
        self.generator_agent = dynamic_import(
            llm_model, self.log_dir
        )
        self.reflector_agent = dynamic_import(
            llm_model, self.log_dir
        )

        # 3. 提示词与UI组件
        self.prompts = IRCopilotPrompt()
        self.console = Console()    # rich.console.Console
        self.spinner = Spinner("line", "Processing")    # rich.spinner
        
        # 4. 会话状态初始化
        self.generator_session_id: Optional[str] = None
        self.planner_session_id: Optional[str] = None
        self.reflector_session_id: Optional[str] = None

        self.chat_count = 0
        self.planner_response = None     # Planner 的每一步响应
        self.selected_task = None       # Planner的决策结果

        # 5. 历史记录初始化
        self.history: Dict[str, List[Tuple[float, str]]] = {
            "user": [],
            "IRCopilot": [],
            "planner": [],
            "generator": [],
            "reflector": [],
            "exception": [],
        }
        self.action_history: List[str] = []     # 存储用户的操作
        self.irt_and_task_history: List[str] = []       # 存储系统的响应
        
        # 6. 打印欢迎信息
        self._print_welcome_info(llm_model, useAPI)


    def _print_welcome_info(self, llm_model: str, useAPI: bool):
        """打印初始化信息"""
        self.console.print("IRCopilot, design for incident response.", style="bold #94C9B7")
        self.console.print("Settings : ")
        try:
            # 尝试获取模型名称，处理不同类型的 Agent 对象
            model_name = getattr(self.planner_agent, 'name', llm_model)
            self.console.print(f" - llm model: {model_name}", style="bold #94C9B7")
        except AttributeError:
            self.console.print(f" - llm model: {llm_model}", style="bold #94C9B7")
            
        self.console.print(f" - use API: {useAPI}", style="bold #94C9B7")
        self.console.print(f" - log directory: {self.log_dir}", style="bold #94C9B7") 

    def log_conversation(self, source: str, text: str):
        """将对话追加到历史记录中。"""
        timestamp = time.time()
        self.history.setdefault(source, []).append((timestamp, text))

    def refresh_session(self):
        """刷新当前会话 (主要用于非 API 模式)。"""
        if self.useAPI:
            msg = "You're using API mode, so no need to refresh the session."
            self.console.print(msg)
            self.log_conversation("IRCopilot", msg)
            return

        self.console.print("Please ensure that you put the curl command into `config/chatgpt_config_curl.txt`", style="bold green")
        self.log_conversation("IRCopilot", "Please ensure that you put the curl command into `config/chatgpt_config_curl.txt`")
        input("Press Enter to continue...")

        # 刷新 Agent
        if hasattr(self.reflector_agent, 'refresh'): self.reflector_agent.refresh()
        if hasattr(self.planner_agent, 'refresh'): self.planner_agent.refresh()
        
        msg = "Session refreshed. If you receive the same session refresh request, please refresh the ChatGPT page and paste the new curl request again."
        self.console.print(msg, style="bold green")
        self.log_conversation("IRCopilot", "Session refreshed.")
        return "Session refreshed."

    def save_session(self):
        """保存当前会话状态到文件。"""
        self.console.print("Before you quit, you may want to save the current session.", style="bold green")
        
        default_name = str(time.time())
        save_name = prompt_ask(
            f"Please enter the name of the current session. (Default: {default_name})\n> ",
            multiline=False,
        ) or default_name

        project_root = Path(__file__).resolve().parent.parent 
        save_path = project_root / self.save_dir / save_name
        save_path.parent.mkdir(parents=True, exist_ok=True)

        session_data = {
            "planner": self.planner_session_id,
            "generator": self.generator_session_id,
            "reflector": self.reflector_session_id,
            "task_log": self.task_log,
        }

        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(session_data, f, indent=4)    # 增加 indent 方便阅读
            
        self.console.print(f"The current session is saved as {save_name}", style="bold green")

    def _preload_session(self) -> Optional[Dict]:
        """从保存目录选择并预加载会话数据。"""
        if not confirm("Do you want to continue from previous session?"):
            return None

        project_root = Path(__file__).resolve().parent.parent
        save_dir_path = project_root / self.save_dir
        
        # 过滤可能的非文件项，增加容错
        filenames = [f for f in save_dir_path.glob('*') if f.is_file()]

        if not filenames:
            print("No previous session found. Please start a new session.")
            return None

        print("Please select the previous session by its index (integer):")
        for i, filename in enumerate(filenames):
            print(f"{i}. {filename.name}")

        try:
            index = int(input("Please key in your option (integer): "))
            if 0 <= index < len(filenames):
                selected_file = filenames[index]
                print(f"You selected: {selected_file.name}")
                with open(selected_file, "r", encoding='utf-8') as f:
                    return json.load(f)
            else:
                print("Index out of range.")
        except (ValueError, IndexError):
            print("Invalid input.")
        
        print("Will start a new session.")
        return None


    def _feed_init_prompts(self):
        """
        触发初始对话流程：收集信息 -> 推理构建任务树 -> 生成任务细节。
        """
        # 1. 获取用户输入
        init_description = prompt_ask(
            "Please describe the incident response task, including the system, task, incident type, etc.\n1 > ",
            multiline=True,
        )
        self.log_conversation("user", init_description)    # 记录用户提供的任务描述
        self.task_log["task description"] = init_description    # 保存任务描述到任务日志中

        # 2. 推理阶段：构建初始 IRT
        prefixed_desc = f"{self.prompts.task_description}{init_description}"
        # 任务描述 (生成 IRT) + 用户提供的信息

        with self.console.status(
            "[bold #94C9B7] Constructing Initial Incident Response Tree..."
        ) as status:
            # 推理会话处理 prefixed_desc
            planner_output = self.planner_agent.send_message(
                prefixed_desc, self.planner_session_id
            )
            _task_selection = self.planner_agent.send_message(
                self.prompts.task_selection, self.planner_session_id
            )
            planner_output = (
                f"{planner_output}\n"
                f"{'-' * 100}\n"
                f"{_task_selection}"
            )

        # 3. 生成阶段：基于推理结果生成指令
        # 注意，生成会话不用于任务初始化。
        with self.console.status("[bold #94C9B7] Generating Initial Task") as status:
            _generation_response = self.generator_agent.send_message(
                f"{self.prompts.todo_to_command}{planner_output}",
                self.generator_session_id,
            )
            # todo RAG

        # 4. 输出展示
        response = f"{planner_output}\n{_generation_response}"
        self.console.print("IRCopilot output: ", style="bold #94C9B7")
        self.console.print(response)
        self.log_conversation("IRCopilot", f"IRCopilot output: {response}")

    def initialize(self, previous_session_ids: Optional[Dict] = None, run_init_prompts: bool = True):
        """
        初始化核心会话（生成、推理、反思），支持加载旧会话或创建新会话。
        """
        # 定义三个会话：生成会话、推理会话和解析会话
        if previous_session_ids is not None and self.useAPI is False:
            self.generator_session_id = previous_session_ids.get("generator", None) or previous_session_ids.get("test_generation", None)
            self.planner_session_id = previous_session_ids.get("planner", None)
            self.reflector_session_id = previous_session_ids.get("reflector", None) or previous_session_ids.get("reflection", None)

            # 调试输出会话的ID
            print(f"Previous session ids: {str(previous_session_ids)}")
            print(f"Generator session id: {str(self.generator_session_id)}")
            print(f"Planner session id: {str(self.planner_session_id)}")
            print(f"Reflector session id: {str(self.reflector_session_id)}")

            print("-----------------")

            # 打印调试信息
            self.task_log = previous_session_ids.get("task_log", {})
            self.console.print(f"Task log: {str(self.task_log)}", style="bold green")
            print("You may use 'discuss' to remind the task.")

            # 验证会话有效性
            if any(sid is None for sid in [self.generator_session_id, self.planner_session_id, self.reflector_session_id]):
                self.console.print("[bold red] Error: Previous session IDs are incomplete/invalid. Starting new sessions.")
                self.initialize(previous_session_ids=None) # 递归调用以重新初始化
            return

        with self.console.status(
            "[bold #94C9B7] Initialize LLM Sessions..."
        ) as status:
            try:
                # 启动生成会话
                _, self.generator_session_id = \
                    self.generator_agent.send_new_message(self.prompts.Generator_init)
                self.console.print(f"Generator session : {self.generator_session_id}", style="bold #94C9B7")

                # 启动推理会话
                _, self.planner_session_id = \
                    self.planner_agent.send_new_message(self.prompts.Planner_init)
                self.console.print(f"Planner session : {self.planner_session_id}", style="bold #94C9B7")

                # 启动反思会话 (通常包含一个 bad example 的预热)
                _, self.reflector_session_id = \
                    self.reflector_agent.send_new_message(self.prompts.Reflector_init)
                self.reflector_agent.send_message(self.prompts.bad_example, self.reflector_session_id)
                self.console.print(f"Reflector session: {self.reflector_session_id}", style="bold #94C9B7")
            
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
        if run_init_prompts:
            self._feed_init_prompts()

    def planner_handler(self, text: str) -> Tuple[str, str]:
        """处理推理请求：更新 IRT 并选择任务。"""
        # if len(text) > self.parsing_char_window:
        #     # 如果文本长度超过解析字符窗口，调用input_parsing_handler()处理文本
        #     text = self.input_parsing_handler(text)

        # 1. 更新IRT
        _updated_irt = self.planner_agent.send_message(
            f"{self.prompts.process_results}{text}", self.planner_session_id
        )

        # 2. 验证IRT是否正确，反思并修订IRT

        # 3. 选择最优任务
        selected_task = self.planner_agent.send_message(
            self.prompts.task_selection, self.planner_session_id
        )

        # 4. 组合结果
        full_response = (
            f"{_updated_irt}\n"
            f"{'-' * 100}\n"
            f"{selected_task}"
        )

        self.log_conversation("planner", full_response)
        return full_response, selected_task

    def generator_handler(self, text: str) -> str:
        """处理生成请求。"""
        # input_handler: more/tdo
        response = self.generator_agent.send_message(
            text, self.generator_session_id
        )
        # 记录对话
        self.log_conversation("generator", response)
        return response
    

    def local_input_handler(self) -> str:
        """
        处理本地辅助任务 (Help, Discuss, Deliberate)。
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
            user_msg = "Please share your findings/questions with IRCopilot.(End with <ctrl + right>)"
            self.console.print(user_msg)
            self.log_conversation("IRCopilot", user_msg)
            
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            
            # (2) 将信息传递给生成会话
            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                # todo:RAG
                local_task_response = self.generator_handler(
                    f"{self.prompts.local_task_prefix}{user_input}"
                )

            # (3) 显示结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(f"{local_task_response}\n", style="yellow")
            self.log_conversation("IRCopilot", local_task_response)

        # generation: 尝试识别解决问题的所有潜在方法
        elif local_request_option == "deliberate":  # 解决问题
            # (1) 如果用户选择头脑风暴，请求多行输入
            user_msg = "Please share your concerns and questions with IRCopilot.(End with <ctrl + enter>)"
            self.console.print(user_msg)
            self.log_conversation("IRCopilot", user_msg)
            
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            
            # (2) 将信息传递给生成会话
            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                # todo:RAG
                local_task_response = self.generator_handler(
                    f"{self.prompts.local_task_brainstorm}{user_input}"
                )

            # (3) 显示结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(f"{local_task_response}\n", style="yellow")
            self.log_conversation("IRCopilot", local_task_response)

        elif local_request_option == "exit":
            # 如果用户选择继续主任务
            self.console.print("Exit the local task and continue the main task.")
            self.log_conversation("IRCopilot", "Exit the local task and continue the main task.")
            return "exit"

        return local_task_response
    
    def _ui_interaction_wrapper(self, prompt_msg: str, agent_func, *args) -> Tuple[str, str]:
        """封装通用的 UI 交互流程 (提示->输入->思考->打印)。"""
        self.console.print(prompt_msg)
        self.log_conversation("IRCopilot", prompt_msg)
        
        user_input = prompt_ask("1 > ", multiline=True)
        self.log_conversation("user", user_input)

        response = ""
        with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
            # 这里的 agent_func 可以是 self.planner_agent.send_message 或其他 handler
            response = agent_func(user_input, *args)
        
        return response, user_input
    
    def input_handler(self) -> str:
        """
        核心输入处理循环：根据用户选择的主任务选项分发逻辑。
        """
        self.chat_count += 1
        request_option = task_entry(completer_type='main')
        self.log_conversation("user", request_option)

        # 会话保活检查 (非 API 模式)
        # if not self.useAPI:
        #     conversation_history = self.parsingAgent.get_conversation_history()
        #     while conversation_history is None:
        #         self.refresh_session()
        #         conversation_history = self.parsingAgent.get_conversation_history()

        response = ""

        # === 分支逻辑 ===

        if request_option == "chat_with_Planner":
            self.console.print("Please send your thoughts to Planner. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send your thoughts to Planner.")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", thoughts)

            with self.console.status("[bold #94C9B7] IRCopilot thinking...") as status:
                response = self.planner_agent.send_message(thoughts, self.planner_session_id)
                self.planner_response = response

            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(response + "\n", style="green")
            self.log_conversation("IRCopilot", response)

        # 用户->解析->推理->生成
        elif request_option == "next":
            self.console.print("Your input: (End with <ctrl + right>)", style="bold green")
            user_input = prompt_ask("1 > ", multiline=True)     # 获取用户的详细输入。
            self.log_conversation("user", user_input)
            # self.log_conversation("user", f"Source: {options[int(source)]}\n{user_input}")

            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                # (1) 使用input_parsing_handler()解析用户输入
                # parsed_input = self.input_parsing_handler(
                #     user_input, source=options[int(source)]
                # )
                # (2) 将 解析后的信息 传递给 推理会话，获取基于 解析结果的推理响应。
                response, self.selected_task = self.planner_handler(user_input)
                self.planner_response = response

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
                _updated_irt = self.planner_agent.send_message(
                    f"{self.prompts.analysis_results}{user_input}", self.planner_session_id
                )

                selected_task = self.planner_agent.send_message(
                    self.prompts.task_selection, self.planner_session_id
                )

                response = f"{_updated_irt}\n{'-'*100}\n{selected_task}"
                self.irt_and_task_history.append(response)  # 存储系统响应

                # 可以再传递给generate
                self.planner_response = response

            # 打印结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(f"{response}\n", style="green")
            self.log_conversation("IRCopilot", response)

        elif request_option == 'analyse_files':
            self.console.print("Please send the files that need to be reviewed to IRCopilot. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send the files that need to be reviewed to IRCopilot.")
            user_input = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", user_input)
            self.action_history.append(user_input)  # 存储用户操作

            with self.console.status("[bold #94C9B7] IRCopilot Thinking...") as status:
                _updated_irt = self.planner_agent.send_message(
                    f"{self.prompts.analysis_files}{user_input}", self.planner_session_id
                )

                selected_task = self.planner_agent.send_message(
                    self.prompts.task_selection, self.planner_session_id
                )

                response = f"{_updated_irt}\n{'-'*100}\n{selected_task}"
                self.irt_and_task_history.append(response)  # 存储系统响应

                # 可以再传递给generate
                self.planner_response = response

            # (3) 打印结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(f"{response}\n", style="green")
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
                response,self.selected_task = self.planner_handler(f"{self.prompts.discussion}{user_input}")
                # 测试人员提供了以下思考供您参考，请给出您的意见，并在必要时更新任务。+ user_input

                # 可以再传递给generate
                self.planner_response = response

            # (3) 打印结果
            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(f"{response}\n", style="yellow")
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
                planner_resp, self.selected_task = self.planner_handler(f"{self.prompts.regenerate}{user_input}")

                # 重新生成指导
                message = f"{self.prompts.todo_to_command}\n{planner_resp}"
                generation_resp = self.generator_handler(message)

            # (3) 打印结果
            response = planner_resp
            self.console.print(f"Based on the analysis, the following tasks are recommended: \n{response}\n",
                               style="bold green")  # reason->任务树

            self.console.print(f"You can follow the instructions below to complete the tasks. \n{generation_resp}\n",
                               style="bold green")  # generation->指导

            
            self.log_conversation(
                "IRCopilot",
                f"Based on the analysis, the following tasks are recommended:{response}\n"
                "You can follow the instructions below to complete the tasks."
                f"{generation_resp}"
            )

        elif request_option == "chat_with_Generator":
            self.console.print("Please send your thoughts to Generator. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send your thoughts to Generator.")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", thoughts)

            with self.console.status("[bold #94C9B7] IRCopilot thinking...") as status:
                response = self.generator_agent.send_message(thoughts, self.generator_session_id)
                self.generator_response = response

            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(f"{response}\n", style="green")
            self.log_conversation("IRCopilot", response)

        elif request_option == "generate_commands":
            if not hasattr(self, "planner_response"):
                msg = "You have not initialized the task yet. Please perform the basic testing following `next` option."
                self.console.print(msg, style="bold red")
                self.log_conversation("IRCopilot", msg)
                return msg

            # (2) 开始本地任务生成
            # (2.1) 请求推理会话分析当前情况，并解释任务
            self.console.print("IRCopilot will generate details", style="bold #94C9B7")
            self.log_conversation( "IRCopilot", "IRCopilot will generate details.")

            # (2.2) 将子任务传递给测试生成会话
            with self.console.status("[bold #94C9B7] IRCopilot Generating...") as status:
                # todo:# 可以在此处集成 RAG 或 Extractor
                # # 提取推理结果的关键词
                # question = self.extractorAgent.send_message(
                #     self.prompts.extract_keyword + self.planner_response, self.extractor_session_id
                # )
                # # 关键词->RAG->prompt
                # rag_prompt = rag2prompt(question=question)
                # # 根绝RAG检索的背景生成任务、指导、或是命令

                self.generator_response = self.generator_handler(
                    self.planner_response
                )

                # 对生成会话进行评估反思循环？
                # generation_response = self.reflect_cmd(generation_response)

            # 打印
            self.console.print(f"Below are the further details.\n{self.generator_response}\n",style="bold green")
            response = self.generator_response    # 生成会话的结果
            self.log_conversation("IRCopilot", response)

        elif request_option == "sub-task":
            if not hasattr(self, "generator_response"):
                msg = "You haven't initialized the generator yet. Please perform the basic testing following `generate` option."
                self.console.print(msg, style="bold red")
                self.log_conversation("IRCopilot", msg)
                return msg

            while True:
                # 触发子任务生成的逻辑
                _local_init_response = self.generator_handler(
                    self.prompts.local_task_init  # 生成会话 忽略之前的信息
                )
                local_resp = self.local_input_handler()
                if local_resp == "exit":
                    break
            # todo：这里子任务的response有待商榷
            response = local_resp
            # response = "Sub-task session ended."

        elif request_option == "chat_with_Reflector":
            self.console.print("Please send your thoughts to Reflector. (End with <ctrl + right>)")
            self.log_conversation("IRCopilot", "Please send your thoughts to Reflector.")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.log_conversation("user", thoughts)

            with self.console.status("[bold #94C9B7] IRCopilot thinking...") as status:
                response = self.reflector_agent.send_message(thoughts, self.reflector_session_id)
                self.reflector_response = response

            self.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.console.print(f"{response}\n", style="green")
            self.log_conversation("IRCopilot", response)

        # 对命令的执行的结果进行反思
        elif request_option == "reflect":
            try:
                self.console.print("Please send your thoughts to LLM for reflection. (End with <ctrl + right>)")
                self.log_conversation("IRCopilot", "Please send your thoughts to LLM for reflection.")
                thoughts = prompt_ask("1 > ", multiline=True)
                self.log_conversation("user", thoughts)

                # 定义k值，表示希望获取的历史记录的数量
                self.console.print("Enter the number of recent conversations to include in reflection:")
                user_k = prompt_ask("num > ")

                try:
                    k = int(user_k) if user_k.strip() else 1
                except ValueError:
                    print("Invalid input. UUsing default value 1.")
                    k = 1

                # 获取最近的 k 个决策或者任务
                recent_tasks = "\n\n".join(
                    self.irt_and_task_history[-k:] if len(self.irt_and_task_history) >= k else self.irt_and_task_history)
                # 获取最近的 k 个执行结果
                recent_actions = "\n\n".join(
                    self.action_history[-k:] if len(self.action_history) >= k else self.action_history)

                # 推理(IRT)->决策(Task)->生成(cmd)->执行(cmd)->反思
                with self.console.status("[bold #94C9B7] IRCopilot Reflecting...") as status:
                    reflect_input = (
                        f"{self.prompts.reflect_input}"
                        f"Your previously designed Incident Response Tree (IRT) and the decisions you made based on the IRT: {recent_tasks}\n\n"
                        f"Results of the incident response steps: \n{recent_actions}\n\n"
                        f"Analyst's thoughts or your previous reflections (can be empty): \n{thoughts}"
                    )
                    response = self.reflector_agent.send_message(reflect_input, self.reflector_session_id)
                    self.planner_response = response

                self.console.print("IRCopilot:\n", style="bold #94C9B7")
                self.console.print(f"{response}\n", style="green")
                self.log_conversation("IRCopilot", response)

            except Exception as e:
                self.console.print(f"[red]An error occurred during reflection: {e}[/red]")
                self.log_conversation("IRCopilot", f"An error occurred during reflection: {e}")
                response = f"Error: {e}"

        elif request_option == "exit_IRCopilot":
            self.console.print("Thank you for using IRCopilot!", style="bold green")
            self.log_conversation("IRCopilot", "Thank you for using IRCopilot!")
            response = False  # 返回 False 结束循环

        else:
            msg = "Please key in the correct options."
            self.console.print(msg, style="bold red")
            self.log_conversation("IRCopilot", msg)
            response = msg

        return response


    def main(self):
        """
        IRCopilot 主程序入口。
        """
        # 1. 初始化
        loaded_ids = self._preload_session()      
        self.initialize(previous_session_ids=loaded_ids)

        # 2. 主循环
        while True:
            try:
                result = self.input_handler()  # 处理用户输入
                self.console.print(
                    "-" * 41, style="bold white"
                )

                # input_handler 返回 False 时退出
                if result is False:
                    break
            except Exception as e:
                self.log_conversation("exception", str(e))
                self.console.print(f"Exception: {str(e)}", style="bold red")
                exc_type, exc_obj, exc_tb = sys.exc_info()  # 捕获异常信息
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]  # 获取异常发生的文件名
                self.console.print("Exception details are below.", style="bold red")
                # self.console.print(exc_type, fname, exc_tb.tb_lineno)  # 提供了错误的基本信息
                self.console.print(traceback.format_exc(), style="bold red") # 提供了更详细的调用栈信息
                break

        # 3. 退出前保存日志和会话
        try:
            log_name = f"IRCopilot_log_{time.time()}.txt"
            # 使用 pathlib 
            log_path = self.log_dir / log_name
            # log_path = os.path.join(self.log_dir, log_name)
            with open(log_path, "w", encoding='utf-8') as f:
                json.dump(self.history, f, indent=4)
            
            self.save_session()
        except Exception as e:
            self.console.print(f"Error saving session/logs: {e}", style="bold red")



if __name__ == "__main__":
    IRCopilot = IRCopilot()
    IRCopilot.main()
