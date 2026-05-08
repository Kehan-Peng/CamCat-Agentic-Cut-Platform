from backend.app.domain.models import CreativeSuggestion
from backend.app.retrieval.local_index import LocalSearchResult


def build_creative_suggestion(result: LocalSearchResult) -> CreativeSuggestion:
    if result.motion_score >= 0.85 or result.highlight_score >= 0.85:
        return CreativeSuggestion(
            recommended_bgm_style="热血鼓点 / 电子摇滚",
            transition_suggestions=["卡点硬切", "速度拉升"],
            editing_notes=["优先贴合高光动作点", "可用于短视频开场或高潮段落"],
        )

    return CreativeSuggestion(
        recommended_bgm_style="中速节奏铺底",
        transition_suggestions=["节奏切换"],
        editing_notes=["适合作为上下文衔接素材"],
    )


def build_overall_suggestion(results: list[LocalSearchResult]) -> CreativeSuggestion:
    if any(result.motion_score >= 0.85 or result.highlight_score >= 0.85 for result in results):
        return CreativeSuggestion(
            recommended_bgm_style="热血鼓点 / 电子摇滚",
            transition_suggestions=["按高光分排序后做连续卡点"],
            editing_notes=["先使用运动分和高光分最高的片段承接高潮"],
        )

    return CreativeSuggestion(
        recommended_bgm_style="中速节奏铺底",
        transition_suggestions=["自然转场"],
        editing_notes=["当前结果更适合叙事铺垫"],
    )
