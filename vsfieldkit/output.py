import sys
from typing import IO, Callable, Mapping, Optional

from vapoursynth import (ChromaLocation, ColorFamily, ColorRange, FieldBased,
                         SampleType, VideoFormat, VideoNode)

Y4M_FLOAT_DEPTH_CODES = {
    16: 'h',
    32: 's',
    64: 'd'
}

Y4M_YCBCR_SUBSAMPLING_CODES = {
    (1, 1): '420',
    (1, 0): '422',
    (0, 0): '444',
    (2, 2): '410',
    (2, 0): '411',
    (0, 1): '440'
}

Y4M_CHROMA_SITING_CODES = {
    ChromaLocation.CHROMA_CENTER: 'jpeg',
    ChromaLocation.CHROMA_LEFT: 'mpeg2',
    ChromaLocation.CHROMA_TOP_LEFT: 'paldv',
}

Y4M_RANGE_CODES = {
    ColorRange.RANGE_LIMITED: 'LIMITED',
    ColorRange.RANGE_FULL: 'FULL',
}


def output_frame_inferred_y4m(
    clip: VideoNode,
    fileobj: IO,
    progress_update: Optional[Callable] = None,
    prefetch: int = 0,
    backlog: int = -1
) -> None:
    """Similar to VideNode.output, writes raw video data to the given file
    object, decorated with yuv4mpeg2 headers based on the clip and the first
    frame's properties."""
    if (
        (fileobj is sys.stdout or fileobj is sys.stderr)
        and hasattr(fileobj, 'buffer')
    ):
        write = fileobj.buffer.write
    else:
        write = fileobj.write
    y4m_header = yuv4mpeg2_header(clip)
    write(y4m_header)
    write(b'\n')
    if progress_update:
        def y4m_progress_update(done: int, total: int) -> None:
            progress_update(done, total)
            if done != total:
                write(b'FRAME\n')
    else:
        def y4m_progress_update(done: int, total: int) -> None:
            if done != total:
                write(b'FRAME\n')
    return clip.output(
        fileobj,
        progress_update=y4m_progress_update,
        prefetch=prefetch,
        backlog=backlog
    )


def yuv4mpeg2_header(clip: VideoNode, infer_from_first_frame=True) -> bytes:
    """Produces a YUV4MPEG2 header for the video clip. Unlike vspipe's
    out-of-the-box Y4M header, this one infers full details from the first
    frame of the clip, not just the clip's dimensions.
    """
    # Defaults that can be overridden by frame metadata:
    interlacing = '?'
    sar = '0:0'
    color_range_code = None
    if infer_from_first_frame:
        first_frame_props = clip.get_frame(0).props
        interlacing = {
            FieldBased.FIELD_PROGRESSIVE: 'p',
            FieldBased.FIELD_TOP: 't',
            FieldBased.FIELD_BOTTOM: 'b'
        }.get(first_frame_props.get('_FieldBased'), '?')
        if '_SARNum' in first_frame_props:
            sar = (
                f'{first_frame_props["_SARNum"]}'
                f':{first_frame_props.get("_SARDen", 1)}'
            )
        if '_ColorRange' in first_frame_props:
            color_range_code = Y4M_RANGE_CODES[first_frame_props["_ColorRange"]]
        chroma_format = _yuv4mpeg2_chroma_string(clip, first_frame_props)
    else:
        chroma_format = _yuv4mpeg2_chroma_string(clip)

    y4m_header = (
        f'YUV4MPEG2 '
        f'C{chroma_format} '
        f'W{clip.width} '
        f'H{clip.height} '
        f'F{clip.fps_num}:{clip.fps_den} '
        f'I{interlacing} '
        f'A{sar} '
        f'XLENGTH={len(clip)}'
    )

    if color_range_code:
        y4m_header += f' XCOLORRANGE={color_range_code}'

    return y4m_header.encode('ascii')


def _yuv4mpeg2_chroma_string(
    clip: VideoNode,
    props: Optional[Mapping] = None
) -> str:
    fmt: VideoFormat = clip.format
    if fmt.color_family == ColorFamily.GRAY:
        return f'mono{fmt.bits_per_sample if fmt.bits_per_sample > 8 else ""}'
    elif fmt.color_family == ColorFamily.YUV:
        subsampling = Y4M_YCBCR_SUBSAMPLING_CODES.get(
            (fmt.subsampling_w, fmt.subsampling_h)
        )
        if not subsampling:
            raise ValueError(f'No matching Y4M colorspace for {fmt}.')
        if fmt.sample_type == SampleType.INTEGER:
            if fmt.bits_per_sample > 8:
                return f'{subsampling}p{fmt.bits_per_sample}'
            else:
                if props and subsampling == '420':
                    colorspace = Y4M_CHROMA_SITING_CODES.get(
                        props.get('_ChromaLocation', None),
                        ''
                    )
                    return f'{subsampling}{colorspace}'
                else:
                    return subsampling
        elif fmt.sample_type == SampleType.FLOAT:
            return (
                f'{subsampling}p{Y4M_FLOAT_DEPTH_CODES[fmt.bits_per_sample]}'
            )
        else:
            raise ValueError('Unknown sample type.')
    else:
        raise ValueError(f'{fmt.color_family} color family incompatible'
                         f'with Y4M')
