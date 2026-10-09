#!/usr/bin/env python3
"""Decrypt an official MTA:SA luac.mtasa.com client script (marker 0x1C).

Reimplements the public-key RSA transform and LuaQ bytecode normalizer
documented by the netc.dll DeobfuscateScript path / ByteRevenant Gafnium.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


def bytes_to_long(data: bytes) -> int:
    return int.from_bytes(data, "big")


def long_to_bytes(value: int, length: int) -> bytes:
    if value < 0:
        raise ValueError("negative RSA integer")
    try:
        return int(value).to_bytes(length, "big")
    except OverflowError as exc:
        raise ValueError(f"RSA integer does not fit in {length} bytes") from exc

SIGNED_MAGIC = 0xF14A55B7
HEADER_SIZE = 93
SIGNATURE_SIZE = 64
SIGNED_SIZE = HEADER_SIZE + SIGNATURE_SIZE
RSA_BLOCK = 64
RSA_PAYLOAD = 63

OBFUSCATION_KEY_HEX = (
    "0100010005B20A3E491EDB02B85E1073E4B3BA6EEA2AF02A361F32A6FA56A89F"
    "E7B773B11732F9394E8BF6A6D71F34A68B55AF4266A41AEC82363E8E3F37499"
    "818DBE0C9"
)

LUAQ_CRYPT = [
    0x8E, 0x79, 0x64, 0xBB, 0x77, 0xEA, 0x60, 0xD2, 0xCA, 0x3C, 0x1A, 0x1A, 0xC4, 0xC1, 0x98, 0x1E,
    0x1E, 0x61, 0x99, 0xFD, 0xEB, 0x26, 0xAD, 0xC2, 0x3E, 0x87, 0xDC, 0x4B, 0x63, 0x0A, 0x9B, 0xDA,
    0xBC, 0x9D, 0xA8, 0x90, 0x27, 0xD2, 0xBA, 0xAB, 0xE0, 0x49, 0xC0, 0xE7, 0xE3, 0x1D, 0xB9, 0x4C,
    0x70, 0x64, 0x4B, 0x6B, 0x69, 0x96, 0xD4, 0xFF, 0x61, 0xDD, 0x37, 0x85, 0x64, 0xD6, 0x10, 0x43,
    0xBA, 0x85, 0xE0, 0x24, 0x0B, 0xFB, 0x1F, 0xC8, 0x24, 0x14, 0x8F, 0x1B, 0x8F, 0x66, 0xF3, 0x20,
    0xDF, 0xBA, 0xEF, 0x36, 0x10, 0x71, 0xE0, 0xFB, 0x0D, 0x1D, 0x99, 0x80, 0x10, 0x51, 0x9B, 0x19,
    0xDB, 0xAB, 0x1D, 0x7E, 0x13, 0xC3, 0xC1, 0xCB, 0x4C, 0xBB, 0xFE, 0x2C, 0x69, 0x94, 0xE7, 0x56,
    0xD5, 0x88, 0x63, 0x16, 0xD5, 0xFB, 0xA1, 0xC4, 0x55, 0x91, 0x5D, 0x6D, 0x51, 0xD7, 0x19, 0x3C,
    0x95, 0x43, 0x66, 0x36, 0x7B, 0xAF, 0xD7, 0x99, 0x75, 0xE5, 0x32, 0xA7, 0x13, 0xA7, 0x5E, 0xF8,
    0x39, 0xAB, 0x57, 0x45, 0x87, 0xDC, 0x8B, 0xA1, 0x09, 0x21, 0x0D, 0xB3, 0xBB, 0xE1, 0x57, 0xEE,
    0xDD, 0x62, 0xC7, 0x23, 0xFC, 0x3F, 0x91, 0xBD, 0x7B, 0xA5, 0xAF, 0x3D, 0xEA, 0x7E, 0x75, 0x49,
    0xC1, 0xB2, 0x0D, 0x4D, 0x65, 0xA9, 0x21, 0x9A, 0xF1, 0x05, 0xA7, 0x63, 0x78, 0x6D, 0x83, 0xF9,
    0xC6, 0x5C, 0xF7, 0xF6, 0xCD, 0xCA, 0x76, 0x7A, 0x7A, 0x2D, 0xE7, 0x84, 0x67, 0xDD, 0x65, 0x99,
    0x26, 0x02, 0xCF, 0x95, 0xA1, 0xC0, 0x32, 0x88, 0xC5, 0x04, 0x92, 0x77, 0xB4, 0xB9, 0x7B, 0x4A,
    0x31, 0x42, 0x5D, 0x18, 0x0C, 0x2C, 0xFA, 0x46, 0x34, 0x76, 0xD9, 0xC2, 0xA7, 0xA4, 0xAC, 0x69,
    0xF0, 0xE1, 0x74, 0x79, 0x28, 0xB0, 0x64, 0xEA, 0x6D, 0x84, 0x86, 0xE6, 0x79, 0xEF, 0xB6, 0xB7,
]

OP_JMP, OP_FORLOOP, OP_FORPREP = 22, 31, 32
OP_MTA_NOP, OP_MTA_XOR, OP_MTA_FAIL = 0x26, 0x27, 0x28


def u32(buf: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def wu32(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into("<I", buf, off, value)


def getarg(raw: int, pos: int, size: int) -> int:
    return (raw >> pos) & ((1 << size) - 1)


def opcode(raw: int) -> int:
    return getarg(raw, 0, 6)


def arg_a(raw: int) -> int:
    return getarg(raw, 6, 8)


def arg_bx(raw: int) -> int:
    return getarg(raw, 14, 18)


def arg_sbx(raw: int) -> int:
    return arg_bx(raw) - 131071


def set_sbx(raw: int, value: int) -> int:
    packed = value + 131071
    mask = ((1 << 18) - 1) << 14
    return (raw & ~mask) | ((packed << 14) & mask)


def decrypt_header(trailer: bytearray) -> bytearray:
    decoded = bytearray(trailer)
    for index in range(73):
        bit = 1 << (index & 7)
        decoded[8 + index] ^= (((index % 12) * (index % 12)) ^ 0x5D ^ bit) & 0xFF
    return decoded


def rsa_transform_block(block: bytes, e: int, n: int) -> bytes:
    m = bytes_to_long(block[::-1])
    c = pow(m, e, n)
    return long_to_bytes(c, RSA_BLOCK)[::-1]


def rsa_decrypt_payload(raw: bytes) -> bytes:
    key = bytes.fromhex(OBFUSCATION_KEY_HEX)
    e = struct.unpack_from("<I", key, 0)[0]
    n = bytes_to_long(key[4:][::-1])
    original_length = u32(raw, len(raw) - 4)
    encrypted = raw[5:-4]
    if len(encrypted) % RSA_BLOCK != 0:
        raise ValueError("encrypted payload is not a multiple of the RSA block size")
    out = bytearray()
    for offset in range(0, len(encrypted), RSA_BLOCK):
        block = rsa_transform_block(encrypted[offset:offset + RSA_BLOCK], e, n)
        remaining = original_length - len(out)
        if remaining <= 0:
            break
        out.extend(block[: min(RSA_PAYLOAD, remaining)])
    if len(out) != original_length:
        raise ValueError(f"RSA output length {len(out)} != {original_length}")
    return bytes(out)


def decrypt_mta_luac(data: bytes) -> tuple[bytes, dict]:
    if not data or data[0] != 0x1C:
        raise ValueError("not an MTA obfuscated script (expected 0x1C marker)")
    if len(data) < SIGNED_SIZE:
        raise ValueError("file too small for signed MTA footer")

    footer_off = len(data) - SIGNED_SIZE
    raw = data[:footer_off]
    trailer = bytearray(data[footer_off:footer_off + HEADER_SIZE])
    if u32(trailer, 81) != SIGNED_MAGIC:
        raise ValueError("missing MTA signed-script magic")
    if u32(trailer, 85) != footer_off:
        raise ValueError("header offset mismatch")

    checksum = sum(data[: len(data) - SIGNATURE_SIZE - 5]) & 0xFFFFFFFF
    info = {
        "checksum_ok": checksum == u32(trailer, 89),
        "decoded_header": bytes(decrypt_header(trailer)),
    }
    chunk = rsa_decrypt_payload(raw)
    if chunk[:4] != b"\x1bLua":
        raise ValueError("RSA decrypt did not yield a Lua 5.1 chunk")
    return chunk, info


class LuaQNormalizer:
    def __init__(self, data: bytearray):
        self.data = data
        self.pos = 0
        self.stats = {"strings": 0, "code_blocks": 0, "nops": 0, "jumps": 0}

    def u8(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b

    def u32(self) -> int:
        v = u32(self.data, self.pos)
        self.pos += 4
        return v

    def skip(self, n: int) -> None:
        self.pos += n

    def erase(self, off: int, count: int) -> None:
        del self.data[off:off + count]
        if off < self.pos:
            self.pos -= min(count, self.pos - off)

    def parse_string(self) -> None:
        size_off = self.pos
        raw_size = self.u32()
        if raw_size == 0:
            return
        key = (raw_size >> 24) & 0xFF
        size = raw_size & 0x00FFFFFF
        if key:
            wu32(self.data, size_off, size)
            for i in range(size):
                self.data[self.pos + i] ^= LUAQ_CRYPT[key]
                key = (key + 1) & 0xFF
            self.stats["strings"] += 1
        self.pos += size

    def parse_code(self) -> int:
        size_off = self.pos
        size = self.u32()
        code_off = self.pos
        if size:
            first = u32(self.data, code_off)
            if opcode(first) == OP_MTA_XOR:
                crypt_size = arg_bx(first) * 4
                key = arg_a(first)
                back = crypt_size - 1
                for index in range(crypt_size - 4):
                    self.data[code_off + back] ^= (index ^ key ^ (5 * index)) & 0xFF
                    back -= 1
                if u32(self.data, code_off + crypt_size - 4) != 0x0080001E:
                    raise ValueError("XOR code block did not end in RETURN")
                size -= 1
                wu32(self.data, size_off, size)
                self.erase(code_off, 4)
                self.stats["code_blocks"] += 1
        index = 0
        while index < size:
            inst_off = code_off + 4 * index
            inst = u32(self.data, inst_off)
            op = opcode(inst)
            if op in (OP_MTA_NOP, OP_MTA_FAIL):
                size -= 1
                wu32(self.data, size_off, size)
                self.erase(inst_off, 4)
                self.stats["nops"] += 1
                continue
            if op in (OP_JMP, OP_FORLOOP, OP_FORPREP):
                target = arg_sbx(inst)
                if target > 60000:
                    wu32(self.data, inst_off, set_sbx(inst, 120000 - target))
                    self.stats["jumps"] += 1
            index += 1
        self.pos = code_off + size * 4
        return size

    def parse_constants(self) -> None:
        for _ in range(self.u32()):
            t = self.u8()
            if t == 1:
                self.skip(1)
            elif t == 3:
                self.skip(8)
            elif t == 4:
                self.parse_string()
            elif t != 0:
                raise ValueError(f"unknown constant type {t}")
        for _ in range(self.u32()):
            self.parse_function()

    def parse_debug(self, code_len: int) -> None:
        line_off = self.pos
        nline = self.u32()
        if nline == code_len + 1:
            wu32(self.data, line_off, code_len)
            self.erase(self.pos, 4)
            nline -= 1
        self.skip(nline * 4)
        for _ in range(self.u32()):
            self.parse_string()
            self.skip(8)
        for _ in range(self.u32()):
            self.parse_string()

    def parse_function(self) -> None:
        self.parse_string()
        self.skip(8 + 4)
        code_len = self.parse_code()
        self.parse_constants()
        self.parse_debug(code_len)

    def run(self) -> dict:
        self.skip(12)
        self.parse_function()
        return self.stats


def normalize_luaq(chunk: bytes) -> tuple[bytes, dict]:
    buf = bytearray(chunk)
    stats = LuaQNormalizer(buf).run()
    return bytes(buf), stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--no-normalize", action="store_true")
    args = parser.parse_args()
    data = Path(args.input).read_bytes()
    chunk, info = decrypt_mta_luac(data)
    if not args.no_normalize:
        chunk, stats = normalize_luaq(chunk)
        print("LuaQ", stats, file=sys.stderr)
    Path(args.output).write_bytes(chunk)
    print(f"wrote {args.output} ({len(chunk)} bytes), checksum_ok={info['checksum_ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
