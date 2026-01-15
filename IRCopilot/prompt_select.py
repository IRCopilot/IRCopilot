# 创建一个基于命令行界面的交互式程序,允许用户在命令行中进行多行输入、选择操作以及自定义的键盘快捷键
from __future__ import unicode_literals

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.widgets import Label, RadioList

# 处理多行输入的续行符
def prompt_continuation(width, line_number, wrap_count):
    """
    续行符：在软换行前显示行号和 '->'。
    注意我们可以从这里返回任何格式的文本。
    续行符不必与第一行前显示的提示符宽度相同，但在这个示例中我们选择对齐它们。
    这里接收的 `width` 输入代表提示符的宽度。
    """
    if wrap_count > 0:
        return " " * (width - 3) + "  -> "
    text = ("%i > " % (line_number + 1)).rjust(width)
    return HTML("<strong>{}</strong>".format(text))

# 创建一个带有单选列表的交互式用户命令行界面。
def prompt_select(title="", values=None, style=None, async_=False):
    """
    创建一个带有单选列表的交互式用户界面。

    参数:
    - title (str): 界面顶部显示的标题。
    - values (list): 一个元组列表，其中每个元组包含一个选项的值和显示文本。
    - style (str): 应用于界面的样式。
    - async_ (bool): 如果设置为True，函数将异步运行，否则同步运行。

    返回:
    - 如果 async_ 为 True，则返回一个未来对象；如果为 False，则在用户选择后返回选择的值。
    """
    # 添加退出键绑定。
    bindings = KeyBindings()

    @bindings.add("c-z")
    def exit_(event):
        event.app.exit()  # 退出界面

    @bindings.add("c-right")
    def exit_with_value(event):
        event.app.exit(result=radio_list.current_value)  # 返回选中的值

    # 创建一个单选列表组件，其中的选项由参数 `values` 提供。
    radio_list = RadioList(values)
    # 设置应用程序，其中包含一个水平分割的布局（标题和单选列表）。
    application = Application(
        layout=Layout(HSplit([Label(title), radio_list])),
        key_bindings=merge_key_bindings([load_key_bindings(), bindings]),
        mouse_support=True,
        style=style,
        full_screen=False,
    )

    return application.run_async() if async_ else application.run()


# 创建一个自定义的交互式输入提示，支持单行或多行输入
def prompt_ask(text, multiline=True) -> str:
    """
    创建一个自定义的交互式输入提示，支持单行或多行输入。
    在单行模式下，结束键可以是 [ctrl + enter]。
    在多行模式下，结束键也是 [ctrl + enter]。[enter] 将插入新行。

    参数:
    - text (str): 显示在用户输入前的提示文本。
    - multiline (bool): 指定输入模式是否为多行。如果为True，允许多行输入；如果为False，仅允许单行输入。

    返回:
    - str: 用户输入的文本。
    """
    # 添加退出键绑定。
    kb = KeyBindings()

    # 如果是多行模式，添加一个键绑定：当用户按下 Enter 键时，在当前位置插入新行。
    if multiline:
        @kb.add("enter")
        def _(event):
            event.current_buffer.insert_text("\n")

    # 为所有模式添加键绑定：当用户按下 Ctrl+Enter 时，验证并处理当前缓冲区的内容。
    @kb.add("c-right")  # 官网看了是这个
    def _(event):
        event.current_buffer.validate_and_handle()

    return prompt(
        text,  # 提示文本
        multiline=multiline,  # 是否允许多行输入
        prompt_continuation=prompt_continuation,  # 用于多行输入时显示续行符
        key_bindings=kb,  # 使用定义的键绑定
    )


if __name__ == "__main__":
    print("Test case below") # 以下是测试案例
    print("This is a multi-line input. Press [shift + right-arrow] to accept input. ") # 这是一个多行输入。按 [shift + 右箭头] 接受输入。
    answer = prompt_ask("Multiline input: ", multiline=True)
    print(f"You said: {answer}")

    # With HTML.
    request_option = prompt_select(
        title="> Please key in your options: ",
        values=[
            ("1", HTML('<style fg="cyan">Input test results</style>')), # 输入测试结果
            ("2", HTML('<style fg="cyan">Ask for todos</style>')), # 请求待办事项
            ("3", HTML('<style fg="cyan">Discuss with irGPT</style>')),
            ("4", HTML('<style fg="cyan">Exit</style>')), # 退出
        ],
    )

    print(f"Result = {request_option}")
