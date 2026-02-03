import argparse
import sys

from IRCopilot.utils.IRCopilot import IRCopilot
from IRCopilot.utils.prompt_select import prompt_ask
from IRCopilot.langgraph.graph import (
    IRCopilotGraphRuntime,
    IRCopilotState,
    build_graph_with_runtime,
)


def main():
    parser = argparse.ArgumentParser(description="IRCopilot")

    # 解析器参数
    # 0. 日志目录
    parser.add_argument(
        "--log_dir",
        type=str,
        default="logs",
        help="path to the log directory, where conversations will be stored",
    )

    # 1. 推理模型
    parser.add_argument(
        "--reasoning_model",
        type=str,
        default="gpt-4",
        help="reasoning models are responsible for higher-level cognitive tasks, choose 'gpt-4' or 'gpt-4-turbo'",
    )

    # 2. 解析模型
    parser.add_argument(
        "--parsing_model",
        type=str,
        default="gpt-4",
        help="parsing models deal with the structural and grammatical aspects of language, choose 'gpt-4-turbo' or 'gpt-3.5-turbo-16k'",
    )

    # 已弃用：仅用于测试时使用cookie设为False
    parser.add_argument(
        "--useAPI",
        action="store_true",
        default=True,
        help="deprecated: set to False only for testing if using cookie",
    )
    parser.add_argument(
        "--use_langgraph",
        action="store_true",
        default=False,
        help="run LangGraph loop instead of legacy CLI",
    )

    args = parser.parse_args()

    IRCopilotHandler = IRCopilot(
        reasoning_model=args.reasoning_model,
        parsing_model=args.parsing_model,
        useAPI=args.useAPI,
        log_dir=args.log_dir,
    )

    if args.use_langgraph:
        loaded_ids = IRCopilotHandler._preload_session()
        IRCopilotHandler.initialize(previous_session_ids=loaded_ids, run_init_prompts=False)
        init_description = prompt_ask(
            "Please describe the incident response task, including the system, task, incident type, etc.\n1 > ",
            multiline=True,
        )
        IRCopilotHandler.log_conversation("user", init_description)
        IRCopilotHandler.task_log["task description"] = init_description
        runtime = IRCopilotGraphRuntime(IRCopilotHandler)
        graph = build_graph_with_runtime(runtime)
        graph.invoke(
            IRCopilotState(user_input=init_description),
            config={"recursion_limit": 1000},
        )
    else:
        IRCopilotHandler.main()


if __name__ == "__main__":
    main()
