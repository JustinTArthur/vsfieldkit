from math import ceil
from typing import Optional, Sequence, Tuple, Union

from vapoursynth import (ColorFamily, FieldBased, PresetFormat, VideoFormat,
                         VideoNode, core)

from vsfieldkit.types import FormatSpecifier
from vsfieldkit.util import format_from_specifier, requires_plugins
from vsfieldkit.vapoursynth import VS_FIELD_FROM_BOTTOM, VS_FIELD_FROM_TOP

FULL_ANALOG_DISPLAY_LINES = frozenset((486, 576))


@requires_plugins(('fb', 'fillborders'), ('cf', 'ContinuityFixer'))
def fill_analog_frame_ends(
    clip: VideoNode,
    top_blank_width: Optional[int] = None,
    bottom_blank_width: Optional[int] = None,
    continuity_radius: Union[int, Sequence[int]] = (5,),
    luma_splash_radius: int = 1,
    original_format: Optional[FormatSpecifier] = None,
    restore_blank_detail=False
) -> VideoNode:
    """Fills the beginning and end half-lines from frames digitized for or
    from PAL/NTSC signal. It aims to interpolate only the missing data, leaving
    existing pixels in-tact.

    These lines are often half-blanked so that the CRT electron beam won't
    light up phosphors as it zig-zags from the bottom of screen to the top to
    start painting the next frame."""
    if top_blank_width is None:
        top_blank_width = ceil(clip.width * 0.65)
    if bottom_blank_width is None:
        bottom_blank_width = ceil(clip.width * 0.65)

    if original_format is None:
        original_format = clip.format
    else:
        original_format = format_from_specifier(original_format)

    color_family = clip.format.color_family
    num_planes = clip.format.num_planes
    chroma_height = 2 ** clip.format.subsampling_h
    original_chroma_height = 2 ** original_format.subsampling_h
    orig_color_sample_equiv = max(1, original_chroma_height // chroma_height)

    luma_damage_radius = 1 + luma_splash_radius
    if color_family == ColorFamily.YUV:
        fill_sizes = (
            1,
            orig_color_sample_equiv,
            orig_color_sample_equiv
        )
        continue_sizes = (
            luma_damage_radius,
            orig_color_sample_equiv,
            orig_color_sample_equiv
        )
    elif color_family == ColorFamily.GRAY:
        # Assume no color info persisted. Skip supersampling.
        fill_sizes = (1,) * num_planes
        continue_sizes = (luma_damage_radius,) * num_planes
    else:
        # Assume every plane has luma AND color info.
        fill_sizes = (orig_color_sample_equiv,) * num_planes
        continue_sizes = (
            max(luma_damage_radius, orig_color_sample_equiv),
        ) * num_planes

    if isinstance(continuity_radius, int):
        continuity_radius = (continuity_radius,)
    # Expand radius across implied planes:
    continuity_radius = (
        continuity_radius
        + (continuity_radius[-1:] * (num_planes - len(continuity_radius)))
    )

    # Separate fields. Default tff doesn't matter as we don't care about
    # order, only position.
    fields = clip.std.SeparateFields(tff=True)
    fields_top_edge, fields_bottom_edge = _repaired_frame_edges(
        fields,
        top_blank_width=top_blank_width,
        bottom_blank_width=bottom_blank_width,
        fill_sizes=fill_sizes,
        continue_sizes=continue_sizes,
        continuity_radius=continuity_radius,
        color_sample_height=orig_color_sample_equiv,
        restore_blank_detail=restore_blank_detail
    )
    progressive_top_edge, progressive_bottom_edge = _repaired_frame_edges(
        clip,
        top_blank_width=top_blank_width,
        bottom_blank_width=bottom_blank_width,
        fill_sizes=fill_sizes,
        continue_sizes=continue_sizes,
        continuity_radius=continuity_radius,
        color_sample_height=orig_color_sample_equiv,
        restore_blank_detail=restore_blank_detail
    )
    progressive_repaired = clip
    if top_blank_width:
        fields_repaired_top = core.std.StackVertical((
            fields_top_edge,
            fields.std.Crop(top=fields_top_edge.height)
        ))
        progressive_repaired = core.std.StackVertical((
            progressive_top_edge,
            progressive_repaired.std.Crop(
                top=progressive_top_edge.height
            )
        ))
    else:
        fields_repaired_top = fields
    if bottom_blank_width:
        fields_repaired_bottom = core.std.StackVertical((
            fields.std.Crop(bottom=fields_bottom_edge.height),
            fields_bottom_edge
        ))
        progressive_repaired = core.std.StackVertical((
            progressive_repaired.std.Crop(
                bottom=progressive_bottom_edge.height
            ),
            progressive_bottom_edge
        ))
    else:
        fields_repaired_bottom = fields
    replacement_by_position = {
        VS_FIELD_FROM_TOP: fields_repaired_top,
        VS_FIELD_FROM_BOTTOM: fields_repaired_bottom,
    }

    def repair_field_frame(n, f):
        return replacement_by_position[f.props._Field]

    repaired_fields = fields.std.FrameEval(
        repair_field_frame,
        prop_src=(fields,),
        clip_src=tuple(replacement_by_position.values())
    )
    # Re-interlace fields
    interlaced_repaired = repaired_fields.std.DoubleWeave()[::2]
    # Copy original properties in case we overwrote field-related flags
    interlaced_repaired = interlaced_repaired.std.CopyFrameProps(clip)

    def repair_frame(n, f):
        _field_based = f.props.get('_FieldBased')
        if _field_based in (FieldBased.FIELD_TOP, FieldBased.FIELD_BOTTOM):
            return interlaced_repaired
        else:
            return progressive_repaired

    repaired_frames = clip.std.FrameEval(
        repair_frame,
        prop_src=(clip,),
        clip_src=(interlaced_repaired, progressive_repaired)
    )

    return repaired_frames


def _repaired_frame_edges(
    clip: VideoNode,
    top_blank_width: int,
    bottom_blank_width: int,
    continue_sizes: Sequence[int],
    fill_sizes: Sequence[int],
    continuity_radius: Sequence[int],
    color_sample_height: int,
    restore_blank_detail: bool
) -> Tuple[VideoNode, VideoNode]:
    """Returns repaired top and bottom edges with repairs. Can be fed
    individual field frames or deinterlaced frames. Will be used
    by the caller to reconstruct a full field or frame with the repaired edges.
    """
    color_family = clip.format.color_family
    num_planes = clip.format.num_planes

    # Repeated data provides saner input to cf's least-squares regression due
    # to a horizontal fade often present on the edge.
    field_planes = [
        clip.std.ShufflePlanes(
            planes=(plane,),
            colorfamily=ColorFamily.GRAY
        ) for plane in range(num_planes)
    ]

    filled_top_planes = [
        plane.fb.FillBorders(top=fill_radius, mode='fixborders')
        for plane, fill_radius in zip(field_planes, fill_sizes)
    ]
    filled_bottom_planes = [
        plane.fb.FillBorders(bottom=fill_radius, mode='fixborders')
        for plane, fill_radius in zip(field_planes, fill_sizes)
    ]
    filled_top = core.std.ShufflePlanes(
        clips=filled_top_planes,  # filled_primary_tops + filled_chroma_tops,
        planes=[0 for _plane in range(num_planes)],
        colorfamily=color_family
    )
    filled_bottom = core.std.ShufflePlanes(
        clips=filled_bottom_planes,
        planes=[0 for _plane in range(num_planes)],
        colorfamily=color_family
    )
    top_interpolated = filled_top.cf.ContinuityFixer(
        top=continue_sizes,
        radius=continuity_radius
    )
    bottom_interpolated = filled_bottom.cf.ContinuityFixer(
        bottom=continue_sizes,
        radius=continuity_radius
    )
    if restore_blank_detail:
        # Merge continuity without a prefill on top of the prefill continuity
        top_interpolated = top_interpolated.std.Merge(
            clip.cf.ContinuityFixer(
                top=continue_sizes,
                radius=continuity_radius
            )
        )
        bottom_interpolated = bottom_interpolated.std.Merge(
            clip.cf.ContinuityFixer(
                bottom=continue_sizes,
                radius=continuity_radius
            ))

    # Only bring out the portions that actually needed repair:
    chroma_height_pixels = 2 ** clip.format.subsampling_h
    orig_chroma_height_pixels = color_sample_height * chroma_height_pixels
    repair_height = max(orig_chroma_height_pixels, continue_sizes[0])
    # Round to nearest chroma subsample size:
    repair_height = (
        (repair_height + (chroma_height_pixels - 1))
        & ~(chroma_height_pixels - 1)
    )
    if top_blank_width:
        orig_top_right = clip.std.Crop(
            left=top_blank_width,
            bottom=clip.height - repair_height
        )
        repaired_top_left = top_interpolated.std.Crop(
            right=top_interpolated.width - top_blank_width,
            bottom=top_interpolated.height - repair_height
        )
        repaired_top_edge = core.std.StackHorizontal(
            (repaired_top_left, orig_top_right)
        )
    else:
        repaired_top_edge = clip.std.Crop(
            bottom=clip.height - repair_height
        )
    if bottom_blank_width:
        orig_bottom_left = clip.std.Crop(
            right=bottom_blank_width,
            top=clip.height - repair_height
        )
        repaired_bottom_right = bottom_interpolated.std.Crop(
            left=bottom_interpolated.width - bottom_blank_width,
            top=bottom_interpolated.height - repair_height
        )
        repaired_bottom_edge = core.std.StackHorizontal(
            (orig_bottom_left, repaired_bottom_right)
        )
    else:
        repaired_bottom_edge = clip.std.Crop(
            top=clip.height - repair_height
        )
    return repaired_top_edge, repaired_bottom_edge
