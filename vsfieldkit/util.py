from functools import partial
from typing import Iterator, Mapping, Optional, Sequence, Tuple, Union

from vapoursynth import (ColorFamily, ColorRange, Error, FieldBased,
                         VideoFormat, VideoFrame, VideoNode, core)

from vsfieldkit.types import Factor, FormatSpecifier, Resizer

FORMAT_INTRINSICS = (
    'color_family',
    'sample_type',
    'subsampling_w',
    'subsampling_h',
    'bits_per_sample'
)

VERTICAL_CENTER_CHROMA_LOCS = {
    None: 2,  # assume left, resample as topleft
    0: 2,     # left, resample as topleft
    1: 3      # center, resample as top
}


def assume_bff(clip: VideoNode) -> VideoNode:
    """Returns a new clip where every frame is marked as interlaced in
    bottom-field-first order. Only changes metadata, does not adjust the clip
    content or re-arrange chroma samples.
    """
    return clip.std.SetFrameProp(
        prop='_FieldBased',
        intval=FieldBased.FIELD_BOTTOM.value
    )


def assume_tff(clip: VideoNode) -> VideoNode:
    """Returns a new clip where every frame is marked as interlaced in
    top-field-first order. Only changes metadata, does not adjust the clip
    content or re-arrange chroma samples.
    """
    return clip.std.SetFrameProp(
        prop='_FieldBased',
        intval=FieldBased.FIELD_TOP.value
    )


def assume_progressive(clip: VideoNode) -> VideoNode:
    """Returns a new clip where every frame is marked as progressive. Only
    changes metadata, does not adjust the clip content or re-arrange chroma
    samples.
    """
    return clip.std.SetFrameProp(
        prop='_FieldBased',
        intval=FieldBased.FIELD_PROGRESSIVE.value
    )


def double(clip: VideoNode) -> VideoNode:
    """Returns a clip where each original frame is repeated once and plays at
    twice the speed so the played image matches the original in time.

    Not specific to interlacing or deinterlacing, but useful for comparing
    original interlaced pictures with frame-doubled content such as that
    from a bob or phosphor deinterlacer.
    """
    doubled_frames = core.std.Interleave(
        (clip, clip),
        modify_duration=True  # Should double fps, halve per-frame duration
    )
    return doubled_frames


def group_by_combed(
    clip: VideoNode
) -> Iterator[Tuple[Union[bool, None], VideoNode]]:
    """Assuming the passed-in clip was processed by a filter that performs
    comb detection, this splits the clip into segments based on whether they
    are combed or not. The values it generates are True, False, or None if it
    was marked combed, not combed, or not marked as well as the segment of the
    clip."""
    last_combed = ...
    last_change = 0
    for n, frame in enumerate(clip.frames()):
        is_combed = getattr(frame.props, '_Combed', None)
        if is_combed != last_combed:
            if last_combed is not ...:
                yield last_combed, clip[last_change:n]
                last_change = n

            last_combed = is_combed
    yield last_combed, clip[last_change:]


def group_by_field_order(
    clip: VideoNode
) -> Iterator[Tuple[Union[FieldBased, None], VideoNode]]:
    """
    Generates field orders and clips from the passed in clip split up by
    changes in field order. Field order is expressed as a
    vapoursynth.FieldBased enumeration or None if field order is not
    applicable or not available."""
    last_order = ...
    last_change = 0
    for n, frame in enumerate(clip.frames()):
        frame_order = getattr(frame.props, '_FieldBased', None)
        if frame_order != last_order:
            if last_order is not ...:
                yield (
                    None if last_order is None else FieldBased(last_order),
                    clip[last_change:n]
                )
                last_change = n

            last_order = frame_order
    yield (
          None if last_order is None else FieldBased(last_order),
          clip[last_change:]
    )


def convert_format_if_needed(
    clip: VideoNode,
    kernel: Resizer = core.resize.Spline36,
    format: Optional[VideoFormat] = None,
    dither_type='random',
    **format_or_resize_specs,
):
    existing_fmt_specs = {
        attr: getattr(clip.format, attr)
        for attr in FORMAT_INTRINSICS
    }

    target_fmt_specs = dict(existing_fmt_specs)
    if format:
        target_fmt_specs.update({
            attr: getattr(format, attr)
            for attr in FORMAT_INTRINSICS
        })
    target_fmt_specs.update({
        arg: value
        for arg, value in format_or_resize_specs.items()
        if arg in FORMAT_INTRINSICS
    })

    resize_args = {
        arg: value
        for arg, value in format_or_resize_specs.items()
        if arg not in FORMAT_INTRINSICS
    }
    if target_fmt_specs != existing_fmt_specs:
        resize_args['format'] = core.query_video_format(**target_fmt_specs).id

    if not resize_args:
        # No changes needed.
        return clip

    if (
        dither_type is not None
        and dither_type != 'none'
        and target_fmt_specs['bits_per_sample'] < 16
    ):
        resize_args['dither_type'] = dither_type

    return kernel(clip, **resize_args)


def black_clip_from_clip(clip, **blank_clip_args):
    """Creates a clip of black color in the same format as the passed in clip.
    Unlike BlankClip, this takes the passed in clip's color range into account
    by rendering the first frame.
    """
    bit_depth = clip.format.bits_per_sample
    is_integer = (clip.format.sample_type == 0)
    color_range = clip.get_frame(0).props.get('_ColorRange')

    black_planes = []
    # Luma Plane
    if is_integer and color_range == ColorRange.RANGE_LIMITED:
        floor_multiplier = (2 ** bit_depth) / 256
        limited_black = 16 * floor_multiplier
        black_planes.append(limited_black)
    else:
        black_planes.append(0)
    # First Chroma Plane
    if clip.format.color_family == ColorFamily.YUV:
        black_planes.append((1 << (bit_depth - 1)) if is_integer else 0.5)
    # Fill to rest of the planes
    black_planes += (
        [black_planes[-1]]
        * (clip.format.num_planes - len(black_planes))
    )

    return clip.std.BlankClip(color=black_planes, **blank_clip_args)


def brighten(clip: VideoNode, factor: Factor):
    """Increases intensity across all colors.
    This may not map 1:1 with an H′S′V′ family V′ increase.
    With Y′CbCr, only increases Y′.

    Note this increase ignores the clip's OETF (transfer characteristic)
    so the factor is applied as if the values are linear light levels.
    """
    format: VideoFormat = clip.format
    is_integer = (format.sample_type == 0)
    color_range = clip.get_frame(0).props.get('_ColorRange')

    if is_integer:
        if color_range == ColorRange.RANGE_LIMITED:
            ceiling_multiplier = (2 ** format.bits_per_sample) / 256
            max_val = 235 * ceiling_multiplier
        else:
            max_val = (2 ** format.bits_per_sample) - 1
    else:
        max_val = 1.0

    plane_expr = f'x {float(factor)} * {max_val} min'
    if format.color_family == ColorFamily.YUV:
        expr = (plane_expr, '')
    else:
        expr = (plane_expr,)

    return clip.std.Expr(expr)


def format_from_specifier(specifier: FormatSpecifier) -> VideoFormat:
    if isinstance(specifier, VideoFormat):
        return specifier
    elif isinstance(specifier, VideoNode):
        return specifier.format
    return core.get_video_format(specifier)


def require_plugins(
    *plugins: Tuple[str, str]
):
    missing = []
    for plugin_namespace, plugin_name in plugins:
        if not hasattr(core, plugin_namespace):
            missing.append(f'{plugin_namespace} ({plugin_name})')
    if missing:
        raise Error(f'Missing required plugin(s): {",".join(missing)}')


def require_one_of(
    *plugins: Tuple[str, str]
):
    missing = []
    for plugin_namespace, plugin_name in plugins:
        if hasattr(core, plugin_namespace):
            break
        else:
            missing.append(f'{plugin_namespace} ({plugin_name})')
    else:
        raise Error(
            f'Requires any one of these plugins: {",".join(missing)}'
        )


def shift_chroma_to_luma_sited(
    clip: VideoNode,
    tff: bool,
    shift_kernel: Resizer,
) -> VideoNode:
    """Takes a clip marked as having vertically centered chroma and
    assumes that the chroma samples are centered BETWEEN luma samples
    from a prior subsampled state. Establishes new chroma samples that
    resemble the same content but relative from the luma sample
    locations. The _ChromaLocation property will be corrected to
    one that makes more sense (e.g. topleft instead of left).
    """
    if clip.format.color_family != ColorFamily.YUV:
        return clip

    def shift_centered_chroma(
        n: int,
        f: VideoFrame,
        plane_fields: VideoNode,
        field_shifts: Mapping[Optional[int], VideoNode]
    ):
        props = f.props
        if props.get('_ChromaLocation') in VERTICAL_CENTER_CHROMA_LOCS:
            return field_shifts[props.get('_Field')]
        else:
            # Assume was already vertically co-sited
            return plane_fields

    y, cb, cr = clip.std.SplitPlanes()
    shifted_planes = [y]
    for plane in cb, cr:
        plane_fields = plane.std.SeparateFields(tff=tff)
        shifted_as_top = shift_kernel(plane_fields, src_top=-1 / 4)
        shifted_as_bottom = shift_kernel(plane_fields, src_top=1 / 4)
        field_shifts = {
            None: shifted_as_top if tff else shifted_as_bottom,
            0: shifted_as_bottom,
            1: shifted_as_top
        }

        shifted_plane_fields = plane_fields.std.FrameEval(
            eval=partial(
                shift_centered_chroma,
                plane_fields=plane_fields,
                field_shifts=field_shifts
            ),
            prop_src=(plane_fields,),
            clip_src=(plane_fields, shifted_as_top, shifted_as_bottom)
        )
        shifted_planes.append(
            shifted_plane_fields.std.DoubleWeave()[::2]
        )
    shifted = core.std.ShufflePlanes(
        clips=shifted_planes,
        planes=(0, 0, 0),
        colorfamily=ColorFamily.YUV
    )

    def revise_frame_props(n: int, f: VideoFrame):
        props = f.props
        corrected_f = f.copy()
        if '_ChromaLocation' in props:
            corrected_f.props['_ChromaLocation'] = (
                VERTICAL_CENTER_CHROMA_LOCS.get(
                    props['_ChromaLocation'],
                    props['_ChromaLocation']
                )
            )
            return corrected_f
        return f

    shifted = shifted.std.ModifyFrame(
        clips=(shifted,),
        selector=revise_frame_props
    )

    return shifted


def annotate_bobbed_fields(
    clip: VideoNode,
    original_clip: VideoNode,
    prop: str = 'OriginalField',
    tff: Optional[bool] = None
) -> VideoNode:
    """Adds a property to frames of a bobbed clip to indicate what
    original field position was used to derive the new frame."""
    assert len(clip) == len(original_clip) * 2

    def annotate_frame(n: int, f: Sequence[VideoFrame]):
        bobbed_frame, original_frame = f
        field_based = original_frame.props.get('_FieldBased')
        if field_based == FieldBased.FIELD_TOP:
            tff_int = 1
        elif field_based == FieldBased.FIELD_BOTTOM:
            tff_int = 0
        elif tff is None:
            raise Error(
                'Could not determine field order and tff argument not '
                'supplied.'
            )
        else:
            tff_int = int(tff)

        annotated_frame = bobbed_frame.copy()
        annotated_frame.props[prop] = (n & 1) ^ tff_int
        return annotated_frame

    return clip.std.ModifyFrame(
        clips=(clip, double(original_clip)),
        selector=annotate_frame
    )
