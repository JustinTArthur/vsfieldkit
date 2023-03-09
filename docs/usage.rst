Usage
=====

Installation
------------
vsfieldkit is `hosted on PyPI <https://pypi.org/project/vsfieldkit/>`_ so it's
as simple as using your favorite installer:

.. code-block:: bash

    python -m pip install vsfieldkit

.. code-block:: bash

    poetry add vsfieldkit

To add to a specific scripts directory:


.. code-block:: bash

    python -m pip install --target=./my_scripts_dir vsfieldkit


The package uses semantic versioning to indicate backwards
compatible changes to the API.

As the developer does not have Windows, vsrepo is not officially supported.
That said, it seems to be able to install vsfieldkit.

Dependencies
^^^^^^^^^^^^
For most functions, just VapourSynth. The
:py:func:`~vsfieldkit.fill_analog_frame_ends` function requires the FillBorders
and either the ContinuityFixer or EdgeFixer plugins. Generating a resampling
kernel with :py:func:`~vsfieldkit.kernels.prepare_nnedi3_chroma_upsampler`
requires the nnedi3 plugin.

Functions
---------
Reinterpreting
^^^^^^^^^^^^^^
.. autofunction:: vsfieldkit.assume_bff(clip) -> VideoNode

.. autofunction:: vsfieldkit.assume_progressive(clip) -> VideoNode

    For progressive content that has been interlaced and has vertical chroma
    subsampling, :py:func:`vsfieldkit.resample_as_progressive` or
    :py:func:`vsfieldkit.upsample_as_progressive` could be considered as well.

.. autofunction:: vsfieldkit.assume_tff(clip) -> VideoNode

Deinterlacing
^^^^^^^^^^^^^
.. function:: vsfieldkit.bob(clip, shift=True, tff=None, \
        keep_field_property=True, kernel=core.resize.Spline36, \
        dither_type='random')

    A simple bob deinterlacer. Returns a clip of progressive frames, each
    consisting of a field from the original interlaced clip in order of its
    original capture. As interlaced fields have half the resolution of a given
    moment, the new frames are stretched up to the original clip's height.

    If shifting for playback comfort, VapourSynth R58 and above provides a
    built-in :py:func:`resize.Bob` that should be used instead as it provides
    near-identical functionality.

    :param VideoNode clip: Video with interlaced frames to bob into the
        resulting clip.

    :param bool shift: Whether to shift the lines during scaling to account for
        the field's position in a full frame. Recommended if the output is
        intended for playback.

    :param bool tff:
        Specifies the field order to assume when scanning progressive footage
        or clips without field order marking. ``True`` assumes top-field-first.
        ``False`` for bottom-field-first.

    :param Resizer kernel:
        Resampling/resizing function from vapoursynth.core.resize to use to
        stretch the fields to the target frame height. Defaults to
        :py:func:`resize.Spline36`.

    :param str dither_type:
        If video is processed at a higher bit depth internally before being
        returned to an original depth of less than 16 bits per plane, this
        dithering method will be used to avoid banding and other unnatural
        artifacts caused by rounding at low bit rate.

.. function:: vsfieldkit.resample_as_progressive( \
        clip, \
        subsampling_kernel=resample_chroma_with_spline36, \
        upsampling_kernel=resample_chroma_with_spline36, \
        dither_type='random' \
    ) -> VideoNode

    This can be used instead of :py:func:`vsfieldkit.assume_progressive`
    when progressive content has been encoded interlaced with vertical chroma
    subsampling.

    The primary use-case for this is removing 2:2 pulldown on 25p content
    that's been hard-telecined to 50i in DV, DVB, or DVD formats with 4:2:0
    chroma subsampling. It can also be used to resample chroma on frames
    created with field-matching that pulled up other pulldown patterns.

    When progressive content is encoded as interlaced pictures with 4:2:0
    chroma subsampling, the chroma samples span alternating instead of adjacent
    lines of a frame. Simply marking/assuming such clips as progressive could
    result in color samples being attributed to the wrong lines (bleeding), and
    in those cases this function can be used instead. It will prevent bleeding,
    though as this comes up with new samples for the progressive content, it
    results in loss of original color precision.

    If you wish to perform additional processing before the final chroma
    subsampling is restored, use :py:func:`vsfieldkit.upsample_as_progressive`
    instead.

    :param VideoNode clip: Video with progressive frames encoded as interlaced
        with vertical subsampling.

    :param Resizer subsampling_kernel:
        Resampling/resizing function to use to restore deinterlaced chroma to =
        the original chroma height. Defaults to
        :py:func:`vsfieldkit.kernels.resample_chroma_with_spline36`.

    :param Resizer upsampling_kernel:
        Resampling/resizing function to use for upsampling sub-sampled
        chroma. Must be interlacing-aware like most of VapourSynth's
        built in :external+vapoursynth:doc:`functions/video/resize` functions.
        Defaults to
        :py:func:`vsfieldkit.kernels.resample_chroma_with_spline36`.

        If the nnedi3 VapourSynth plugin is present,
        :py:func:`vsfieldkit.kernels.prepare_nnedi3_chroma_upsampler`
        can be used to create a suitable upsampling kernel employing
        the nnedi3 model.

    :param str dither_type:
        If video is processed at a higher bit depth internally before being
        returned to an original depth of less than 16 bits per plane, this
        dithering method will be used to avoid banding and other unnatural
        artifacts caused by rounding at low bit rate.

.. function:: vsfieldkit.scan_interlaced( \
        clip, \
        warmup_clip=None, \
        tff=None, \
        chroma_subsample_scanning=ChromaSubsampleScanning.SCAN_LATEST, \
        attack_factor=None, \
        decay_factor=None, \
        decay_base=None, \
        dither_type='random', \
        post_processing=(), \
        post_processing_blend_kernel=core.resize.Spline36, \
    ) -> VideoNode

    Returns a new clip where interlaced fields from the original clip are
    painted onto each frame in their correct position moment-by-moment like
    an interlaced scan display would. This is sometimes referred to as display
    interlacing, phosphor deinterlacing, or simply interlaced scan.
    Like bob deinterlacing, it doubles the amount of frames used to portray
    the moments represented in the interlaced footage.

    Interlaced content is typically stored or transmitted with two moments
    interlaced into one frame and each moment only appearing in that one frame.
    This balances the destructive compression of time and image resolution. The
    frames generated by ``scan_interlaced`` will repeat a field from the
    previous moment, losing that compression advantage. Additionally, they
    can't be treated as interlaced by downstream filters or playback systems
    that expect a field's picture to only appear once. Because of this, they
    are marked as progressive by the function. It might be better to call this
    function a "display interlacer" rather than a deinterlacer.

    This was inspired by `Juha Jeronen <https://github.com/Technologicat>`_'s
    wonderful Phosphor deinterlacer for VideoLAN's
    `VLC media player <https://www.videolan.org/vlc/>`_. This code was not
    derived from it, but it tries to at least keep the subsampling
    nomenclature the same.

    More background and some examples can be found in the
    :doc:`scan_interlaced_deep_dive`.

    :param VideoNode clip: Video with interlaced frames to scan to
        the resulting clip.

    :param VideoNode warmup_clip:
        The first field from the main clip will be painted alongside the last
        field of the warmup clip if supplied. This can allow seamless splicing
        of scan_interlace output with other clips. If no warmup clip is
        supplied, black scanlines are used to warm up that field.

    :param bool tff:
        Specifies the field order to assume when scanning progressive footage
        or clips without field order marking. ``True`` assumes top-field-first.
        ``False`` for bottom-field-first. Applies to the main clip and/or the
        warmup clip if either have not-explicitly-interlaced frames.

    :param ChromaSubsampleScanning chroma_subsample_scanning:
        When Chroma is sub-sampled vertically, such as in Y'CbCr 4:2:0 clips,
        a decision must be made on how to present the color of the newly-laced
        scan lines in the final frames because those frames will be marked as
        progressive. Progressive frames don't have chroma samples for
        alternating scan lines. Without a chroma scanning decision, the first
        line's color would bleed into the second line, which was scanned from a
        different moment, third into the fourth… resulting in thicker visual
        comb lines and lines having color untrue to their source material.

        Enumerations are available on the vsfieldkit top level module and the
        :py:class:`~vsfieldkit.ChromaSubsampleScanning` enum.

    :param Factor attack_factor:
        Amount by which to brighten lines that have been scanned in the
        current moment. Usually expressed as a
        :py:class:`float`, :py:class:`~decimal.Decimal` or
        :py:class:`~fractions.Fraction` where ``1`` means the newly
        scanned line is not brightened, ``2`` means the line is doubled
        in brightness.

    :param Factor decay_factor:
        Amount by which to dim the lines scanned in the previous moment,
        exposing the ``decay_base`` clip. This simulates the decay of cathode
        ray tube phosphors in the moments after they've been scanned onto and
        the persistence of vision in humans.

        Usually expressed as a :py:class:`float`, :py:class:`~decimal.Decimal`
        or :py:class:`~fractions.Fraction` where ``1`` means the
        previously-laced scan lines are completely replaced by lines from the
        decay_base clip, ``0.5`` means the clip is dimmed half and ``0`` means
        there is no dimming at all. ``decay_base`` can be used to dim
        to a background other than solid black.

    :param VideoNode decay_base:
        A background clip that previously-scanned scan lines should be dimmed
        to instead of black. Ignored if ``decay_factor`` is not set. Should be
        one frame long. The frame will be re-used.

    :param str dither_type:
        If video is processed at a higher bit depth internally before being
        returned to an original depth of less than 16 bits per plane, this
        dithering method will be used to avoid banding and other unnatural
        artifacts caused by rounding colors to the nearest integer.

    :param Sequence[InterlacedScanPostProcessor] post_processing:
        Post-processing steps to run on the frames resulting from interlaced
        scanning. At the moment, only
        :py:attr:`~vsfieldkit.InterlacedScanPostProcessor.BLEND_VERTICALLY` is
        available.

        Enumerations are available on the vsfieldkit top level module and the
        :py:class:`~vsfieldkit.InterlacedScanPostProcessor` enum.

.. function:: vsfieldkit.upsample_as_progressive(clip, \
        upsample_horizontally=False, \
        kernel=resample_chroma_with_spline36 \
    ) -> VideoNode

    Returns a clip now marked as progressive and with any vertical chroma
    subsampling removed so that previously-alternating chroma lines will be
    laid out in the correct one-line-after-another order for progressive
    content.

    This can be used instead of :py:func:`vsfieldkit.assume_progressive`
    when the progressive frames have been encoded interlaced and additional
    processing is desired before restoring the target chroma sub-sampling.

    .. code-block:: python
        :caption: Example

        # Interpret as progressive, removing vertical chroma subsampling
        upsampled = vsfieldkit.upsample_as_progressive(clip)

        # Additional processing:
        fixed_edges = awsmfunc.bbmod(upsampled, left=2, right=3)

        # Restore original subsampling with favorite kernel then output:
        resampled = fixed_edges.resize.Spline36(format=clip.format)
        resampled.set_output()

    :param bool upsample_horizontally:
        Whether or not to horizontally upsample. The function will always
        vertically upsample if applicable.

    :param Resizer kernel:
        Resampling/resizing function to use for upsampling sub-sampled
        chroma. Must be interlacing-aware like most of VapourSynth's
        built in :external+vapoursynth:doc:`functions/video/resize` functions.
        Defaults to
        :py:func:`vsfieldkit.kernels.resample_chroma_with_spline36`.

        If the nnedi3 VapourSynth plugin is present,
        :py:func:`vsfieldkit.kernels.prepare_nnedi3_chroma_upsampler`
        can be used to create a suitable upsampling kernel employing
        the nnedi3 model.

Interlacing
^^^^^^^^^^^
.. function:: vsfieldkit.telecine( \
        clip, \
        *, \
        tff, \
        pulldown_pattern=None, \
        fpsnum=None, \
        fpsden=1, \
        interlace_progressive_chroma=True, \
        pre_subsample_fields=False, \
        subsampling_kernel=resample_chroma_with_spline36, \
        upsampling_kernel=resample_chroma_with_spline36, \
        dither_type='random' \
    ) -> VideoNode
    
    Interlaces the given progressive clip by spreading its content over 
    interlaced fields according to a given interlaced frame rate or a given
    pull-down pattern.
    
    :param VideoNode clip:
        Progressive video to be interlaced. Must have an even height.
    
    :param bool tff:
        Whether the top field is the first field from the frame to be
        displayed during interlaced-aware playback. If False, the bottom
        field is first.
    
    :param typing.Union[str, PulldownPattern, None] pulldown_pattern:
        A string of numbers seperated by colons, where each number
        indicates for how many field durations to include each frame from
        the original clip in the new interlaced clip. A field duration is
        half the interlaced frame duration.
    
        For example, the popular "2:3" pattern will include the first
        original progressive frame for 2 field durations in the new
        interlaced clip. It will then include parts of the second original
        frame for 3 field durations. The pattern repeats, so the third
        original frame is included for 2 field durations of the new clip
        and so-on.

        Some common pulldown pattern enumerations are available on the
        top level module or the :py:class:`~vsfieldkit.PulldownPattern` enum.
        They can be supplied instead of a ``str``.
    
        Either ``pulldown_pattern`` or ``fpsnum`` must be supplied
    
    :param int fpsnum:
        The numerator of the speed of the new interlaced clip in
        frames-per-second. When supplied, the original progressive frames
        will be pulled down or up to stretch across interlaced fields so
        that parts of the original frame would be displayed at the same
        time they occurred in the original clip.
    
        A denominator can be supplied in the corresponding ``fpsden``
        argument.
    
        This allows flexibility of input and output frame rates and will
        consistently produce the lowest-judder interlaced representation
        of the original clip. For example, when going from 24000/1001
        progressive FPS to ``fpsnum=30_000`` and ``fpsden=1_001``, the
        footage will appropriately end up in the popular the 2:3 pulldown
        pattern (though may not start at the "2" in the cycle). Note that
        this virtual time-based telecine will drop original content if
        needed to meet the new time base.
    
    :param int fpsden:
        The denominator to use with a supplied ``fpsnum`` (numerator) for
        virtual time-based telecine. If not supplied, this defaults to
        ``1``.
    
    :param bool interlace_progressive_chroma:
        If ``False``, when both fields of an interlaced frame would come
        from the same original progressive frame, simply use that
        progressive frame and call it interlaced (fake interlacing). This
        results in material with vertical chroma subsampling remaining
        unbroken and unblurred if a downstream deinterlacer or display
        upsampler treats the clean frames as progressive.
    
        Defaults to ``True``.
    
    :param bool pre_subsample_fields:
        Crushes chroma to half its original resolution prior to upsampling
        for interlacing. This can be a way to produce output that is
        displayed consistently accross a variety of deinterlacers and
        display upsamplers that might otherwise be susceptible to artifacts
        from chroma upsampling error (CUE) or interlaced chroma problem
        (ICP).

    .. note::
        The word *telecine* is often ascribed to the process of scanning
        physical film media to digital video. This function does not interact
        with physical telecine systems or color suites. It is instead a
        virtual equivalent of what telecine machinery would accomplish when
        scanning physical film media to an interlaced video signal such as NTSC
        or PAL.

.. autofunction:: vsfieldkit.weave_fields(clip) -> VideoNode

Repair
^^^^^^
.. function:: vsfieldkit.fill_analog_frame_ends( \
        clip, \
        top_blank_width=None, \
        bottom_blank_width=None, \
        continuity_radius=(5,), \
        luma_splash_radius=1, \
        original_format=None, \
        restore_blank_detail=False, \
        prefill_mode='fillmargins' \
    ) -> VideoNode

    Fills the beginning and end half-lines from frames digitized from or
    for PAL/NTSC/SECAM signal. These lines are often half-blanked so that a CRT
    monitor's electron beam won't light up phosphors as it zig-zags from the
    bottom of screen to the top to start painting the next frame.

    It aims to interpolate only the missing data, leaving clean pixels
    in-tact. Interpolation is performed by repetition and averaging of adjacent
    line data using the FillBorders plugin followed by least-squares regression
    using the ContinuityFixer or EdgeFixer plugin.

    If the bottom black bar coincides with head-switching noise from a camera
    or VCR, the bottom bar repair will not be useful.

    :param VideoNode clip:
        Video from or for analog source. Can be in its original interlaced form
        or de-interlaced.

    :param int top_blank_width:
        Width in pixels of the top-left black bar at its longest, including any
        horizontal fade. If not supplied, assumed to be 65% of the top line.
        Set to ``0`` to not attempt top line repair.

    :param int bottom_blank_width:
        Width in pixels of the bottom-right black bar at its longest, including
        any horizontal fade. If not supplied, assumed to be 65% of the bottom
        line.  Set to ``0`` to not attempt bottom line repair.

    :param continuity_radius:
        Number of rows next to the black bar to use as input for interpolating
        the new pixels to generate inside the bar.
    :type continuity_radius: int or Sequence[int]

    :param int luma_splash_radius:
        Repair this many extra rows of luma data above or below the half line.
        Adjacent picture data is often damaged by the black bar if the video's
        fields are resized from their original signal height (e.g. from 486i
        to 480i for NTSC to fit a DVD or DV stream) or if the studio applied
        artificial sharpening.

        If the adjacent rows have correct brightness even if they're gray, this
        can be set to 0 to persist the clean luma data. The function's
        adjustments for chroma sub-sampling should address adjacent gray area.

    :param original_format:
        If the clip to repair has been up-sampled for editing (e.g. from
        YUV420P8 to YUV422P16), pass in the original clip's format here
        so that correct assumptions are made for damage repair decisions.
    :type original_format: PresetFormat, VideoFormat, VideoNode or int

    :param bool restore_blank_detail:
        In rare cases where the black bars contain salvageable image data, this
        can be used to merge some of that original data on top of the
        filled-and-continued repair of the bar. Otherwise, this introduces
        noise.

    :param str prefill_mode:
        How to fill the blank line prior to interpolation. This is
        passed directly to the fillborders plugin. This pre-fill is
        used to improve the quality of the least-squares regression that is
        applied afterwards.

        As of fillborders v2, possible values are ``"fillmargins"``,
        ``"mirror"``, and ``"repeat"``.

Utility
^^^^^^^
.. autofunction:: vsfieldkit.annotate_bobbed_fields(clip, original_clip, tff, prop='OriginalField') -> VideoNode

.. autofunction:: vsfieldkit.double(clip) -> VideoNode

.. function:: vsfieldkit.group_by_combed( \
        clip \
    ) -> Iterator[Tuple[Union[bool, None], VideoNode]]

    Assuming the passed-in clip was processed by a filter that performs
    comb detection, this splits the clip into segments based on whether they
    are combed or not. The values it generates are True, False, or ``None`` if
    it was marked combed, not combed, or not marked as well as the segment of
    the clip. This does not have any built-in comb detection.

    This function requests rendered frames and blocks until it gets them. If
    not needing to remove frames, splice additional frames, or analyze frames,
    consider using :py:func:`std.FrameEval` or :py:func:`std.ModifyFrame`
    instead for simple comb-based frame replacements.

    .. code-block:: python
        :caption: Example

        progressive_clips = []
        detelecined = tivtc.TFM(clip, PP=1)
        for combed, segment in vsfieldkit.group_by_combed(detelecined):
            if combed:
                progressive_clips.append(
                    havsfunc.QTGMC(segment, TFF=False)
                )
            else:
                progressive_clips.append(
                    tivtc.TDecimate(segment, tff=False)
                )
        vs.core.std.Splice(progressive_clips).set_output()

.. function:: vsfieldkit.group_by_field_order( \
        clip \
    ) -> Iterator[Tuple[Union[FieldBased, None], VideoNode]]

    Generates field orders and clips from the passed in clip split up by
    changes in field order. Field order is expressed as a
    :py:class:`FieldBased` enumeration or ``None`` if field order is not
    applicable or not available.

    This function requests rendered frames and blocks until it gets them. If
    not needing to remove frames, splice additional frames, or analyze frames,
    consider using :py:func:`std.FrameEval` or :py:func:`std.ModifyFrame`
    instead for simple field-order-based frame replacements.

    .. code-block:: python
        :caption: Example

        progressive_clips = []
        for order, segment in vsfieldkit.group_by_field_order(clip):
            if order == vs.FIELD_TOP:
                progressive_clips.append(
                    havsfunc.QTGMC(segment, TFF=True)
                )
            elif order == vs.FIELD_BOTTOM:
                progressive_clips.append(
                    havsfunc.QTGMC(segment, TFF=False)
                )
            elif order == vs.PROGRESSIVE:
                progressive_clips.append(
                    vsfieldkit.double(segment)
                )
        vs.core.std.Splice(progressive_clips).set_output()

Types
^^^^^

.. autoclass:: vsfieldkit.ChromaSubsampleScanning
    :members:
    :undoc-members:

.. autoclass:: vsfieldkit.InterlacedScanPostProcessor
    :members:
    :undoc-members:

.. autoclass:: vsfieldkit.PulldownPattern
    :members:
    :undoc-members:

.. autoclass:: vsfieldkit.Factor

.. autoclass:: vsfieldkit.Resizer

Resampling Kernels
------------------
These are mostly for use as arguments to vsfieldkit's functions, but they all
can be used directly by calling them as you would any of the kernels found in
vapoursynth's built-in resize module.

.. autofunction:: vsfieldkit.kernels.resample_chroma_with_bicubic
.. autofunction:: vsfieldkit.kernels.resample_chroma_with_bilinear
.. autofunction:: vsfieldkit.kernels.resample_chroma_with_lanczos
.. autofunction:: vsfieldkit.kernels.resample_chroma_with_spline16
.. autofunction:: vsfieldkit.kernels.resample_chroma_with_spline36
.. autofunction:: vsfieldkit.kernels.resample_chroma_with_spline64
.. autofunction:: vsfieldkit.kernels.prepare_nnedi3_chroma_upsampler
