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
        "--llm_model",
        type=str,
        default="gpt-5.1-2025-11-13",
        help="primary LLM used across planner/generator/reflector/analyst",
    )

    # 2. 解析模型（当前未使用，保留注释以备将来恢复）
    # parser.add_argument(
    #     "--parsing_model",
    #     type=str,
    #     default="gpt-5.1-2025-11-13",
    #     help="parsing models deal with the structural and grammatical aspects of language",
    # )

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
        llm_model=args.llm_model,
        # parsing_model=args.parsing_model,
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
        state = IRCopilotState(user_input=init_description)
        def _normalize_state(latest: object, current: IRCopilotState) -> IRCopilotState:
            if isinstance(latest, IRCopilotState):
                return latest
            if not isinstance(latest, dict):
                return current

            # If stream yields node-keyed outputs, pick nested state/dict.
            for value in latest.values():
                if isinstance(value, IRCopilotState):
                    return value
                if isinstance(value, dict):
                    nested = value
                    if any(hasattr(current, key) for key in nested.keys()):
                        merged = IRCopilotState(**current.__dict__)
                        for key, val in nested.items():
                            if hasattr(merged, key):
                                setattr(merged, key, val)
                        return merged

            # Fall back to overlaying updates on the current state.
            merged = IRCopilotState(**current.__dict__)
            for key, value in latest.items():
                if hasattr(merged, key):
                    setattr(merged, key, value)
            return merged

        while True:
            for latest_state in graph.stream(
                state,
                stream_mode="values",
                config={"recursion_limit": 1000},
            ):
                state = _normalize_state(latest_state, state)
                if state.exit_requested:
                    break
                if state.last_node == "ir_results_input" and not state.next_node:
                    break

            if state.exit_requested:
                break
    else:
        IRCopilotHandler.main()


if __name__ == "__main__":
    main()
