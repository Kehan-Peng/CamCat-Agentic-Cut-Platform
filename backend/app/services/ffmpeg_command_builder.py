"""
FFmpegCommandBuilder

构建安全的 FFmpeg 命令（使用参数列表，不使用 shell 字符串）。
"""
import os
from backend.app.domain.render import ClipSegment


class FFmpegCommandBuilder:
    """FFmpeg 命令构建器"""

    # 允许的滤镜白名单
    ALLOWED_FILTERS = {
        "fade_in",
        "fade_out",
        "speed_1.5x",
        "speed_2x",
        "scale",
        "crop"
    }

    def build_clip_command(
        self,
        input_path: str,
        output_path: str,
        clip: ClipSegment
    ) -> list[str]:
        """
        构建剪辑命令

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            clip: 剪辑片段

        Returns:
            FFmpeg 命令参数列表

        Raises:
            ValueError: 如果路径或滤镜不安全
        """
        # 验证路径
        self._validate_path(input_path)
        self._validate_path(output_path)

        # 验证滤镜
        for filter_name in clip.filters:
            self._validate_filter(filter_name)

        # 构建命令参数列表
        command = [
            "ffmpeg",
            "-i", input_path,
            "-ss", str(clip.start_time),
            "-t", str(clip.end_time - clip.start_time),
        ]

        # 添加滤镜
        if clip.filters:
            filter_complex = self._build_filter_complex(clip.filters)
            command.extend(["-vf", filter_complex])

        # 添加输出路径
        command.append(output_path)

        return command

    def _validate_path(self, path: str) -> None:
        """
        验证路径安全性

        Args:
            path: 文件路径

        Raises:
            ValueError: 如果路径不安全
        """
        # 检查路径遍历
        if ".." in path:
            raise ValueError(f"不安全的路径: {path}")

        # 检查绝对路径
        if not os.path.isabs(path):
            raise ValueError(f"必须使用绝对路径: {path}")

        # 检查路径是否在允许的目录中
        # 在实际实现中，这里应该检查路径是否在白名单目录中
        # 现在只做基本检查
        if path.startswith("/etc/") or path.startswith("/sys/"):
            raise ValueError(f"不安全的路径: {path}")

    def _validate_filter(self, filter_name: str) -> None:
        """
        验证滤镜安全性

        Args:
            filter_name: 滤镜名称

        Raises:
            ValueError: 如果滤镜不安全
        """
        # 检查是否在白名单中
        if filter_name not in self.ALLOWED_FILTERS:
            raise ValueError(f"不安全的滤镜: {filter_name}")

        # 检查是否包含危险字符
        if ";" in filter_name or "|" in filter_name or "&" in filter_name:
            raise ValueError(f"不安全的滤镜: {filter_name}")

    def _build_filter_complex(self, filters: list[str]) -> str:
        """
        构建滤镜复合字符串

        Args:
            filters: 滤镜列表

        Returns:
            滤镜复合字符串
        """
        # 简单实现：将滤镜用逗号连接
        # 在实际实现中，这里应该根据滤镜类型构建正确的 FFmpeg 滤镜语法
        return ",".join(filters)
