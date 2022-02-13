from collections.abc import Mapping, Sequence
from typing import Callable, Optional

from vapoursynth import YUV, ColorFamily, FieldBased, VideoNode, core

from vsfieldkit.types import (ChromaSubsampleScanning,
                              InterlacedScanPostProcessor)
from vsfieldkit.util import assume_progressive, convert_format_if_needed

post_processing_routines: Mapping[InterlacedScanPostProcessor, Callable]


def scan_interlaced(
    clip: VideoNode,
    warmup_clip: Optional[VideoNode] = None,
    tff: Optional[bool] = None,
    chroma_subsample_scanning: ChromaSubsampleScanning = (
        ChromaSubsampleScanning.SCAN_LATEST
    ),
    dither_type: str = 'random',
    post_processing: Sequence[InterlacedScanPostProcessor] = (),
    post_processing_blend_kernel: Callable = core.resize.Spline36,
) -> VideoNode:
    """
    Returns a new clip where interlaced fields from the original clip are
    painted onto each frame in their correct position moment-by-moment like an
    interlaced scan display would. This is sometimes referred to as phosphor
    deinterlacing. Like bob deinterlacing, it doubles the amount of frames
    (and frame rate accordingly) produced to portray the moments represented in
    the interlaced footage."""
    # TFF (w is warmup field)
    # Top field source: 1 1 2 2 3 3 4 4 5 5
    # Bot field source: w 1 1 2 2 3 3 4 4 5
    # Desired Result:   1a+wb 1a+1b 2a+1b 2a+2b 3a+2b

    # BFF
    # Top field source: w 1 1 2 2 3 3 4 4 5
    # Bot field source: 1 1 2 2 3 3 4 4 5 5
    # Desired Result:   wa+1b 1a+1b 2a+1b 2a+2b 3a+2b

    if not warmup_clip:
        warmup_clip = clip.std.BlankClip(length=1)
        warmup_clip = warmup_clip.std.CopyFrameProps(clip[0])
    else:
        warmup_clip = warmup_clip[-1]

    # Upsample the footage to have single line height chroma resolution if it
    # doesn't already so that we can persist the exact chroma layout we want to
    # the final "progressive" frame before downsampling back to 4:2:0 if
    # requested.
    scannable_clip = convert_format_if_needed(clip, subsampling_h=0)
    scannable_warmup = convert_format_if_needed(warmup_clip, subsampling_h=0)
    chroma_upsampled = (scannable_clip.format.id != clip.format.id)

    original_fields = scannable_clip.std.SeparateFields(tff=tff)
    warmup_fields = scannable_warmup.std.SeparateFields(tff=tff)

    # Pick out the field position not about to be initialized by main clip
    first_field = original_fields.get_frame(0).props._Field
    for field_frame_clip in warmup_fields:
        field_frame = field_frame_clip.get_frame(0)
        if field_frame.props._Field != first_field:
            warmup_field = field_frame_clip
            break
    else:
        raise ValueError("Couldn't determine warmup field from supplied clip.")

    # To achieve the updating and repeating of fields, we can rely on the same
    # functions used to interlace. We just need to ensure every field is
    # interlaced twice except for the last one.
    recycled_fields = original_fields.std.SelectEvery(
        cycle=2,
        offsets=(0, 1, 0, 1),
        modify_duration=True
    )[:-1]
    synced_warmup_field = warmup_field.std.AssumeFPS(src=recycled_fields)

    # Insert our warm-up field in a way that scans the interlaced material
    # in the same field order it came in. Probably not required.
    phosphor_fields = (
        recycled_fields[0]
        + synced_warmup_field
        + recycled_fields[1:]
    )
    if (
        chroma_upsampled
        and chroma_subsample_scanning == ChromaSubsampleScanning.SCAN_LATEST
    ):
        phosphor_fields = _repeat_new_field_chroma(phosphor_fields)

    laced = core.std.DoubleWeave(phosphor_fields, tff=True)[::2]
    as_progressive = assume_progressive(laced)

    post_processed = as_progressive
    for step in post_processing:
        process = post_processing_routines[step]
        post_processed = process(post_processed,
                                 kernel=post_processing_blend_kernel)

    if chroma_subsample_scanning == ChromaSubsampleScanning.SCAN_UPSAMPLED:
        # Restore the upsampled format in case changed by post-processing.
        # Restore original bit depth:
        return convert_format_if_needed(
            post_processed,
            subsampling_w=scannable_clip.format.subsampling_w,
            subsampling_h=scannable_clip.format.subsampling_h,
            bits_per_sample=clip.format.bits_per_sample,
            dither_type=dither_type
        )
    else:
        return convert_format_if_needed(
            post_processed,
            format=clip.format,
            dither_type=dither_type
        )


def _repeat_new_field_chroma(clip: VideoNode, offset=0):
    """Returns a new clip of scanned field frames where the chroma plane from
    the first field of a final frame is copied over the next frame's chroma,
    then the 3rd frame's chroma is copied over the 4th, etc."""
    if offset:
        pre_offset = clip[:offset]
        edit_range = clip[offset:]
    else:
        pre_offset = None
        edit_range = clip

    # Given a scan from TFF:
    # NewTop  WarmupBtm OldTop  NewBtm  NewTop  OldBtm  OldTop NewBtm  NewTop…
    # Source1 Target1   Target2 Source2 Source3 Target3 Target4 Source4
    # Source Cadence:
    # 0 3 4 7 8
    # Target Cadence:
    # 1 2 5 6 9
    # If then interleaved:
    # 0 1 3 2 4 5 7 6 8 9
    source_frames = edit_range.std.SelectEvery(
        cycle=4,
        offsets=(0, 3),
        modify_duration=False
    )
    target_frames = edit_range.std.SelectEvery(
        cycle=4,
        offsets=(1, 2),
        modify_duration=False
    )
    overwritten_target = core.std.ShufflePlanes(
        clips=(target_frames, source_frames, source_frames),
        planes=(0, 1, 2),
        colorfamily=ColorFamily.YUV
    )
    edited_interleaved = core.std.Interleave(
        (source_frames, overwritten_target),
        modify_duration=False
    )
    edited_ordered = edited_interleaved.std.SelectEvery(
        cycle=4,
        offsets=(0, 1, 3, 2),
        modify_duration=False
    )

    if offset:
        return pre_offset + edited_ordered
    return edited_ordered


def _blend_vertically(clip: VideoNode, kernel: Callable) -> VideoNode:
    """Instead of typical Bob deinterlacing that takes advantage of temporal
    changes in a field, this deinterlacer simply plays back the interlaced
    fields at their original field rate in their correct position, but blends
    each moment.

    This is a nice fallback when the original material flickers in a
    bob-deinterlacer, is smooth when played back at original field refresh rate
    (like on an old CRT), but combing is still undesirable.
    """

    # Process at high bit depth, assume will be restored downstream.
    processing_format_reqs = {
        'subsampling_h': 0,
        'subsampling_w': 0
    }
    if clip.format.bits_per_sample < 16:
        processing_format_reqs['bits_per_sample'] = 16
    downscaled = convert_format_if_needed(
        clip,
        height=clip.height // 2,
        kernel=kernel,
        **processing_format_reqs
    )
    rescaled = kernel(downscaled, height=clip.height)
    return rescaled


post_processing_routines = {
    InterlacedScanPostProcessor.BLEND_VERTICALLY: _blend_vertically
}
