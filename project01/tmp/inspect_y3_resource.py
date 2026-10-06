from pathlib import Path
import struct, re, json

ROOT = Path(r'D:\Program Files\y3\games\2.0\game\LocalData\Patch')
OUT = Path(r'D:\codex\project01\tmp\lvbu-resource-analysis')
OUT.mkdir(parents=True, exist_ok=True)

def decode(data):
    if data.startswith(b'CCCCZZZ4'):
        base = 8
    elif data.startswith(b'ZZZ4'):
        base = 4
    else:
        return data
    size = struct.unpack_from('<I', data, base)[0]
    src = data[base+4:]
    dst = bytearray()
    i = 0
    while i < len(src) and len(dst) < size:
        token = src[i]; i += 1
        literal = token >> 4
        if literal == 15:
            while True:
                n = src[i]; i += 1; literal += n
                if n != 255: break
        dst.extend(src[i:i+literal]); i += literal
        if i >= len(src): break
        offset = src[i] | src[i+1] << 8; i += 2
        length = token & 15
        if length == 15:
            while True:
                n = src[i]; i += 1; length += n
                if n != 255: break
        length += 4
        if offset <= 0 or offset > len(dst):
            raise ValueError((i, offset, len(dst)))
        start = len(dst)-offset
        if offset >= length:
            dst.extend(dst[start:start+length])
        else:
            chunk = bytes(dst[start:])
            dst.extend((chunk*((length+offset-1)//offset))[:length])
    print('decode sizes',size,len(dst),'remaining',len(src)-i)
    return bytes(dst[:size])

if __name__ == '__main__':
    b = decode((ROOT/'resource.repository').read_bytes())
    (OUT/'resource.repository.decoded').write_bytes(b)
    print('decoded',len(b),repr(b[:160]))
    for m in re.finditer(b'504061',b):
        print('match',m.start(),repr(b[max(0,m.start()-36):m.start()+90]))
