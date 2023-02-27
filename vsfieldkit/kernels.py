from typing import Callable, Optional, Union

from vapoursynth import (ColorFamily, Error, PresetFormat, VideoFormat,
                         VideoNode, core)

from vsfieldkit.util import (annotate_bobbed_fields, require_plugins,
                             shift_chroma_to_luma_sited, format_from_specifier)

resample_nearest_neighbor = core.resize.Point


def prepare_nnedi3_chroma_upsampler(
    shift_kernel: Callable = core.resize.Spline36,
    nsize: Optional[int] = None,
    nns: Optional[int] = None,
    qual: Optional[int] = None,
    etype: Optional[int] = None,
    pscrn: Optional[int] = None,
    opt: Optional[bool] = None,
    int16_prescreener: Optional[bool] = None,
    int16_predictor: Optional[bool] = None,
    exp: Optional[int] = None,
    show_mask: Optional[bool] = None
) -> Callable:
    """Creates a resampling function that uses the nnedi3 interpolation model
    originally made for deinterlacing to produce a clip without vertical chroma
    subsampling. The resampling function will use the given nnedi3 parameters.

    This resampling function will act like a typical VapourSynth
    resize kernel, but will only work for format changes in vertical
    subsampling, going from Y′CbCr 4:2:0 to Y′CbCr 4:2:2 or Y′CbCr 4:4:0 to
    Y′CbCr 4:4:4. Attempting to make any other light/color/sampling changes
    will result in an error.
    """
    def upsample_chroma_using_nnedi3(
        clip: VideoNode,
        format: Union[VideoFormat, PresetFormat] = None,
        *resize_args,
        **resize_kwargs
    ) -> VideoNode:
        """Given a clip with half-size (subsampled) vertical chroma, fills in
        missing vertical detail using the nnedi3 interpolation model originally
        made for deinterlacing to produce a clip without vertical chroma
        subsampling.
        """
        require_plugins(('nnedi3', 'nnedi3'))

        if (
            clip.format.subsampling_h != 1
            or format is None
            or format_from_specifier(format) != clip.format.replace(subsampling_h=0)
        ):
            raise Error(
                'upsample_chroma_using_nnedi3 is currently only for format '
                'conversion from Y′CbCr 4:2:0 to Y′CbCr 4:2:2 or Y′CbCr 4:4:0 '
                'to Y′CbCr 4:4:4.'
            )

        y, cb, cr = clip.std.SplitPlanes()
        # We're using TFF (field=3). It doesn't really matter what order we bob
        # in, as long as we're consistent when we annotate for re-weaving.
        bobbed_cb = cb.nnedi3.nnedi3(field=3, nsize=nsize, nns=nns, qual=qual,
                                     etype=etype, pscrn=pscrn, opt=opt,
                                     int16_prescreener=int16_prescreener,
                                     int16_predictor=int16_predictor, exp=exp,
                                     show_mask=show_mask)
        bobbed_cr = cr.nnedi3.nnedi3(field=3, nsize=nsize, nns=nns, qual=qual,
                                     etype=etype, pscrn=pscrn, opt=opt,
                                     int16_prescreener=int16_prescreener,
                                     int16_predictor=int16_predictor, exp=exp,
                                     show_mask=show_mask)
        # These are effectively bobbed.
        # Treat the bobs as if they were plain separated fields
        bobbed_cb = annotate_bobbed_fields(
            bobbed_cb,
            original_clip=cb,
            tff=True,
            prop='_Field'
        )
        bobbed_cr = annotate_bobbed_fields(
            bobbed_cr,
            original_clip=cr,
            tff=True,
            prop='_Field'
        )
        reinterlaced_cb = core.std.DoubleWeave(bobbed_cb)[::2]
        reinterlaced_cr = core.std.DoubleWeave(bobbed_cr)[::2]

        upsampled = core.std.ShufflePlanes(
            clips=(y, reinterlaced_cb, reinterlaced_cr),
            planes=(0, 0, 0),
            colorfamily=ColorFamily.YUV
        )
        # Any downstream operations will consider the chroma loocation
        # to be vertically co-sited with luma samples now that we're 4:2:2,
        # so resample relative to luma site if we started from vertically
        # centered chroma siting.
        chromaloc_corrected = shift_chroma_to_luma_sited(
            upsampled,
            tff=True,
            shift_kernel=shift_kernel
        )
        return chromaloc_corrected
    return upsample_chroma_using_nnedi3


def _prepare_chroma_only_resampler(resampler_name: str) -> Callable:
    def chroma_only_resampler(*resize_args, **resize_kwargs) -> VideoNode:
        return resample_nearest_neighbor(
            *resize_args,
            **resize_kwargs,
            resample_filter_uv=resampler_name
        )

    try:
        annotations = getattr(resample_nearest_neighbor, '__annotations__')
    except AttributeError:
        pass
    else:
        setattr(chroma_only_resampler, '__annotations__', annotations)

    chroma_only_resampler.__name__ = f'resample_chroma_with_{resampler_name}'
    chroma_only_resampler.__qualname__ = (
        f'resample_chroma_with_{resampler_name}'
    )
    chroma_only_resampler.__doc__ = (
        f'Assumes that the clip is Y′CbCr and that only the Cb and Cr planes '
        f'are being resized. The Cb and Cr planes will be resampled with '
        f'{resampler_name}. The Y′ plane will be resampled with the nearest '
        f'neighbour (point) method to ensure unaltered passthrough.'
    )

    return chroma_only_resampler


resample_chroma_with_bicubic = _prepare_chroma_only_resampler('bicubic')
resample_chroma_with_bilinear = _prepare_chroma_only_resampler('bilinear')
resample_chroma_with_lanczos = _prepare_chroma_only_resampler('lanczos')
resample_chroma_with_spline16 = _prepare_chroma_only_resampler('spline16')
resample_chroma_with_spline36 = _prepare_chroma_only_resampler('spline36')
resample_chroma_with_spline64 = _prepare_chroma_only_resampler('spline64')
