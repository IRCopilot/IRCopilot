#!/usr/bin/env python
"""
url: https://github.com/prompt-toolkit/python-prompt-toolkit/tree/master/examples/prompts/auto-completion
演示自定义补全类的使用和通过传递格式化文本对象
到 Completion 的 "display" 和 "display_meta" 参数
来独立样式化补全的可能性。
"""
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import CompleteStyle, prompt


class BaseTaskCompleter(Completer):
    tasks = []
    task_meta = {}

    # 自动补全
    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()
        for task in self.tasks:
            if task.startswith(word):
                yield Completion(
                    task,
                    start_position=-len(word),
                    display=task,
                    display_meta=self.task_meta.get(task),
                )


class localTaskCompleter(BaseTaskCompleter):
    tasks = [
        "discuss",
        "deliberate",
        "help",
        "exit",
    ]

    task_meta = {
        "discuss": HTML("Discuss with <b>IRCopilot</b> about the sub-task."),
        "deliberate": HTML("Deliberate on solutions for the sub-task."),
        "help": HTML("Show the help page."),
        "exit": HTML("Exit from sub-task."),
    }

    task_details = """
    - discuss: Discuss with IRCopilot about this sub-task.
    - deliberate: Deliberate on solutions for the sub-task.
    - help: Show the help page.
    - exit: Exit from sub-task."""


class mainTaskCompleter(BaseTaskCompleter):
    tasks = [
        "chat_with_Planner",
        "next",
        "analyse_results",
        "analyse_files",
        "discuss_with_IRCopilot",
        "regenerate_the_IRT",
        "chat_with_Generator",
        "generate_commands",
        "sub-task",
        "chat_with_Reflector",
        "reflect",
        "help",
        "exit_IRCopilot",
    ]

    task_meta = {
        "chat_with_Planner": HTML("Chat with Planner."),
        "next": HTML("Go to the next step."),
        "analyse_results": HTML("Analysis results."),
        "analyse_files": HTML("Analysis files."),
        "discuss_with_IRCopilot": HTML("Discuss with <b>IRCopilot</b>."),
        "regenerate_the_IRT": HTML("Regenerate the IRT."),
        "chat_with_Generator": HTML("Chat with Generator"),
        "generate_commands": HTML("Generate commands"),
        "sub-task": HTML("Focus on the sub-task."),
        "chat_with_Reflector":HTML("Chat with Reflector"),
        "reflect": HTML("Reflect on the results of the execution."),
        "help": HTML("Show the help page."),
        "exit_IRCopilot": HTML("End the current session."),
    }

    task_details = """
 - chat_with_Planner: Chat with Planner.
 - next: Continue to the next step by inputting the test results.
 - analyse_results: Analysis results.
 - analyse_files: Analysis files. 
 - discuss_with_IRCopilot: Ask IRCopilot for the task list and what to do next.
 - regenerate_the_IRT: Regenerate the IRT. You can ask for help, discuss the task, or give any feedbacks.
 - chat_with_Generator: Chat with Generator
 - generate_commands: Explain the previous given task with more details.
 - sub-task: Focus on the sub-task.
 - chat_with_Reflector: Chat with Reflector
 - reflect: Reflect on the results of the execution.
 - help: Show this help page.
 - exit_IRCopilot: End the current session."""


def task_entry(completer_type, text="> "):
    completers = {
        'main': mainTaskCompleter(),
        'local': localTaskCompleter()
    }

    completer = completers.get(completer_type)

    while True:
        result = prompt(text, completer=completer)
        if result not in completer.tasks:
            print("Invalid task, try again.")
        else:
            return result


if __name__ == "__main__":
    task_entry(completer_type='main')
