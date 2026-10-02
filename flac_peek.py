#!/usr/bin/env python3
"""Summarize FLAC stream metadata without decoding audio frames."""

import argparse
from pathlib import Path
import stat
import sys


SIGNATURE = b"fLaC"
STREAMINFO_SIZE = 34
MAX_METADATA_SIZE = 128 * 1024 * 1024
MAX_BLOCKS = 1_000_000


class FlacError(ValueError):
    pass


def read_exact(stream, size, label):
    data = stream.read(size)
    if len(data) != size:
        raise FlacError(f"truncated {label}")
    return data


def inspect(path):
    source = Path(path)
    file_stat = source.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise FlacError("input must be a regular file")

    with source.open("rb") as stream:
        if read_exact(stream, 4, "signature") != SIGNATURE:
            raise FlacError("invalid FLAC signature")

        streaminfo = None
        block_count = comments = pictures = 0
        metadata_size = 0
        last = False
        while not last:
            header = read_exact(stream, 4, "metadata block header")
            last = bool(header[0] & 0x80)
            block_type = header[0] & 0x7F
            length = int.from_bytes(header[1:], "big")
            block_count += 1
            metadata_size += 4 + length
            if block_count > MAX_BLOCKS or metadata_size > MAX_METADATA_SIZE:
                raise FlacError("metadata block limit exceeded")
            if stream.tell() + length > file_stat.st_size:
                raise FlacError("metadata block extends past end of file")
            if block_type == 127:
                raise FlacError("forbidden metadata block type")
            if block_count == 1 and (block_type != 0 or length != STREAMINFO_SIZE):
                raise FlacError("STREAMINFO must be the first 34-byte metadata block")
            if block_type == 0:
                if streaminfo is not None or length != STREAMINFO_SIZE:
                    raise FlacError("invalid duplicate STREAMINFO block")
                streaminfo = read_exact(stream, length, "STREAMINFO block")
                continue
            if block_type == 4:
                comments += 1
                if comments > 1:
                    raise FlacError("multiple Vorbis comment blocks")
            elif block_type == 6:
                pictures += 1
            stream.seek(length, 1)

        metadata_end = stream.tell()

    if streaminfo is None:
        raise FlacError("STREAMINFO is missing")
    minimum_block = int.from_bytes(streaminfo[0:2], "big")
    maximum_block = int.from_bytes(streaminfo[2:4], "big")
    if not 16 <= minimum_block <= maximum_block <= 65535:
        raise FlacError("invalid STREAMINFO block-size range")

    packed = int.from_bytes(streaminfo[10:18], "big")
    sample_rate = packed >> 44
    channels = ((packed >> 41) & 0x7) + 1
    bits_per_sample = ((packed >> 36) & 0x1F) + 1
    total_samples = packed & ((1 << 36) - 1)
    if not 4 <= bits_per_sample <= 32:
        raise FlacError("invalid STREAMINFO bit depth")
    duration = total_samples / sample_rate if total_samples and sample_rate else None
    return sample_rate, channels, bits_per_sample, total_samples, duration, block_count, comments, pictures, file_stat.st_size - metadata_end


def main():
    parser = argparse.ArgumentParser(description="Summarize FLAC metadata without decoding audio frames.")
    parser.add_argument("input", help="FLAC file")
    args = parser.parse_args()
    try:
        (sample_rate, channels, bits_per_sample, total_samples, duration,
         block_count, comments, pictures, payload_size) = inspect(args.input)
    except (OSError, FlacError) as error:
        print(f"flac-peek: {error}", file=sys.stderr)
        return 1

    print(f"Sample rate: {sample_rate:,} Hz" if sample_rate else "Sample rate: unknown")
    print(f"Channels: {channels}")
    print(f"Bits per sample: {bits_per_sample}")
    print(f"Total samples: {total_samples:,}" if total_samples else "Total samples: unknown")
    print(f"Duration: {duration:.3f} s" if duration is not None else "Duration: unknown")
    print(f"Metadata blocks: {block_count}")
    print(f"Vorbis comments: {'present' if comments else 'absent'}")
    print(f"Pictures: {'present' if pictures else 'absent'}")
    print(f"Bytes after metadata: {payload_size:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
