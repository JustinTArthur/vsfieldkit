from typing import Iterator, Optional, Tuple, Union

from vapoursynth import FieldBased, VideoFormat, VideoNode, core

FORMAT_INTRINSICS = (
    'color_family',
    'sample_type',
    'subsampling_w',
    'subsampling_h',
    'bits_per_sample'
)


def assume_bff(clip: VideoNode):
    return clip.std.SetFrameProp(
        prop='_FieldBased',
        intval=FieldBased.FIELD_BOTTOM.value
    )


def assume_tff(clip: VideoNode):
    return clip.std.SetFrameProp(
        prop='_FieldBased',
        intval=FieldBased.FIELD_TOP.value
    )


def assume_progressive(clip: VideoNode) -> VideoNode:
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
    clip.

    This does not have any built-in comb detection.

    Example:

        progressive_clips = []
        detelecined = tivtc.TFM(clip)
        for is_combed, segment in vsfieldkit.group_by_combed(detelecined):
            if is_combed:
                progressive_clips.append(havsfunc.QTGMC(segment, TFF=False))
            else:
                progressive_clips.append(tivtc.TDecimate(segment, tff))
        vs.core.std.Splice(progressive_clips).set_output()

    """
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
    applicable or not available.

    Example:

        progressive_clips = []
        for field_based, segment in vsfieldkit.group_by_field_order(clip):
            if field_based == vs.FIELD_TOP:
                progressive_clips.append(havsfunc.QTGMC(segment, TFF=True))
            elif field_based == vs.FIELD_BOTTOM:
                progressive_clips.append(havsfunc.QTGMC(segment, TFF=False))
            elif field_based == vs.PROGRESSIVE:
                progressive_clips.append(vsfieldkit.double(segment))
        vs.core.std.Splice(progressive_clips).set_output()

    """
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
    kernel=core.resize.Spline36,
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
