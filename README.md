# flac-peek

Read a FLAC file's STREAMINFO and count metadata blocks without decoding audio frames or printing tag contents. Useful for a quick technical summary when you do not want to reveal embedded titles, comments, or artwork.

## Use

Requires Python 3.8+; no packages to install.

```sh
python flac_peek.py recording.flac
```

The report includes sample rate, channels, bit depth, sample count, estimated duration when known, metadata block count, and whether Vorbis comments or pictures are present. `Bytes after metadata` is a byte count only; the tool does not validate audio frames or decode samples. It limits the metadata section to 128 MiB and one million blocks.

The STREAMINFO fields and metadata-block layout follow [RFC 9639](https://www.rfc-editor.org/rfc/rfc9639.html). The file must be seekable and a regular file.

## License

MIT
