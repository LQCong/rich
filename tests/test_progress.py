# encoding=utf-8

import io
from time import time

import pytest

from rich.bar import Bar
from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.progress import (
    BarColumn,
    FileSizeColumn,
    TotalFileSizeColumn,
    DownloadColumn,
    TransferSpeedColumn,
    Progress,
    Task,
    TextColumn,
    TimeRemainingColumn,
    track,
    TaskID,
    _RefreshThread,
)
from rich.text import Text


class MockClock:
    """A clock that is manually advanced."""

    def __init__(self, time=0.0, auto=True) -> None:
        self.time = time
        self.auto = auto

    def __call__(self) -> float:
        try:
            return self.time
        finally:
            if self.auto:
                self.time += 1

    def tick(self, advance: float = 1) -> None:
        self.time += advance


def test_bar_columns():
    bar_column = BarColumn(100)
    assert bar_column.bar_width == 100
    task = Task(1, "test", 100, 20, _get_time=lambda: 1.0)
    bar = bar_column(task)
    assert isinstance(bar, Bar)
    assert bar.completed == 20
    assert bar.total == 100


def test_text_column():
    text_column = TextColumn("[b]foo", highlighter=NullHighlighter())
    task = Task(1, "test", 100, 20, _get_time=lambda: 1.0)
    text = text_column.render(task)
    assert str(text) == "foo"

    text_column = TextColumn("[b]bar", markup=False)
    task = Task(1, "test", 100, 20, _get_time=lambda: 1.0)
    text = text_column.render(task)
    assert text == Text("[b]bar")


def test_time_remaining_column():
    class FakeTask(Task):
        time_remaining = 60

    column = TimeRemainingColumn()
    task = Task(1, "test", 100, 20, _get_time=lambda: 1.0)
    text = column(task)
    assert str(text) == "-:--:--"

    text = column(FakeTask(1, "test", 100, 20, _get_time=lambda: 1.0))
    assert str(text) == "0:01:00"


def test_task_ids():
    progress = make_progress()
    assert progress.task_ids == [0, 1, 2, 4]


def test_finished():
    progress = make_progress()
    assert not progress.finished


def make_progress() -> Progress:
    _time = 0.0

    def fake_time():
        nonlocal _time
        try:
            return _time
        finally:
            _time += 1

    console = Console(
        file=io.StringIO(),
        force_terminal=True,
        color_system="truecolor",
        width=80,
        legacy_windows=False,
    )
    progress = Progress(console=console, get_time=fake_time, auto_refresh=False)
    task1 = progress.add_task("foo")
    task2 = progress.add_task("bar", total=30)
    progress.advance(task2, 16)
    task3 = progress.add_task("baz", visible=False)
    task4 = progress.add_task("egg")
    progress.remove_task(task4)
    task4 = progress.add_task("foo2", completed=50, start=False)
    progress.start_task(task4)
    progress.update(
        task4, total=200, advance=50, completed=200, visible=True, refresh=True
    )
    return progress


def render_progress() -> str:
    progress = make_progress()
    with progress:
        pass
    progress_render = progress.console.file.getvalue()
    return progress_render


def test_expand_bar() -> None:
    console = Console(
        file=io.StringIO(),
        force_terminal=True,
        width=10,
        color_system="truecolor",
        legacy_windows=False,
    )
    progress = Progress(
        BarColumn(bar_width=None),
        console=console,
        get_time=lambda: 1.0,
        auto_refresh=False,
    )
    progress.add_task("foo")
    with progress:
        pass
    expected = "\x1b[?25l\x1b[38;5;237m━━━━━━━━━━\x1b[0m\r\x1b[2K\x1b[38;5;237m━━━━━━━━━━\x1b[0m\n\x1b[?25h"
    render_result = console.file.getvalue()
    print(repr(render_result))
    assert render_result == expected


def test_render() -> None:
    expected = "\x1b[?25lfoo  \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m  0%\x1b[0m \x1b[36m-:--:--\x1b[0m\nbar  \x1b[38;2;249;38;114m━━━━━━━━━━━━━━━━━━━━━\x1b[0m\x1b[38;5;237m╺\x1b[0m\x1b[38;5;237m━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m 53%\x1b[0m \x1b[36m-:--:--\x1b[0m\nfoo2 \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m100%\x1b[0m \x1b[36m0:00:00\x1b[0m\r\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2Kfoo  \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m  0%\x1b[0m \x1b[36m-:--:--\x1b[0m\nbar  \x1b[38;2;249;38;114m━━━━━━━━━━━━━━━━━━━━━\x1b[0m\x1b[38;5;237m╺\x1b[0m\x1b[38;5;237m━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m 53%\x1b[0m \x1b[36m-:--:--\x1b[0m\nfoo2 \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m100%\x1b[0m \x1b[36m0:00:00\x1b[0m\n\x1b[?25h"
    render_result = render_progress()
    print(repr(render_result))
    assert render_result == expected


def test_track() -> None:

    console = Console(
        file=io.StringIO(),
        force_terminal=True,
        width=60,
        color_system="truecolor",
        legacy_windows=False,
    )
    test = ["foo", "bar", "baz"]
    expected_values = iter(test)
    for value in track(
        test, "test", console=console, auto_refresh=False, get_time=MockClock(auto=True)
    ):
        assert value == next(expected_values)
    result = console.file.getvalue()
    print(repr(result))
    expected = "\x1b[?25ltest \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m  0%\x1b[0m \x1b[36m-:--:--\x1b[0m\r\x1b[2Ktest \x1b[38;2;249;38;114m━━━━━━━━━━━━━\x1b[0m\x1b[38;5;237m╺\x1b[0m\x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m 33%\x1b[0m \x1b[36m-:--:--\x1b[0m\r\x1b[2Ktest \x1b[38;2;249;38;114m━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m\x1b[38;2;249;38;114m╸\x1b[0m\x1b[38;5;237m━━━━━━━━━━━━━\x1b[0m \x1b[35m 67%\x1b[0m \x1b[36m0:00:06\x1b[0m\r\x1b[2Ktest \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m100%\x1b[0m \x1b[36m0:00:00\x1b[0m\r\x1b[2Ktest \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[35m100%\x1b[0m \x1b[36m0:00:00\x1b[0m\n\x1b[?25h"
    assert result == expected

    with pytest.raises(ValueError):
        for n in track(5):
            pass


def test_columns() -> None:

    console = Console(
        file=io.StringIO(),
        force_terminal=True,
        width=80,
        log_time_format="[TIME]",
        color_system="truecolor",
        legacy_windows=False,
        log_path=False,
    )
    progress = Progress(
        "test",
        TextColumn("{task.description}"),
        BarColumn(bar_width=None),
        TimeRemainingColumn(),
        FileSizeColumn(),
        TotalFileSizeColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        transient=True,
        console=console,
        auto_refresh=False,
        get_time=MockClock(),
    )
    task1 = progress.add_task("foo", total=10)
    task2 = progress.add_task("bar", total=7)
    with progress:
        for n in range(4):
            progress.advance(task1, 3)
            progress.advance(task2, 4)
        print("foo")
        console.log("hello")
        console.print("world")
        progress.refresh()
    from render import replace_link_ids

    result = replace_link_ids(console.file.getvalue())
    print(repr(result))
    expected = "\x1b[?25ltest foo \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m10 bytes\x1b[0m \x1b[32m0/10 bytes\x1b[0m \x1b[31m?\x1b[0m\ntest bar \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m7 bytes \x1b[0m \x1b[32m0/7 bytes \x1b[0m \x1b[31m?\x1b[0m\r\x1b[2K\x1b[1A\x1b[2Kfoo\ntest foo \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m10 bytes\x1b[0m \x1b[32m0/10 bytes\x1b[0m \x1b[31m?\x1b[0m\ntest bar \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m7 bytes \x1b[0m \x1b[32m0/7 bytes \x1b[0m \x1b[31m?\x1b[0m\r\x1b[2K\x1b[1A\x1b[2K\x1b[2;36m[TIME]\x1b[0m\x1b[2;36m \x1b[0mhello                                                                    \ntest foo \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m10 bytes\x1b[0m \x1b[32m0/10 bytes\x1b[0m \x1b[31m?\x1b[0m\ntest bar \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m7 bytes \x1b[0m \x1b[32m0/7 bytes \x1b[0m \x1b[31m?\x1b[0m\r\x1b[2K\x1b[1A\x1b[2Kworld\ntest foo \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m10 bytes\x1b[0m \x1b[32m0/10 bytes\x1b[0m \x1b[31m?\x1b[0m\ntest bar \x1b[38;5;237m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m-:--:--\x1b[0m \x1b[32m0 bytes\x1b[0m \x1b[32m7 bytes \x1b[0m \x1b[32m0/7 bytes \x1b[0m \x1b[31m?\x1b[0m\r\x1b[2K\x1b[1A\x1b[2Ktest foo \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m0:00:00\x1b[0m \x1b[32m12 bytes\x1b[0m \x1b[32m10 bytes\x1b[0m \x1b[32m12/10 bytes\x1b[0m \x1b[31m1 byte/s \x1b[0m\ntest bar \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m0:00:00\x1b[0m \x1b[32m16 bytes\x1b[0m \x1b[32m7 bytes \x1b[0m \x1b[32m16/7 bytes \x1b[0m \x1b[31m2 bytes/s\x1b[0m\r\x1b[2K\x1b[1A\x1b[2Ktest foo \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m0:00:00\x1b[0m \x1b[32m12 bytes\x1b[0m \x1b[32m10 bytes\x1b[0m \x1b[32m12/10 bytes\x1b[0m \x1b[31m1 byte/s \x1b[0m\ntest bar \x1b[38;2;114;156;31m━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m \x1b[36m0:00:00\x1b[0m \x1b[32m16 bytes\x1b[0m \x1b[32m7 bytes \x1b[0m \x1b[32m16/7 bytes \x1b[0m \x1b[31m2 bytes/s\x1b[0m\n\x1b[?25h\r\x1b[1A\x1b[2K\x1b[1A\x1b[2K"
    assert result == expected


def test_task_create() -> None:
    task = Task(TaskID(1), "foo", 100, 0, _get_time=lambda: 1)
    assert task.elapsed is None
    assert not task.finished
    assert task.percentage == 0.0
    assert task.speed is None
    assert task.time_remaining is None


def test_task_start() -> None:
    current_time = 1

    def get_time():
        nonlocal current_time
        return current_time

    task = Task(TaskID(1), "foo", 100, 0, _get_time=get_time)
    task.start_time = get_time()
    assert task.started == True
    assert task.elapsed == 0
    current_time += 1
    assert task.elapsed == 1
    current_time += 1
    task.stop_time = get_time()
    current_time += 1
    assert task.elapsed == 2


def test_task_zero_total() -> None:
    task = Task(TaskID(1), "foo", 0, 0, _get_time=lambda: 1)
    assert task.percentage == 0


def test_progress_create() -> None:
    progress = Progress()
    assert progress.finished
    assert progress.tasks == []
    assert progress.task_ids == []


def test_refresh_thread() -> None:
    progress = Progress()
    thread = _RefreshThread(progress, 10)
    assert thread.progress == progress


if __name__ == "__main__":
    _render = render_progress()
    print(_render)
    print(repr(_render))
