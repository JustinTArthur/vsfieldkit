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

As the developer does not have Windows, vsrepo is not supported.

Dependencies
^^^^^^^^^^^^
Just VapourSynth.

Deinterlacing
-------------
.. function:: vsfieldkit.scan_interlaced( \
        clip: VideoNode, \
        warmup_clip: Optional[VideoNode] = None, \
        tff: Optional[bool] = None, \
        chroma_subsample_scanning: ChromaSubsampleScanning = ( \
            ChromaSubsampleScanning.SCAN_LATEST \
        ), \
        dither_type: str = 'random', \
        post_processing: Sequence[InterlacedScanPostProcessor] = (), \
        post_processing_blend_kernel: Callable = core.resize.Spline36, \
    ) -> VideoNode

    Returns a new clip where interlaced fields from the original clip are
    painted onto each frame in their correct position moment-by-moment like
    an interlaced scan display would. This is sometimes referred to as
    phosphor deinterlacing, display interlacing, or simply interlaced scan.
    Like bob deinterlacing, it doubles the amount of frames used produced to
    portray the moments represented in the interlaced footage.

    Interlaced content is typically stored or transmitted with two moments
    interlaced into one frame and each moment only appearing in that one frame.
    This balances the destructive compression of time and image resolution. The
    frames generated by ``scan_interlaced`` will repeat a field from the
    previous moment, losing that compression advantage. Additionally, they
    can't be treated as interlaced by downstream filters or playback systems
    that expect a field's picture to only appear once. Because of this, they
    are marked as progressive by the function. It might be better to call this
    function a "display interlacer" rather than a deinterlacer.

    In the function's current version, there are no simulations of physical
    CRT/phosphor effects like dimming/decay, aperture grille, or shadow mask.

    This was inspired by Juha Jeronen's wonderful Phosphor deinterlacer for
    VideoLAN's VLC. This code was not derived from it, but I've tried to at
    least keep the subsampling nomenclature the same.

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
        ``False`` for bottom-field first. Applies to the main clip and/or the
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

    :param str dither_type:
        If video is processed at a higher bit depth internally before being
        returned to an original depth of less than 16 bits per plane, this
        dithering method will be used to avoid banding or other unnatural
        artifacts caused by rounding.

    :param Sequence[InterlacedScanPostProcessor] post_processing:
        Post-processing steps to run on the frames resulting from interlaced
        scanning. At the moment, only
        :py:attr:`~vsfieldkit.InterlacedScanPostProcessor.BLEND_VERTICALLY` is
        available.

.. autoclass:: vsfieldkit.ChromaSubsampleScanning
    :members:
    :undoc-members:

.. autoclass:: vsfieldkit.InterlacedScanPostProcessor
    :members:
    :undoc-members:

Utility Functions
-----------------
.. autofunction:: vsfieldkit.assume_bff
.. autofunction:: vsfieldkit.assume_progressive
.. autofunction:: vsfieldkit.assume_tff
.. autofunction:: vsfieldkit.double
.. function:: vsfieldkit.group_by_combed( \
        clip: VideoNode \
    ) -> Iterator[Tuple[Union[bool, None], VideoNode]]

    Assuming the passed-in clip was processed by a filter that performs
    comb detection, this splits the clip into segments based on whether they
    are combed or not. The values it generates are True, False, or ``None`` if
    it was marked combed, not combed, or not marked as well as the segment of
    the clip.

    This does not have any built-in comb detection.

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
        clip: VideoNode \
    ) -> Iterator[Tuple[Union[FieldBased, None], VideoNode]]

    Generates field orders and clips from the passed in clip split up by
    changes in field order. Field order is expressed as a
    :py:class:`FieldBased` enumeration or ``None`` if field order is not
    applicable or not available.

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