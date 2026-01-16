# -*- coding: utf-8 -*-
import asyncio
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
        async_: bool = False
) -> Any:
    """
    创建一个带有单选列表的交互式用户界面。

    Args:
        title: 界面顶部显示的标题。
        values: 选项列表，格式为 [(value, label), ...]。
        style: 应用于界面的样式类或字典。
        async_: 是否异步运行。

    Returns:
        Any: 用户选中的值。如果 async_ 为 True，返回 Future 对象。
    """
    values = values or []
    bindings = KeyBindings()

    @bindings.add("c-z")
    def _exit(event):
        """Ctrl+Z 退出程序"""
        event.app.exit()

    @bindings.add("c-right")
    def _submit(event):
        """Ctrl+Right 确认选择并返回"""
        event.app.exit(result=radio_list.current_value)

    radio_list = RadioList(values)

    application = Application(
        layout=Layout(HSplit([Label(title), radio_list])),
        key_bindings=merge_key_bindings([load_key_bindings(), bindings]),
        mouse_support=True,
        style=style,
        full_screen=False,
    )

    return application.run_async() if async_ else application.run()


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