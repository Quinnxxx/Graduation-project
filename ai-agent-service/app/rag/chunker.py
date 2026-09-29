"""中文友好的文本分块器。

段落/标点自然断点切分 + 固定窗口 + 重叠，用于知识库文档入库前的
分块预处理，保证检索粒度与上下文完整性。
"""

import re
from typing import List


class TextChunker:
    """中文友好的文本分块器：段落/标点自然断点切分 + 固定窗口 + 重叠。

    参数设计理由：chunk_size=500 兼顾检索粒度与上下文完整性；
    overlap=50（约 10% 重叠）保证跨块语义不丢失。
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        """初始化分块器。

        Args:
            chunk_size: 目标分块大小（字符数）。
            overlap: 相邻块重叠字符数。

        Raises:
            ValueError: chunk_size 或 overlap 非法时。
        """
        if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("chunk_size 必须大于 overlap 且均为正数")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(self, text: str) -> List[str]:
        """将文本切分为带重叠的块列表。

        算法（按序执行）：
        1. 文本 strip 后为空返回 []；
        2. 长度 <= chunk_size 直接返回 [文本]；
        3. 按换行符切段落，逐个累积直到长度 >= chunk_size 成块；
           若某段自身超 chunk_size，先按中文句末标点（。！？；）切分，
           切分后仍超长的片段按固定窗口硬切（兜底，保证块不超限）；
        4. 相邻块重叠：下一块开头拼接上一块末尾 overlap 字符；
        5. 每块 strip 后非空才保留。

        Args:
            text: 原始文本。

        Returns:
            分块列表。
        """
        text = (text or "").strip()
        if not text:
            return []
        if len(text) <= self._chunk_size:
            return [text]

        chunks: List[str] = []
        current = ""
        # 先按段落粗切
        for paragraph in text.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph) > self._chunk_size:
                # 当前累积先成块
                if current:
                    chunks.append(current)
                    current = ""
                # 超长段落内部切分
                chunks.extend(self._split_long_paragraph(paragraph))
            else:
                if current and len(current) + 1 + len(paragraph) > self._chunk_size:
                    chunks.append(current)
                    current = paragraph
                else:
                    current = paragraph if not current else current + "\n" + paragraph

        if current:
            chunks.append(current)

        # 相邻块拼接重叠
        result: List[str] = []
        for i, chunk in enumerate(chunks):
            piece = chunk
            if i > 0 and self._overlap > 0:
                prev_tail = result[-1][-self._overlap :]
                piece = prev_tail + piece
            result.append(piece)
        return result

    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """超长段落切分：优先按中文句末标点，兜底固定窗口。

        Args:
            paragraph: 超过 chunk_size 的段落。

        Returns:
            子片段列表。
        """
        segments = re.split(r"(?<=[。！？；])", paragraph)
        pieces: List[str] = []
        buf = ""
        for seg in segments:
            if not seg:
                continue
            if len(seg) > self._chunk_size:
                if buf:
                    pieces.append(buf)
                    buf = ""
                for i in range(0, len(seg), self._chunk_size):
                    pieces.append(seg[i : i + self._chunk_size])
            else:
                if buf and len(buf) + len(seg) > self._chunk_size:
                    pieces.append(buf)
                    buf = seg
                else:
                    buf += seg
        if buf:
            pieces.append(buf)
        return [p for p in pieces if p.strip()]
