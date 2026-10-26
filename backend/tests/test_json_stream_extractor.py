"""Tests for _JsonStringFieldExtractor.

核心验收：流式输入 JSON 字符串时，提取出的 question 字段值
必须是解码后的干净正文，不包含原始 JSON 片段、转义字符、或其他字段内容。
"""

from app.infrastructure.agent.interview_agent import _JsonStringFieldExtractor


def _feed_in_chunks(extractor: _JsonStringFieldExtractor, text: str, chunk_size: int = 3) -> str:
    """Simulate streaming by feeding text in small chunks."""
    result = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        result.append(extractor.feed(chunk))
    return "".join(result)


def test_extracts_plain_string_value() -> None:
    """普通字符串值应原样提取。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"decision":"continue","question":"你好世界","reason":"test"}'
    result = _feed_in_chunks(extractor, json_text)
    assert result == "你好世界"


def test_extracts_value_with_newline_escape() -> None:
    """\\n 转义应解码为真实换行符。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"第一行\\n第二行"}'
    result = _feed_in_chunks(extractor, json_text)
    assert result == "第一行\n第二行"


def test_extracts_value_with_quote_escape() -> None:
    """\\" 转义应解码为真实引号。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"他说\\"你好\\""}'
    result = _feed_in_chunks(extractor, json_text)
    assert result == '他说"你好"'


def test_extracts_value_with_backslash_escape() -> None:
    """\\\\ 转义应解码为单个反斜杠。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"路径\\\\to\\\\file"}'
    result = _feed_in_chunks(extractor, json_text)
    assert result == "路径\\to\\file"


def test_extracts_value_with_tab_escape() -> None:
    """\\t 转义应解码为制表符。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"a\\tb"}'
    result = _feed_in_chunks(extractor, json_text)
    assert result == "a\tb"


def test_extracts_value_with_unicode_escape() -> None:
    """\\uXXXX 转义应解码为对应字符。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"\\u4f60\\u597d"}'  # 你好
    result = _feed_in_chunks(extractor, json_text)
    assert result == "你好"


def test_does_not_leak_other_fields() -> None:
    """其他字段（decision、reason）的内容不应出现在 delta 中。

    这是流式输出的关键安全要求：候选人只能看到问题，
    不能看到面试官的决策依据和内心评价。
    """
    extractor = _JsonStringFieldExtractor("question")
    json_text = (
        '{"decision":"continue",'
        '"question":"请解释一下 HashMap 的工作原理",'
        '"reason":"候选人回答不够深入，需要继续考察基础"}'
    )
    result = _feed_in_chunks(extractor, json_text)
    assert "continue" not in result
    assert "decision" not in result
    assert "reason" not in result
    assert "候选人回答不够深入" not in result
    assert result == "请解释一下 HashMap 的工作原理"


def test_question_not_first_field_no_leak() -> None:
    """question 不在第一个字段时，前面的字段内容不应泄漏。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = (
        '{"decision":"switch",'
        '"reason":"这部分已经掌握了，换个方向",'
        '"question":"说说 Redis 的数据结构"}'
    )
    result = _feed_in_chunks(extractor, json_text)
    assert "switch" not in result
    assert "reason" not in result
    assert "这部分已经掌握了" not in result
    assert result == "说说 Redis 的数据结构"


def test_null_value_yields_nothing() -> None:
    """值为 null 时不输出任何内容（也不报错）。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"decision":"end","question":null}'
    result = _feed_in_chunks(extractor, json_text)
    assert result == ""


def test_field_after_string_closes_stops() -> None:
    """字符串闭合后停止提取，后面的内容不泄漏。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"问题正文","more_stuff":"不应出现"}'
    result = _feed_in_chunks(extractor, json_text)
    assert "不应出现" not in result
    assert result == "问题正文"


def test_non_json_returns_empty() -> None:
    """非 JSON 输出（纯文本）时不提取任何内容。"""
    extractor = _JsonStringFieldExtractor("question")
    result = _feed_in_chunks(extractor, "这是一段纯文本，不是 JSON")
    assert result == ""


def test_partial_json_still_extracts() -> None:
    """JSON 还没收尾时，已到达的 question 内容仍然可以提取。"""
    extractor = _JsonStringFieldExtractor("question")
    # 只给一半：question 字段值还没闭合
    partial = '{"question":"还在生成中'
    result = _feed_in_chunks(extractor, partial)
    assert result == "还在生成中"


def test_mixed_escapes_in_long_string() -> None:
    """复杂混合转义场景下，所有转义序列都正确解码。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = (
        '{"question":"行1\\n行2含\\"引号\\"\\t制表符\\\\反斜杠\\u2713勾号"}'
    )
    result = _feed_in_chunks(extractor, json_text)
    assert "\n" in result
    assert '"' in result
    assert "\t" in result
    assert "\\" in result
    assert "✓" in result
    assert "行1" in result
    assert "行2含" in result


def test_single_chunk_works() -> None:
    """单次喂入完整 JSON 也能正确工作。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"完整问题"}'
    result = extractor.feed(json_text)
    assert result == "完整问题"


def test_done_state_stops_extracting() -> None:
    """提取完成后（DONE 状态）再喂入内容应忽略。"""
    extractor = _JsonStringFieldExtractor("question")
    json_text = '{"question":"已完成","extra":"忽略"}'
    result = extractor.feed(json_text)
    assert result == "已完成"
    # 再次喂入也不会有新内容
    more = extractor.feed("更多内容")
    assert more == ""
