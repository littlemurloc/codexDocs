"""Inspect the observed Y3 cache format and prepare opaque generated textures.

Python + Pillow; does not import resources into Y3 or generate artwork.
"""
import argparse
import hashlib
import io
import json
import re
import struct
import sys
import uuid
from pathlib import Path


def emit(value):
    print(json.dumps(value, ensure_ascii=True, indent=2))


def unpack_resource(data):
    if data.startswith(b'CCCCZZZ4'):
        base = 8
    elif data.startswith(b'ZZZ4'):
        base = 4
    elif data.startswith(b'NNNN'):
        return data[4:], []
    else:
        return data, []
    if len(data) < base + 4:
        raise ValueError('Truncated compression header')
    expected = struct.unpack_from('<I', data, base)[0]
    if not 0 < expected <= 128 * 1024 * 1024:
        raise ValueError('Unsupported advertised decoded size')
    src = data[base + 4:]
    dst = bytearray()
    pos = 0

    def extension(length):
        nonlocal pos
        while True:
            if pos >= len(src):
                raise ValueError('Truncated LZ4 length')
            n = src[pos]
            pos += 1
            length += n
            if n != 255:
                return length

    while pos < len(src) and len(dst) < expected:
        token = src[pos]
        pos += 1
        length = token >> 4
        if length == 15:
            length = extension(length)
        if pos + length > len(src):
            raise ValueError('Truncated LZ4 literals')
        dst.extend(src[pos:pos + length])
        pos += length
        if pos >= len(src) or len(dst) >= expected:
            break
        if pos + 2 > len(src):
            raise ValueError('Truncated LZ4 offset')
        offset = struct.unpack_from('<H', src, pos)[0]
        pos += 2
        if not 0 < offset <= len(dst):
            raise ValueError('Invalid LZ4 offset')
        length = token & 15
        if length == 15:
            length = extension(length)
        length += 4
        if len(dst) + length > expected:
            raise ValueError('LZ4 output exceeds advertised size')
        chunk = bytes(dst[-offset:])
        dst.extend((chunk * ((length + offset - 1) // offset))[:length])
    if len(dst) != expected:
        raise ValueError(f'Decoded length mismatch: {len(dst)} != {expected}')
    return bytes(dst), []


def ensure_new(paths):
    for p in paths:
        if p.exists():
            raise FileExistsError(f'Refusing overwrite: {p}')
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def alpha_range(im):
    return list(im.convert('RGBA').getchannel('A').getextrema())


def repository(args):
    data, warnings = unpack_resource(args.source.read_bytes())
    entries = []
    seen = set()
    for match in re.finditer(re.escape(args.query.encode('ascii')), data, re.I):
        for pos in range(max(18, match.start() - 128), match.start() + 1):
            length = struct.unpack_from('<H', data, pos - 2)[0]
            end = pos + length
            if not 0 < length <= 128 or end < match.end() or end + 4 > len(data):
                continue
            name = data[pos:end]
            if not re.fullmatch(rb'[A-Za-z0-9_ .-]+', name):
                continue
            resource_type = struct.unpack_from('<H', data, end + 2)[0]
            if resource_type > 32:
                continue
            guid = str(uuid.UUID(bytes=data[pos - 18:pos - 2]))
            if (guid, name) in seen:
                continue
            seen.add((guid, name))
            candidates = sorted(str(p) for p in (args.source.parent / guid[:2]).glob(guid + '*'))
            entries.append({'name': name.decode('ascii'), 'guid': guid, 'files': candidates})
    if args.output:
        ensure_new([args.output])
        args.output.write_bytes(data)
    emit({'entries': entries, 'warnings': warnings, 'decoded_size': len(data), 'lookup_mode': 'heuristic; verify candidates through material references'})


def material(args):
    data, warnings = unpack_resource(args.source.read_bytes())
    if not data.startswith(b'.MESSIAH'):
        raise ValueError('Unsupported material header; inspect separately')
    refs = [{'parameter': m.group(1).decode(), 'guid': m.group(2).decode(), 'byte_offset': m.start()}
            for m in re.finditer(rb'(t[A-Za-z0-9]+Map)=([0-9a-fA-F-]{36})', data)]
    if args.output:
        ensure_new([args.output])
        args.output.write_bytes(data)
    emit({'references_in_file_order': refs, 'warnings': warnings})


def extract(args):
    from PIL import Image
    raw = args.source.read_bytes()
    if len(raw) < 60 or raw[:5] != b'\x02\x02\x02\x01\x01':
        raise ValueError('Unsupported Y3 texture container header')
    # Only the two formats observed in this cache family are accepted.
    formats = {0x12: (b'DXT1', 8), 0x14: (b'DXT5', 16)}
    if raw[5] not in formats:
        raise ValueError(f'Unsupported texture format tag: {raw[5]:#x}')
    fourcc, block_size = formats[raw[5]]
    pos = 40
    mips = []
    while pos < len(raw):
        if pos + 20 > len(raw):
            raise ValueError('Truncated mip header')
        n, w, h, depth, row, length = struct.unpack_from('<IHHHHI', raw, pos)
        if n < 20 or pos + n > len(raw) or not 0 < w <= 16384 or not 0 < h <= 16384 or depth != 0:
            raise ValueError('Unsupported or invalid mip layout')
        payload = raw[pos + 16:pos + n]
        if payload[:4] not in (b'NNNN', b'ZZZ4'):
            raise ValueError('Unsupported mip compression marker')
        data, warnings = unpack_resource(payload)
        expected = ((w + 3) // 4) * ((h + 3) // 4) * block_size
        if warnings or len(data) != length or length != expected:
            raise ValueError('Mip block data length mismatch')
        mips.append((w, h, data))
        pos += n
    if not mips:
        raise ValueError('No mip levels')
    w, h, data = max(mips, key=lambda v: v[0] * v[1])
    header = bytearray(124)
    struct.pack_into('<7I', header, 0, 124, 0x81007, h, w, len(data), 0, 1)
    struct.pack_into('<2I', header, 72, 32, 4)
    header[80:84] = fourcc
    struct.pack_into('<I', header, 104, 0x1000)
    dds = b'DDS ' + header + data
    im = Image.open(io.BytesIO(dds))
    im.load()
    paths = [Path(str(args.output) + suffix) for suffix in ('.dds', '.png', '.json')]
    record = {'source': str(args.source.resolve()), 'source_sha256': hashlib.sha256(raw).hexdigest(),
              'size': [w, h], 'mode': im.mode, 'alpha_extrema': alpha_range(im),
              'block_format': fourcc.decode(), 'mip_sizes': [[x[0], x[1]] for x in mips]}
    ensure_new(paths)
    paths[0].write_bytes(dds)
    im.save(paths[1])
    write_json(paths[2], record)
    emit(record)


def prepare(args):
    from PIL import Image
    with Image.open(args.reference) as ref, Image.open(args.source) as source:
        target = ref.size
        if alpha_range(ref) != [255, 255]:
            raise ValueError('Reference has meaningful Alpha; use a workflow that preserves its exact mask')
        if alpha_range(source) != [255, 255]:
            raise ValueError('Generated image has transparency; repair generation rather than flatten it')
        if source.width * target[1] != source.height * target[0]:
            raise ValueError('Aspect ratio mismatch; regenerate, do not crop or distort the atlas')
        master_size = source.size
        final = source.convert('RGB')
        if final.size != target:
            final = final.resize(target, Image.Resampling.LANCZOS)
    if args.output.suffix.lower() != '.png':
        raise ValueError('Prepared output must be PNG')
    metadata = args.output.with_suffix('.metadata.json')
    ensure_new([args.output, metadata])
    final.save(args.output)
    with Image.open(args.output) as verify:
        if verify.size != target or verify.mode != 'RGB':
            raise ValueError('Written output verification failed')
    record = {'file': str(args.output.resolve()), 'reference': str(args.reference.resolve()),
              'size': list(target), 'mode': 'RGB', 'generator_master_size': list(master_size),
              'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}
    write_json(metadata, record)
    emit(record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name, help_text in [('repository', 'Find name/GUID candidates in a cache repository'),
                            ('material', 'List material texture references in serialized order'),
                            ('extract', 'Decode supported BC1/BC3 cache texture to DDS and PNG'),
                            ('prepare', 'Match an opaque generator master to original texture dimensions')]:
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument('--source', type=Path, required=True)
        sub.add_argument('--output', type=Path, required=name in ('extract', 'prepare'))
        if name == 'repository':
            sub.add_argument('--query', required=True, help='ASCII internal model ID or resource name')
        if name == 'prepare':
            sub.add_argument('--reference', type=Path, required=True)
        sub.set_defaults(run=globals()[name])
    args = parser.parse_args()
    try:
        args.run(args)
    except (ValueError, OSError, struct.error) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
