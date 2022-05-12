from typing import Callable, Optional
from warnings import warn

from vapoursynth import FieldBased, VideoNode, core

from vsfieldkit.util import convert_format_if_needed
from vsfieldkit.vapoursynth import VS_FIELD_FROM_BOTTOM, VS_FIELD_FROM_TOP


def bob(
    clip: VideoNode,
    shift: bool = True,
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
    if (
        shift
        and hasattr(core.resize, 'Bob')
        and hasattr(kernel, 'plugin')
        and kernel.plugin.namespace == 'resize'
    ):
        kernel_filter = kernel.name.lower()
        warn(f'In VapourSynth >=R58, use the built-in '
             f'core.resize.Bob(filter="{kernel_filter}" instead)).',
             DeprecationWarning)
        stretched = clip.resize.Bob(filter=kernel_filter)
    else:
        as_fields = clip.std.SeparateFields(tff=tff)
        stretched = convert_format_if_needed(
            as_fields,
            height=clip.height,
            kernel=kernel,
            dither_type=dither_type
        )

        if shift:
            # core.resize doesn't expose zimg's destination field parity
            # options so we have to assume it won't shift for us. We can trick
            # it using its active region stuff instead. In zimg's sub-pixel
            # layout, the fields are shifted by 1/4, adjusted for stretch as
            # 1/8th.
            stretched_as_top = convert_format_if_needed(
                as_fields,
                height=clip.height,
                kernel=kernel,
                dither_type=dither_type,
                src_top=0.125
            )
            stretched_as_bottom = convert_format_if_needed(
                as_fields,
                height=clip.height,
                kernel=kernel,
                dither_type=dither_type,
                src_top=-0.125
            )
            shift_map = {
                VS_FIELD_FROM_TOP: stretched_as_top,
                VS_FIELD_FROM_BOTTOM: stretched_as_bottom
            }
            stretched = stretched.std.FrameEval(
                lambda n, f: shift_map[f.props._Field],
                prop_src=(as_fields,)
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
