from typing import Optional
from warnings import warn

from vapoursynth import FieldBased, VideoNode, core

from vsfieldkit.kernels import resample_chroma_with_spline36
from vsfieldkit.types import Resizer
from vsfieldkit.util import convert_format_if_needed
from vsfieldkit.vapoursynth import VS_FIELD_FROM_BOTTOM, VS_FIELD_FROM_TOP


def bob(
    clip: VideoNode,
    shift: bool = True,
    tff: Optional[bool] = None,
    keep_field_property: bool = True,
    kernel: Resizer = core.resize.Spline36,
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
    subsampling_kernel: Resizer = resample_chroma_with_spline36,
    upsampling_kernel: Resizer = resample_chroma_with_spline36,
    dither_type: str = 'random',
    avoid_chroma_shift=True
) -> VideoNode:
    """When every frame of the clip represents progressive content (no
    combing) this will take any frames encoded interlaced and resample them so
    that they are progressive in both content AND format.
    """
    if (
        avoid_chroma_shift
        and (
            not hasattr(upsampling_kernel, 'supports_resizing')
            or upsampling_kernel.supports_resizing is True
        )
    ):
        # For the round trip up and down, we can avoid the subsampling grid
        # altogether by working on individual planes.
        y, cb, cr = clip.std.SplitPlanes()
        upsampled_planes = [
             y.std.SetFieldBased(FieldBased.FIELD_PROGRESSIVE)
        ] + [
             convert_format_if_needed(
                 plane,
                 height=y.height,
                 width=y.width,
                 kernel=upsampling_kernel
             ).std.SetFieldBased(FieldBased.FIELD_PROGRESSIVE)
             for plane in (cb, cr)
        ]
        resampled_planes = (
            upsampled_planes[0],
            convert_format_if_needed(
                upsampled_planes[1],
                height=cb.height,
                width=cb.width,
                kernel=subsampling_kernel,
                dither_type=dither_type
            ),
            convert_format_if_needed(
                upsampled_planes[2],
                height=cr.height,
                width=cr.width,
                kernel=subsampling_kernel,
                dither_type=dither_type
            )
        )
        resampled = core.std.ShufflePlanes(
            clips=resampled_planes,
            planes=(0, 0, 0),
            colorfamily=clip.format.color_family
        )
    else:
        upsampled = upsample_as_progressive(
            clip,
            kernel=upsampling_kernel,
            upsample_horizontally=True
        )
        resampled = convert_format_if_needed(
            upsampled,
            format=clip.format,
            kernel=subsampling_kernel,
            dither_type=dither_type,
        )
    return resampled


def upsample_as_progressive(
    clip: VideoNode,
    upsample_horizontally=False,
    kernel: Resizer = resample_chroma_with_spline36,
    dither_type: str = 'random'
):
    """Returns a clip now marked as progressive and with any vertical
    chroma subsampling removed so that previously-alternating chroma lines
    will be laid out in the correct one-line-after-another order for
    progressive content."""
    subsampling_w = 0 if upsample_horizontally else clip.format.subsampling_w
    upsampled = convert_format_if_needed(
        clip,
        subsampling_h=0,
        subsampling_w=subsampling_w,
        kernel=kernel,
        dither_type=dither_type
    )
    as_progressive = upsampled.std.SetFieldBased(FieldBased.FIELD_PROGRESSIVE)
    return as_progressive
