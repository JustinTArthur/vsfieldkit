from typing import Callable, Optional

from vapoursynth import VideoNode, core

from vsfieldkit.util import convert_format_if_needed


def bob(
    clip: VideoNode,
    tff: Optional[bool] = None,
    keep_field_property: bool = True,
    kernel: Callable = core.resize.Spline36,
    dither_type: str = 'random'
) -> VideoNode:
    """Returns a clip of progressive frames, each consisting of a field from
    the original interlaced clip in order of its original capture.

    As interlaced fields have half the resolution of a given moment, the new
    frames are stretched up to the original clip's height.
    """
    as_fields = clip.std.SeparateFields(tff=tff)
    stretched = convert_format_if_needed(
        as_fields,
        height=clip.height,
        kernel=kernel,
        dither_type=dither_type
    )
    if keep_field_property:
        return stretched

    return stretched.std.RemoveFrameProps(('_Field',))
