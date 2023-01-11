from fractions import Fraction
from itertools import cycle, islice
from math import ceil, floor
from typing import Callable, Optional, Sequence

from vapoursynth import VideoFrame, VideoNode, core

from vsfieldkit.util import convert_format_if_needed, spline36_cb_cr_only


def telecine(
    clip: VideoNode,
    *,
    tff: bool,
    pulldown_pattern: Optional[str] = None,
    fpsnum: Optional[int] = None,
    fpsden: Optional[int] = 1,
    interlace_progressive_chroma: bool = True,
    pre_subsample_fields: bool = False,
    subsampling_kernel: Callable = spline36_cb_cr_only,
    upsampling_kernel: Callable = spline36_cb_cr_only,
    dither_type: str = 'random'
) -> VideoNode:
    """Spreads the clip's frames across interlaced fields to produce an
    interlaced clip.
    """
    if pre_subsample_fields and clip.format.subsampling_h > 0:
        y, cb, cr = clip.std.SplitPlanes()
        cb_halved = convert_format_if_needed(
            cb,
            kernel=subsampling_kernel,
            height=cb.height // 2
        )
        cr_halved = convert_format_if_needed(
            cr,
            kernel=subsampling_kernel,
            height=cr.height // 2
        )
        upsampled = core.std.ShufflePlanes(
            clips=(
                y,
                cb_halved.resize.Point(height=y.height),
                cr_halved.resize.Point(height=y.height)
            ),
            planes=(0, 0, 0),
            colorfamily=clip.format.color_family
        )
    else:
        upsampled = convert_format_if_needed(
            clip,
            subsampling_h=0,
            kernel=upsampling_kernel,
            dither_type=dither_type
        )

    if pulldown_pattern:
        interlaced = _telecine_by_pattern(
            clip,
            upsampled,
            pulldown_pattern=pulldown_pattern,
            tff=tff,
            pre_subsample_fields=pre_subsample_fields,
            interlace_progressive_chroma=interlace_progressive_chroma,
            subsampling_kernel=subsampling_kernel,
            dither_type=dither_type,
        )
    elif fpsnum:
        interlaced = _telecine_by_time(
            clip,
            upsampled,
            fps=Fraction(fpsnum, fpsden),
            tff=tff,
            pre_subsample_fields=pre_subsample_fields,
            interlace_progressive_chroma=interlace_progressive_chroma,
            subsampling_kernel=subsampling_kernel,
            dither_type=dither_type
        )
    else:
        raise ValueError('Either pulldown_pattern or fpsnum is required.')

    return interlaced


def _pulldown_pattern_to_field_offsets(
    pattern: Sequence[int]
) -> Sequence[int]:
    offsets_pattern = []
    lapsed_duration = 0
    field_idx = 0
    for frame_duration in pattern:
        field_offsets = cycle((field_idx, field_idx + 1))
        pulled_down_field_offsets = islice(
            field_offsets,
            lapsed_duration,
            lapsed_duration + frame_duration
        )
        offsets_pattern.extend(pulled_down_field_offsets)
        lapsed_duration += frame_duration
        field_idx += 2
    return offsets_pattern


def _telecine_by_pattern(
    clip: VideoNode,
    upsampled_clip: VideoNode,
    pulldown_pattern: str,
    pre_subsample_fields: bool,
    subsampling_kernel: Callable,
    dither_type: str,
    interlace_progressive_chroma: bool,
    tff: bool
) -> VideoNode:
    pattern_parts = [
        int(field_duration)
        for field_duration
        in pulldown_pattern.split(':')
    ]
    pattern_duration = sum(pattern_parts)
    if pattern_duration % 2 != 0:
        # Abbreviated pattern.
        # Run twice, so we don't end on half a frame.
        pattern_parts *= 2
    orig_cycle_size = len(pattern_parts)
    offsets_pattern = _pulldown_pattern_to_field_offsets(pattern_parts)

    as_fields = upsampled_clip.std.SeparateFields(tff=tff)
    pulled_down_fields = as_fields.std.SelectEvery(
        cycle=orig_cycle_size * 2,
        offsets=offsets_pattern
    )
    interlaced = pulled_down_fields.std.DoubleWeave()[::2]

    # Resample our upsampled fields if required:
    if pre_subsample_fields:
        interlaced = interlaced.resize.Point(format=clip.format)
    else:
        interlaced = convert_format_if_needed(
            interlaced,
            format=clip.format,
            kernel=subsampling_kernel,
            dither_type=dither_type
        )

    if not interlace_progressive_chroma:
        # Restore original progressive frames but with interlaced metadata
        # First create a map of clean frames in new cycle pointing to
        # original frames in source cycle
        clean_frame_sources = {}
        for field_idx in range(0, len(offsets_pattern), 2):
            field_offset_1, field_offset_2 = (
                offsets_pattern[field_idx:field_idx + 2]
            )
            if (
                (field_offset_2 == field_offset_1 + 1)
                and field_offset_1 % 2 == 0
            ):
                clean_frame_sources[field_idx // 2] = (
                        field_offset_1 // 2
                )
        frame_cycle_size = len(offsets_pattern) // 2

        def restore_original_frames(n: int, f: VideoFrame):
            cycle_idx = floor(n // frame_cycle_size)
            frame_idx_in_cycle = n % frame_cycle_size
            if frame_idx_in_cycle in clean_frame_sources:
                orig_frame_offset = clean_frame_sources[frame_idx_in_cycle]
                orig_frame_num = (
                    (cycle_idx * orig_cycle_size)
                    + orig_frame_offset
                )
                orig_frame = clip.get_frame(orig_frame_num)
                fake_interlaced_frame = orig_frame.copy()
                fake_interlaced_frame.props = dict(f.props)
                return fake_interlaced_frame
            return f

        interlaced = interlaced.std.ModifyFrame(
            clips=(interlaced,),
            selector=restore_original_frames
        )
    return interlaced


def _telecine_by_time(
    clip: VideoNode,
    upsampled_clip: VideoNode,
    fps: Fraction,
    tff: bool,
    interlace_progressive_chroma: bool,
    pre_subsample_fields: bool,
    subsampling_kernel: Callable,
    dither_type: str,
) -> VideoNode:
    original_length = len(clip)
    original_fps = clip.fps
    original_duration = Fraction(original_length, clip.fps)
    original_fields = upsampled_clip.std.SeparateFields(tff=tff)
    new_length = ceil(fps * original_duration)
    new_clip = upsampled_clip.std.BlankClip(
        length=new_length,
        fpsnum=fps.numerator,
        fpsden=fps.denominator
    )
    new_fields = new_clip.std.SeparateFields(tff=tff)
    new_field_rate = new_fields.fps

    def select_original_frame_field(n: int, f: VideoFrame):
        time_at_new_start = Fraction(n, new_field_rate)
        orig_frame_num = floor(time_at_new_start * original_fps)
        orig_field_num = (orig_frame_num * 2) + (n % 2)
        orig_field_frame = original_fields.get_frame(orig_field_num)

        new_field_frame = orig_field_frame.copy()
        new_field_frame.props['_DurationNum'] = f.props['_DurationNum']
        new_field_frame.props['_DurationDen'] = f.props['_DurationDen']
        return new_field_frame

    new_fields = new_fields.std.ModifyFrame(
        selector=select_original_frame_field,
        clips=(new_fields,)
    )

    interlaced = new_fields.std.DoubleWeave()[::2]
    interlaced = convert_format_if_needed(
        interlaced,
        format=clip.format,
        kernel=subsampling_kernel
    )

    # Resample our upsampled fields if required:
    if pre_subsample_fields:
        interlaced = interlaced.resize.Point(format=clip.format)
    else:
        interlaced = convert_format_if_needed(
            interlaced,
            format=clip.format,
            kernel=subsampling_kernel,
            dither_type=dither_type
        )

    if not interlace_progressive_chroma:
        def restore_original_frames(n: int, f: VideoFrame):
            time_at_1st_field = Fraction(n, fps)
            time_at_2nd_field = time_at_1st_field + Fraction(1, new_field_rate)
            orig_1st_field_frame_n = floor(time_at_1st_field * original_fps)
            orig_2nd_field_frame_n = floor(time_at_2nd_field * original_fps)
            if orig_1st_field_frame_n == orig_2nd_field_frame_n:
                orig_frame: VideoFrame = clip.get_frame(orig_1st_field_frame_n)
                fake_interlaced_frame = orig_frame.copy()
                fake_interlaced_frame.props = dict(f.props)
                return fake_interlaced_frame
            return f

        interlaced = interlaced.std.ModifyFrame(
            clips=(interlaced,),
            selector=restore_original_frames
        )

    return interlaced
