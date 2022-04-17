from typing import Callable, Optional

from vapoursynth import FieldBased, VideoNode, core

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


def resample_as_progressive(
    clip: VideoNode,
    kernel: Callable = core.resize.Spline36,
    dither_type: str = 'random'
) -> VideoNode:
    """When every frame of the clip represents progressive content (no
    combing) this will take any frames encoded interlaced and resample them so
    that they are progressive in both content AND format.
    """
    upsampled = upsample_as_progressive(clip)
    resampled = convert_format_if_needed(
        upsampled,
        format=clip.format,
        kernel=kernel,
        dither_type=dither_type
    )
    return resampled


def upsample_as_progressive(clip: VideoNode):
    """Returns a clip now marked as progressive and with any vertical
    chroma subsampling removed so that previously-alternating chroma lines
    will be laid out in the correct one-line-after-another order for
    progressive content."""
    upsampled = convert_format_if_needed(
        clip,
        subsampling_h=0,
        kernel=core.resize.Point,
        dither_type='none'
    )
    as_progressive = upsampled.std.SetFieldBased(FieldBased.FIELD_PROGRESSIVE)
    return as_progressive
