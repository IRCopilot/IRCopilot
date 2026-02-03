from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from langgraph.graph import END, StateGraph
except Exception as exc:  # pragma: no cover - skeleton fallback
    END = "__end__"
    StateGraph = None

from IRCopilot.utils.prompt_select import prompt_ask, prompt_select


@dataclass
class IRCopilotState:
    # Core artifacts
    irt: Optional[str] = None
    selected_task: Optional[str] = None
    generator_output: Optional[str] = None
    reflection: Optional[str] = None
    analyst_summary: Optional[str] = None

    # Conversation / UI
    user_input: Optional[str] = None
    user_actions: List[str] = field(default_factory=list)
    chat_target: Optional[str] = None  # planner/generator/reflector/analyst/None
    exit_requested: bool = False

    # Routing hints
    last_node: Optional[str] = None
    next_node: Optional[str] = None
    skip_reflector: bool = False

    # Free-form scratchpad for tool data
    meta: Dict[str, Any] = field(default_factory=dict)


# ----------------------------
# Node stubs (replace with real logic)
# ----------------------------
def planner_node(state: IRCopilotState) -> IRCopilotState:
    # Placeholder for standalone usage (no injected runtime).
    state.last_node = "planner"
    return state


def generator_node(state: IRCopilotState) -> IRCopilotState:
    # Placeholder for standalone usage (no injected runtime).
    state.last_node = "generator"
    return state


def reflector_node(state: IRCopilotState) -> IRCopilotState:
    # Placeholder for standalone usage (no injected runtime).
    state.last_node = "reflector"
    return state


def analyst_node(state: IRCopilotState) -> IRCopilotState:
    # Placeholder for standalone usage (no injected runtime).
    state.last_node = "analyst"
    return state


def human_input_node(state: IRCopilotState) -> IRCopilotState:
    # Placeholder for standalone usage (no injected runtime).
    state.last_node = "human_input"
    return state


def chat_node(state: IRCopilotState) -> IRCopilotState:
    # Placeholder for standalone usage (no injected runtime).
    state.last_node = "chat"
    return state


def exit_node(state: IRCopilotState) -> IRCopilotState:
    state.last_node = "exit"
    return state


# ----------------------------
# Routers / guards
# ----------------------------
def route_from_planner(state: IRCopilotState) -> str:
    if state.exit_requested:
        return "exit"
    if state.chat_target == "planner":
        return "chat"
    return "generator"


def route_from_generator(state: IRCopilotState) -> str:
    if state.exit_requested:
        return "exit"
    if state.chat_target == "generator":
        return "chat"
    return "human_input"


def route_from_reflector(state: IRCopilotState) -> str:
    if state.exit_requested:
        return "exit"
    if state.chat_target == "reflector":
        return "chat"
    return "analyst"


def route_from_analyst(state: IRCopilotState) -> str:
    if state.exit_requested:
        return "exit"
    if state.chat_target == "analyst":
        return "chat"
    return "planner"


def route_from_chat(state: IRCopilotState) -> str:
    # After chat, continue from last node or default to planner
    if state.exit_requested:
        return "exit"
    if state.next_node:
        return state.next_node
    return state.next_node or "planner"


def route_from_human_input(state: IRCopilotState) -> str:
    if state.exit_requested:
        return "exit"
    if state.chat_target:
        return "chat"
    if state.next_node:
        return state.next_node
    if state.skip_reflector:
        return "analyst"
    return "reflector"


# ----------------------------
# Graph builder
# ----------------------------
def build_graph() -> Any:
    if StateGraph is None:
        raise RuntimeError("langgraph is not available; install langgraph to use this graph.")

    graph = StateGraph(IRCopilotState)

    graph.add_node("planner", planner_node)
    graph.add_node("generator", generator_node)
    graph.add_node("ir_results_input", human_input_node)
    graph.add_node("reflector", reflector_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("chat", chat_node)
    graph.add_node("exit", exit_node)

    # Edges per your specified order: planner -> generator -> reflector -> analyst (loop)
    graph.add_conditional_edges(
        "planner",
        route_from_planner,
        {
            "generator": "generator",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "generator",
        route_from_generator,
        {
            "ir_results_input": "ir_results_input",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_edge("ir_results_input", "reflector")
    graph.add_conditional_edges(
        "reflector",
        route_from_reflector,
        {
            "analyst": "analyst",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "analyst",
        route_from_analyst,
        {
            "planner": "planner",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "chat",
        route_from_chat,
        {
            "planner": "planner",
            "generator": "generator",
            "ir_results_input": "ir_results_input",
            "reflector": "reflector",
            "analyst": "analyst",
            "exit": "exit",
        },
    )

    graph.set_entry_point("planner")
    graph.add_edge("exit", END)

    return graph.compile()


class IRCopilotGraphRuntime:
    """
    Dependency-injected runtime wrapper that binds LangGraph nodes to an existing
    IRCopilot instance. This keeps graph.py decoupled from IRCopilot internals.
    """

    def __init__(self, ircopilot: Any):
        self.ircopilot = ircopilot

    def _gate_after_node(
        self,
        state: IRCopilotState,
        node_name: str,
        next_node: str,
        allow_chat: bool = True,
    ) -> None:
        self.ircopilot.console.print(
            f"[SYSTEM] {node_name}: choose next action",
            style="bold #94C9B7",
        )
        values = [("continue", f"Continue to {next_node}")]
        if allow_chat:
            values.append(("chat", f"Chat with {node_name.title()}"))
        values.append(("exit", "Exit IRCopilot"))
        request = prompt_select(
            title=f"> {node_name}: next action (Confirm with Ctrl+Right): ",
            values=values,
        )

        if request == "exit":
            state.exit_requested = True
            state.chat_target = None
            self.ircopilot.console.print("Thank you for using IRCopilot!", style="bold green")
        elif request == "chat":
            state.chat_target = node_name
            state.next_node = next_node
        else:
            state.chat_target = None
            state.next_node = next_node

    def planner_node(self, state: IRCopilotState) -> IRCopilotState:
        # Planner only selects the next task based on the current IRT.
        decision = self.ircopilot.reasoningAgent.send_message(
            self.ircopilot.prompts.task_selection,
            self.ircopilot.test_reasoning_session_id,
        )
        state.selected_task = decision
        self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
        self.ircopilot.console.print(f"{decision}\n", style="green")
        self.ircopilot.log_conversation("IRCopilot", decision)
        state.last_node = "planner"
        self._gate_after_node(state, "planner", "generator", allow_chat=True)
        return state

    def generator_node(self, state: IRCopilotState) -> IRCopilotState:
        # Use IRT+decision to generate commands/guidance.
        if state.irt and state.selected_task:
            full_reasoning_output = (
                f"{state.irt}\n"
                f"{'-' * 100}\n"
                f"{state.selected_task}"
            )
            response = self.ircopilot.test_generation_handler(
                f"{self.ircopilot.prompts.todo_to_command}{full_reasoning_output}"
            )
            state.generator_output = response
            self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.ircopilot.console.print(f"{response}\n", style="green")
            self.ircopilot.log_conversation("IRCopilot", response)
        state.last_node = "generator"
        self._gate_after_node(state, "generator", "ir_results_input", allow_chat=True)
        return state

    def reflector_node(self, state: IRCopilotState) -> IRCopilotState:
        if state.skip_reflector:
            state.last_node = "reflector"
            return state
        # Build reflect input from existing histories if present.
        recent_tasks = "\n\n".join(self.ircopilot.irt_and_task_history[-1:]) if self.ircopilot.irt_and_task_history else ""
        recent_actions = "\n\n".join(self.ircopilot.action_history[-1:]) if self.ircopilot.action_history else ""
        reflect_input = (
            f"{self.ircopilot.prompts.reflect_input}"
            f"Your previously designed Incident Response Tree (IRT) and the decisions you made based on the IRT: {recent_tasks}\n\n"
            f"Results of the incident response steps: \n{recent_actions}\n\n"
            f"Analyst's thoughts or your previous reflections (can be empty): \n{state.user_input or ''}"
        )
        response = self.ircopilot.reflectionAgent.send_message(
            reflect_input, self.ircopilot.reflection_session_id
        )
        state.reflection = response
        self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
        self.ircopilot.console.print(f"{response}\n", style="green")
        self.ircopilot.log_conversation("IRCopilot", response)
        state.last_node = "reflector"
        self._gate_after_node(state, "reflector", "analyst", allow_chat=True)
        return state

    def analyst_node(self, state: IRCopilotState) -> IRCopilotState:
        # Analyst only analyzes and updates IRT; no task selection here.
        text = state.user_input or ""
        if text:
            if state.irt is None:
                response = self.ircopilot.reasoningAgent.send_message(
                    f"{self.ircopilot.prompts.task_description}{text}",
                    self.ircopilot.test_reasoning_session_id,
                )
            else:
                response = self.ircopilot.reasoningAgent.send_message(
                    f"{self.ircopilot.prompts.analysis_results}{text}",
                    self.ircopilot.test_reasoning_session_id,
                )
            state.irt = response
            state.analyst_summary = response
            self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.ircopilot.console.print(f"{response}\n", style="green")
            self.ircopilot.log_conversation("IRCopilot", response)
        state.last_node = "analyst"
        self._gate_after_node(state, "analyst", "planner", allow_chat=True)
        return state

    def human_input_node(self, state: IRCopilotState) -> IRCopilotState:
        # Collect execution results from user.
        prompt = "Please send the results of the guidance/command execution. (End with <ctrl + right>)"
        self.ircopilot.console.print("[SYSTEM] " + prompt, style="bold #94C9B7")
        self.ircopilot.log_conversation("IRCopilot", prompt)
        self.ircopilot.console.print("[YOU] Input:", style="bold yellow")
        user_input = prompt_ask("1 > ", multiline=True)
        self.ircopilot.log_conversation("user", user_input)

        state.user_input = user_input
        if user_input:
            self.ircopilot.action_history.append(user_input)

        # Ask whether to run reflection.
        self.ircopilot.console.print(
            "[SYSTEM] Run reflection now?",
            style="bold #94C9B7",
        )
        reflect_request = prompt_select(
            title="> Run reflection now? (Confirm with Ctrl+Right): ",
            values=[
                ("no", "No"),
                ("yes", "Yes"),
                ("exit", "Exit IRCopilot"),
            ],
        )

        if reflect_request == "exit":
            state.exit_requested = True
            state.chat_target = None
            state.skip_reflector = False
            self.ircopilot.console.print("Thank you for using IRCopilot!", style="bold green")
        elif reflect_request == "no":
            state.skip_reflector = True
        else:
            state.skip_reflector = False

        # Optional exit gate at this node as well (no chat for human_input).
        next_node = "analyst" if state.skip_reflector else "reflector"
        self._gate_after_node(state, "ir_results_input", next_node, allow_chat=False)

        state.last_node = "human_input"
        return state

    def chat_node(self, state: IRCopilotState) -> IRCopilotState:
        target = state.chat_target
        if not target:
            state.last_node = "chat"
            return state

        if target == "planner":
            msg = "Please send your thoughts to Planner. (End with <ctrl + right>)"
            self.ircopilot.console.print("[SYSTEM] " + msg, style="bold #94C9B7")
            self.ircopilot.log_conversation("IRCopilot", msg)
            self.ircopilot.console.print("[YOU] Input:", style="bold yellow")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.ircopilot.log_conversation("user", thoughts)
            response = self.ircopilot.reasoningAgent.send_message(
                thoughts, self.ircopilot.test_reasoning_session_id
            )
            self.ircopilot.log_conversation("IRCopilot", response)
            self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.ircopilot.console.print(f"{response}\n", style="green")
            state.meta["planner_chat"] = response

        elif target == "generator":
            msg = "Please send your thoughts to Generator. (End with <ctrl + right>)"
            self.ircopilot.console.print("[SYSTEM] " + msg, style="bold #94C9B7")
            self.ircopilot.log_conversation("IRCopilot", msg)
            self.ircopilot.console.print("[YOU] Input:", style="bold yellow")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.ircopilot.log_conversation("user", thoughts)
            response = self.ircopilot.generationAgent.send_message(
                thoughts, self.ircopilot.test_generation_session_id
            )
            self.ircopilot.log_conversation("IRCopilot", response)
            self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.ircopilot.console.print(f"{response}\n", style="green")
            state.meta["generator_chat"] = response

        elif target == "reflector":
            msg = "Please send your thoughts to Reflector. (End with <ctrl + right>)"
            self.ircopilot.console.print("[SYSTEM] " + msg, style="bold #94C9B7")
            self.ircopilot.log_conversation("IRCopilot", msg)
            self.ircopilot.console.print("[YOU] Input:", style="bold yellow")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.ircopilot.log_conversation("user", thoughts)
            response = self.ircopilot.reflectionAgent.send_message(
                thoughts, self.ircopilot.reflection_session_id
            )
            self.ircopilot.log_conversation("IRCopilot", response)
            self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.ircopilot.console.print(f"{response}\n", style="green")
            state.meta["reflector_chat"] = response

        elif target == "analyst":
            msg = "Please send your thoughts to Analyst. (End with <ctrl + right>)"
            self.ircopilot.console.print("[SYSTEM] " + msg, style="bold #94C9B7")
            self.ircopilot.log_conversation("IRCopilot", msg)
            self.ircopilot.console.print("[YOU] Input:", style="bold yellow")
            thoughts = prompt_ask("1 > ", multiline=True)
            self.ircopilot.log_conversation("user", thoughts)
            response = self.ircopilot.reasoningAgent.send_message(
                f"{self.ircopilot.prompts.analysis_results}{thoughts}",
                self.ircopilot.test_reasoning_session_id,
            )
            self.ircopilot.log_conversation("IRCopilot", response)
            self.ircopilot.console.print("IRCopilot:\n", style="bold #94C9B7")
            self.ircopilot.console.print(f"{response}\n", style="green")
            state.analyst_summary = response

        state.chat_target = None
        state.last_node = "chat"
        if state.next_node:
            self.ircopilot.console.print(
                f"[SYSTEM] Continue to {state.next_node}",
                style="bold #94C9B7",
            )
        return state


def build_graph_with_runtime(runtime: IRCopilotGraphRuntime) -> Any:
    """
    Build a graph wired to an IRCopilot instance.
    """
    if StateGraph is None:
        raise RuntimeError("langgraph is not available; install langgraph to use this graph.")

    graph = StateGraph(IRCopilotState)

    graph.add_node("planner", runtime.planner_node)
    graph.add_node("generator", runtime.generator_node)
    graph.add_node("ir_results_input", runtime.human_input_node)
    graph.add_node("reflector", runtime.reflector_node)
    graph.add_node("analyst", runtime.analyst_node)
    graph.add_node("chat", runtime.chat_node)
    graph.add_node("exit", exit_node)

    graph.add_conditional_edges(
        "planner",
        route_from_planner,
        {
            "generator": "generator",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "generator",
        route_from_generator,
        {
            "ir_results_input": "ir_results_input",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "ir_results_input",
        route_from_human_input,
        {
            "reflector": "reflector",
            "analyst": "analyst",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "reflector",
        route_from_reflector,
        {
            "analyst": "analyst",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "analyst",
        route_from_analyst,
        {
            "planner": "planner",
            "chat": "chat",
            "exit": "exit",
        },
    )
    graph.add_conditional_edges(
        "chat",
        route_from_chat,
        {
            "planner": "planner",
            "generator": "generator",
            "ir_results_input": "ir_results_input",
            "reflector": "reflector",
            "analyst": "analyst",
            "exit": "exit",
        },
    )

    graph.set_entry_point("analyst")
    graph.add_edge("exit", END)

    return graph.compile()


__all__ = [
    "IRCopilotState",
    "build_graph",
    "build_graph_with_runtime",
    "IRCopilotGraphRuntime",
    "planner_node",
    "generator_node",
    "reflector_node",
    "analyst_node",
    "human_input_node",
    "chat_node",
    "route_from_human_input",
]
