# copyright: Jetsetter
# license: MIT

import PIL.Image


def get_grays(image, width, height):
    if isinstance(image, (tuple, list)):
        if len(image) != width * height:
            raise ValueError('image sequence length not equal to width*height)')

        return image

    if isinstance(image, PIL.Image.Image):
        gray_image = image.convert('L')
        small_image = gray_image.resize((width, height), PIL.Image.ANTIALIAS)
        return [*small_image.getdata()]

    else:
        raise ValueError("image must be PIL.Image.Image Instance")


def dhash_row_col(image, size=8):
    width = size + 1
    grays = get_grays(image, width, width)

    row_hash = 0
    col_hash = 0

    for y in range(size):
        for x in range(size):
            offset = y * width + x
            row_bit = grays[offset] < grays[offset + 1]
            row_hash = row_hash << 1 | row_bit

            col_bit = grays[offset] < grays[offset + width]
            col_hash = col_hash << 1 | col_bit

    return row_hash, col_hash


def dhash_int(image, size=8):
    row_hash, col_hash = dhash_row_col(image, size=size)
    return row_hash << (size * size) | col_hash


def diff(hash1, hash2):
    return bin(hash1 ^ hash2).count('1')


def format_bytes(row_hash, col_hash, size=8):
    bits_per_hash = size * size
    full_hash = row_hash << bits_per_hash | col_hash
    return full_hash.to_bytes(bits_per_hash // 4, 'big')


def format_hex(row_hash, col_hash, size=8):
    hex_length = size * size // 4
    return f'{row_hash:0{hex_length}x}{col_hash:0{hex_length}x}'


def format_matrix(hash_int, bits='01', size=8):
    output = f'{hash_int:0{size * size}b}'
    output = output.translate({ord('0'): bits[0], ord('1'): bits[1]})

    width = size * len(bits[0])
    lines = [output[i:i + width] for i in range(0, size * width, width)]
    return '\n'.join(lines)


def format_grays(grays, size=8):
    width = size + 1
    lines = []

    for y in range(width):
        line = []
        for x in range(width):
            gray = grays[y * width + x]
            line.append(format(gray, '4'))
        lines.append(''.join(line))

    return '\n'.join(lines)
