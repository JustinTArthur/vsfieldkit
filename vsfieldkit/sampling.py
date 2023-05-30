import math
import sys
from fractions import Fraction
from typing import Optional, Union

from vapoursynth import Error, VideoNode, core

from vsfieldkit.types import FormatSpecifier, Resizer
from vsfieldkit.util import convert_format_if_needed, format_from_specifier, \
    black_clip_from_clip, black_color_from_clip

BT601_SAMPLE_RATE = 13_500_000
NTSC_SUBCARRIER_FREQ = 5_000_000 * Fraction(63, 88)
NTSC_LINE_FREQ = Fraction(2, 455) * NTSC_SUBCARRIER_FREQ
NTSC_FIELD_FREQ = Fraction(2, 525) * NTSC_LINE_FREQ
NTSC_LINE_TIME = 1 / NTSC_LINE_FREQ

NTSC_170M_LEAD_BLANKING_TIME = Fraction(1_500, 1000000000)
NTSC_170M_TAIL_BLANKING_TIME = Fraction(9_200, 1000000000)
NTSC_170M_LINE_BLANKING_TIME = (
    NTSC_170M_LEAD_BLANKING_TIME
    + NTSC_170M_TAIL_BLANKING_TIME
)
NTSC_170M_LINE_ACTIVE_TIME = NTSC_LINE_TIME - NTSC_170M_LINE_BLANKING_TIME
NTSC_170M_ACTIVE_BT601_SAMPLES = (
    # Fraction(14271, 20) or 713.55
    NTSC_170M_LINE_ACTIVE_TIME
    * BT601_SAMPLE_RATE
)

NTSC_BT470_LINE_BLANKING_TIME = Fraction(10_900, 1000000000)
NTSC_BT470_LINE_ACTIVE_TIME = (
    NTSC_LINE_TIME
    - NTSC_BT470_LINE_BLANKING_TIME
)
NTSC_BT470_LINE_ACTIVE_BT601_SAMPLES = (
    # Fraction(14217, 20) or 710.85
    NTSC_BT470_LINE_ACTIVE_TIME
    * BT601_SAMPLE_RATE
)

PAL_LINE_FREQ = 15_625
PAL_SUBCARRIER_FREQ = (
    Fraction(1135, 4)
    + Fraction(1, 625)
) * PAL_LINE_FREQ
PAL_SUBCARRIER_FREQ_ARGENTINA = (
    Fraction(917, 4)
    + Fraction(1, 625)
)
# fOR = 282 * PAL_LINE_FREQ
# fOB = 272 * PAL_LINE_FREQ
PAL_LINE_TIME = Fraction(1, PAL_LINE_FREQ)
PAL_LINE_BLANKING_TIME = Fraction(12_000, 1000000000)
PAL_LINE_ACTIVE_TIME = PAL_LINE_TIME - PAL_LINE_BLANKING_TIME
PAL_ACTIVE_BT601_SAMPLES = (
    # 702
    PAL_LINE_ACTIVE_TIME
    * BT601_SAMPLE_RATE
)
NTSC_4FSC = 4 * NTSC_SUBCARRIER_FREQ
NTSC_4FSC_ACTIVE_WIDTH = NTSC_4FSC * NTSC_170M_LINE_ACTIVE_TIME
# Fraction(33299, 44) or 756.7954545454545
# Some tools use 758 as a multiple of 8
NTSC_4FSC_ACTIVE_HEIGHT = 486  # TODO: exact

PAL_4FSC = 4 * PAL_SUBCARRIER_FREQ
PAL_4FSC_ACTIVE_WIDTH = PAL_4FSC * PAL_LINE_ACTIVE_TIME 
#  Fraction(9221927, 10000) or 922.1927
# Some tools use 928 as a multiple of 8.


def resample_bt601_as_4fsc(
    clip: VideoNode,
    target_height: Optional[int] = None,
    kernel: Resizer = core.resize.Spline36,
    format: Optional[FormatSpecifier] = None,
    output_width_factor: Optional[int] = 8,
    dither_type='random',
    blank_src_pad=True,
    **format_resize_args
) -> VideoNode:
    """Takes a clip sampled from analog video according to the BT.601 spec
    and generates new video as if sampled at four times the color sub-carrier
    frequency (4fSC) of the theoretical original signal instead. Optionally
    changes the sample format in the same transformation.

    Because BT.601-sampled content from 525-line/NTSC-like systems is often
    cropped to 480i and 4fsc content is rarely cropped, this defaults to
    positioning 480i on a 486i canvas for the 4fSC output. This behavior can
    be overriden with target_height=480

    The BT.601 spec outlines expected colorimetry of the transported video
    content. However, this function leaves colorimetry untouched, focusing on
    sample rates and picture geometry. Additionaly note, the output clip
    comprises decoded video samples (e.g. Gray, R′G′B′, or Y′CbCr) and not pure
    4fSC signal sample values.
    """
    if clip.width != 720:
        raise Error('Only full active BT.601 width (720 samples) is supported')

    if clip.height == 576:
        # Full height of ITU BT.470 and BT.1700 PAL active video.
        src_active_width = PAL_ACTIVE_BT601_SAMPLES
        target_active_width = PAL_4FSC_ACTIVE_WIDTH
        src_original_top = None
    elif clip.height == 480:
        src_active_width = NTSC_170M_ACTIVE_BT601_SAMPLES
        target_active_width = NTSC_4FSC_ACTIVE_WIDTH
        # Assume vertical SMPTE RP 202 crop of ST 170M NTSC for compression.
        # This is 5 lines below the 486i start.
        src_original_top = -5
        if target_height is None:
            target_height = 486
    elif clip.height == 486:
        # Full height of SMPTE 170M active video
        src_active_width = NTSC_170M_ACTIVE_BT601_SAMPLES
        target_active_width = NTSC_4FSC_ACTIVE_WIDTH
        src_original_top = None
    else:
        raise Error('480i, 486i, or 576i height required for BT.601 source')

    return _resample_digitized_active_regions(
        clip,
        src_active_width=src_active_width,
        src_original_top=src_original_top,
        target_height=target_height,
        target_active_width=target_active_width,
        output_width_factor=output_width_factor,
        blank_src_pad=blank_src_pad,
        format=format,
        kernel=kernel,
        **format_resize_args
    )


def resample_4fsc_as_bt601(
    clip: VideoNode,
    target_height: Optional[int] = None,
    format: Optional[FormatSpecifier] = None,
    kernel: Resizer = core.resize.Spline36,
    **format_resize_args
):
    if target_height not in (None, 480, 486, 576):
        raise Error('Target height must be 480, 486, or 576.')

    if clip.height == 576:
        # Full height of ITU BT.470 and BT.1700 PAL active video.
        src_active_width = PAL_4FSC_ACTIVE_WIDTH
        target_active_width = PAL_ACTIVE_BT601_SAMPLES
    elif clip.height == 486:
        # Full height of SMPTE 170M active video
        src_active_width = NTSC_4FSC_ACTIVE_WIDTH
        target_active_width = NTSC_170M_ACTIVE_BT601_SAMPLES
        if target_height == 480:
            # Assume wanting RP 202 crop.
            clip = clip.std.Crop(top=5, bottom=1)
    elif clip.height == 480:
        src_active_width = NTSC_4FSC_ACTIVE_WIDTH
        target_active_width = NTSC_170M_ACTIVE_BT601_SAMPLES
        # Leave the crop as-is.
    else:
        raise Error('480i, 486i, or 576i height required for 4fSC source')

    return _resample_digitized_active_regions(
        clip,
        src_active_width=src_active_width,
        target_height=target_height,
        target_width=720,
        target_active_width=target_active_width,
        format=format,
        kernel=kernel,
        **format_resize_args
    )


def _resample_digitized_active_regions(
    clip: VideoNode,
    src_active_width: Union[int, Fraction],
    target_active_width: Union[int, Fraction],
    kernel: Resizer,
    src_original_top: Optional[Union[int, Fraction]] = None,
    target_height: Optional[int] = None,
    target_width: Optional[int] = None,
    format: Optional[FormatSpecifier] = None,
    output_width_factor: int = 8,
    blank_src_pad: Optional[bool] = True,
    **format_resize_args
) -> VideoNode:
    whole_target_width = math.ceil(target_active_width)
    if (
        (not target_width)
        and (whole_target_width % output_width_factor == 0)
    ):
        target_width = whole_target_width
    elif not target_width:
        target_width = (
            whole_target_width
            + (
                output_width_factor
                - (whole_target_width % output_width_factor)
            )
        )
    target_horizontal_pad = target_width - target_active_width
    src_horizontal_pad = (
        (src_active_width / target_active_width)
        * target_horizontal_pad
    )
    src_left_pad = src_horizontal_pad / 2

    src_original_horizontal_pad = clip.width - src_active_width
    src_original_left_pad = src_original_horizontal_pad / 2

    src_clip = clip
    src_left = src_original_left_pad - src_left_pad
    print(f'{src_left=}', file=sys.stderr)
    if blank_src_pad and src_left < 0:
        # Sourcing samples further left than actual source clip.
        extend_by = math.ceil(0 - src_left)
        blanking_color = black_color_from_clip(src_clip)
        src_clip = src_clip.std.AddBorders(
            left=extend_by,
            right=extend_by,
            color=blanking_color
        )
        print(f'{src_clip.width=}', file=sys.stderr)
        src_original_horizontal_pad = src_clip.width - src_active_width
        src_original_left_pad = src_original_horizontal_pad / 2
        src_left = src_original_left_pad - src_left_pad
    src_width = src_active_width + src_horizontal_pad

    target_format = format_from_specifier(format) if format else None
    return convert_format_if_needed(
        clip,
        format=target_format,
        kernel=kernel,
        width=target_width,
        src_left=float(src_left),
        src_top=(
            None if src_original_top is None
            else float(src_original_top)
        ),
        src_width=float(src_width),
        src_height=(
            None if target_height is None
            else float(target_height)
        ),
        **format_resize_args
    )
