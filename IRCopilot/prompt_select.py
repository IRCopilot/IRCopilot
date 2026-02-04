# -*- coding: utf-8 -*-
import asyncio
import threading
from typing import List, Tuple, Any, Optional, Union

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.key_bindings import merge_key_bindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.widgets import Label, RadioList


def prompt_continuation(width: int, line_number: int, wrap_count: int) -> Union[str, HTML]:
    """
    自定义多行输入的续行符样式。

    在软换行（wrap）时显示箭头，新行时显示行号。
    """
    if wrap_count > 0:
        # 软换行（一行文字太长自动折行）：对齐并显示箭头
        return " " * (width - 3) + "  -> "

    # 硬换行（用户按回车）：显示行号
    text = f"{line_number + 1} > ".rjust(width)
    return HTML(f"<strong>{text}</strong>")


def prompt_select(
        title: str = "",
        values: Optional[List[Tuple[Any, Union[str, HTML]]]] = None,
        style: Optional[str] = None,
        async_: bool = False,
        fallback_seconds: Optional[float] = None,
        fallback_default: Optional[Any] = None,
) -> Any:
    """
    Create a single-choice prompt.
    """
    values = values or []
    bindings = KeyBindings()

    @bindings.add("c-z")
    def _exit(event):
        """Ctrl+Z ????"""
        event.app.exit()

    @bindings.add("c-right")
    def _submit(event):
        """Ctrl+Right ???????"""
        event.app.exit(result=radio_list.current_value)

    @bindings.add("enter")
    def _submit_enter(event):
        """Enter confirm selection and return"""
        event.app.exit(result=radio_list.current_value)

    @bindings.add("c-m")
    def _submit_ctrl_m(event):
        """Ctrl+M (Enter) confirm selection and return"""
        event.app.exit(result=radio_list.current_value)

    @bindings.add("c-j")
    def _submit_ctrl_j(event):
        """Ctrl+J confirm selection and return"""
        event.app.exit(result=radio_list.current_value)

    @bindings.add("space")
    def _submit_space(event):
        """Space confirm selection and return"""
        event.app.exit(result=radio_list.current_value)

    radio_list = RadioList(values)

    application = Application(
        layout=Layout(HSplit([Label(title), radio_list]), focused_element=radio_list),
        key_bindings=merge_key_bindings([bindings, load_key_bindings()]),
        mouse_support=True,
        style=style,
        full_screen=False,
    )

    if not async_:
        if fallback_seconds and fallback_seconds > 0:
            def _auto_submit():
                default_value = fallback_default if fallback_default is not None else radio_list.current_value
                try:
                    application.exit(result=default_value)
                except Exception:
                    pass
            try:
                application.call_later(fallback_seconds, _auto_submit)
            except Exception:
                timer = threading.Timer(fallback_seconds, _auto_submit)
                timer.daemon = True
                timer.start()
        return application.run()
    return application.run_async()


def prompt_ask(text: str, multiline: bool = True) -> str:
    """
    创建一个自定义的输入提示，支持单行或多行。

    按键说明:
        - Enter: 插入新行 (仅多行模式)
        - Ctrl + Right: 提交输入 (所有模式)

    Args:
        text: 提示文本。
        multiline: 是否开启多行模式。

    Returns:
        str: 用户输入的文本。
    """
    kb = KeyBindings()

    if multiline:
        @kb.add("enter")
        def _newline(event):
            """多行模式下，回车仅换行，不提交"""
            event.current_buffer.insert_text("\n")

    @kb.add("c-right")
    def _submit(event):
        """绑定 Ctrl+Right 为提交键"""
        event.current_buffer.validate_and_handle()

    return prompt(
        text,
        multiline=multiline,
        prompt_continuation=prompt_continuation,
        key_bindings=kb,
    )


if __name__ == "__main__":
    print("--- Test Case Start ---")

    # 修正提示文案：代码中绑定的是 c-right (Ctrl+Right)，而非 Shift
    print("Instruction: This is a multi-line input.")
    print("Press [Enter] to wrap lines, [Ctrl + Right Arrow] to submit.")

    answer = prompt_ask("Multiline input: ", multiline=True)
    print(f"You said: {answer}")

    print("-" * 30)

    # HTML 格式化选项测试
    request_option = prompt_select(
        title="> Please select an option (Use arrow keys, Confirm with Ctrl+Right): ",
        values=[
            ("1", HTML('<style fg="cyan">Input test results</style>')),
            ("2", HTML('<style fg="cyan">Ask for todos</style>')),
            ("3", HTML('<style fg="cyan">Discuss with irGPT</style>')),
            ("4", HTML('<style fg="red">Exit</style>')),
        ],
    )

    print(f"Result = {request_option}")
