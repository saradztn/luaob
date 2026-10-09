#!/usr/bin/env python3
"""Pure-Python Lua 5.1 decompiler (standard little-endian luac, no Java)."""
from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

OP_MOVE, OP_LOADK, OP_LOADBOOL, OP_LOADNIL = 0, 1, 2, 3
OP_GETUPVAL, OP_GETGLOBAL, OP_GETTABLE = 4, 5, 6
OP_SETGLOBAL, OP_SETUPVAL, OP_SETTABLE = 7, 8, 9
OP_NEWTABLE, OP_SELF = 10, 11
OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD, OP_POW = 12, 13, 14, 15, 16, 17
OP_UNM, OP_NOT, OP_LEN, OP_CONCAT = 18, 19, 20, 21
OP_JMP, OP_EQ, OP_LT, OP_LE = 22, 23, 24, 25
OP_TEST, OP_TESTSET = 26, 27
OP_CALL, OP_TAILCALL, OP_RETURN = 28, 29, 30
OP_FORLOOP, OP_FORPREP, OP_TFORLOOP = 31, 32, 33
OP_SETLIST, OP_CLOSE, OP_CLOSURE, OP_VARARG = 34, 35, 36, 37

BINOPS = {
    OP_ADD: "+",
    OP_SUB: "-",
    OP_MUL: "*",
    OP_DIV: "/",
    OP_MOD: "%",
    OP_POW: "^",
}
UNOPS = {OP_UNM: "-", OP_NOT: "not ", OP_LEN: "#"}
CMPOPS = {OP_EQ: ("==", "~="), OP_LT: ("<", ">="), OP_LE: ("<=", ">")}


def decode(inst: int) -> tuple[int, int, int, int, int, int]:
    op = inst & 0x3F
    a = (inst >> 6) & 0xFF
    c = (inst >> 14) & 0x1FF
    b = (inst >> 23) & 0x1FF
    bx = inst >> 14
    sbx = bx - 131071
    return op, a, b, c, bx, sbx


def is_ident(name: str) -> bool:
    if not name or name in {
        "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
        "if", "in", "local", "nil", "not", "or", "repeat", "return", "then",
        "true", "until", "while",
    }:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    return all(ch.isalnum() or ch == "_" for ch in name)


def lua_number(n: float) -> str:
    if n != n:
        return "(0/0)"
    if n == int(n) and abs(n) < 2**53:
        return str(int(n))
    text = repr(float(n))
    if text.endswith(".0"):
        text = text[:-2]
    return text


def lua_string(raw: bytes | str) -> str:
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return '"' + "".join(f"\\x{b:02x}" for b in raw) + '"'
    else:
        text = raw
    if "\n" in text or "\r" in text:
        eq = 0
        while True:
            open_b = "[" + "=" * eq + "["
            close_b = "]" + "=" * eq + "]"
            if open_b not in text and close_b not in text:
                return open_b + text + close_b
            eq += 1
    out = ['"']
    for ch in text:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 32 or o == 127:
            out.append(f"\\{o:03d}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def const_code(value: Any) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return lua_number(float(value))
    if isinstance(value, bytes):
        return lua_string(value)
    if isinstance(value, str):
        return lua_string(value)
    return lua_string(str(value))


def index_code(obj: str, key: Any, key_expr: str | None = None) -> str:
    if key_expr is None:
        if isinstance(key, bytes):
            try:
                key = key.decode("utf-8")
            except UnicodeDecodeError:
                key = None
        if isinstance(key, str) and is_ident(key):
            return f"{obj}.{key}"
        return f"{obj}[{const_code(key)}]"
    if key_expr.startswith('"') and key_expr.endswith('"'):
        inner = key_expr[1:-1]
        if is_ident(inner) and "\\" not in inner:
            return f"{obj}.{inner}"
    return f"{obj}[{key_expr}]"


@dataclass
class LocVar:
    name: str
    startpc: int
    endpc: int


@dataclass
class Proto:
    source: str = ""
    linedefined: int = 0
    lastlinedefined: int = 0
    nups: int = 0
    numparams: int = 0
    is_vararg: int = 0
    maxstack: int = 0
    code: list[int] = field(default_factory=list)
    k: list[Any] = field(default_factory=list)
    p: list["Proto"] = field(default_factory=list)
    lineinfo: list[int] = field(default_factory=list)
    locvars: list[LocVar] = field(default_factory=list)
    upvalues: list[str] = field(default_factory=list)


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.p = 0
        self.size_t = 4
        self.int_size = 4
        self.num_size = 8
        self.little = True

    def remaining(self) -> int:
        return len(self.data) - self.p

    def take(self, n: int) -> bytes:
        if self.p + n > len(self.data):
            raise ValueError("truncated Lua chunk")
        b = self.data[self.p : self.p + n]
        self.p += n
        return b

    def u8(self) -> int:
        return self.take(1)[0]

    def uint(self, size: int) -> int:
        raw = self.take(size)
        return int.from_bytes(raw, "little" if self.little else "big")

    def integer(self) -> int:
        return self.uint(self.int_size)

    def size(self) -> int:
        return self.uint(self.size_t)

    def number(self) -> float:
        raw = self.take(self.num_size)
        fmt = "<d" if self.little else ">d"
        if self.num_size == 8:
            return struct.unpack(fmt, raw)[0]
        raise ValueError(f"unsupported lua_Number size {self.num_size}")

    def lua_string(self) -> bytes | None:
        n = self.size()
        if n == 0:
            return None
        raw = self.take(n)
        if raw.endswith(b"\x00"):
            raw = raw[:-1]
        return raw


def undump(data: bytes) -> Proto:
    r = Reader(data)
    magic = r.take(4)
    if magic != b"\x1bLua":
        raise ValueError(f"not a Lua chunk: {magic!r}")
    version = r.u8()
    if version != 0x51:
        raise ValueError(f"only Lua 5.1 is supported (got 0x{version:02x})")
    r.u8()  # format
    r.little = r.u8() == 1
    r.int_size = r.u8()
    r.size_t = r.u8()
    insn_size = r.u8()
    r.num_size = r.u8()
    r.u8()  # integral flag
    if insn_size != 4:
        raise ValueError("instruction size must be 4")

    def load_function() -> Proto:
        proto = Proto()
        src = r.lua_string()
        proto.source = (src or b"").decode("utf-8", "replace")
        proto.linedefined = r.integer()
        proto.lastlinedefined = r.integer()
        proto.nups = r.u8()
        proto.numparams = r.u8()
        proto.is_vararg = r.u8()
        proto.maxstack = r.u8()
        ncode = r.integer()
        for _ in range(ncode):
            proto.code.append(r.uint(4))
        nk = r.integer()
        for _ in range(nk):
            t = r.u8()
            if t == 0:
                proto.k.append(None)
            elif t == 1:
                proto.k.append(bool(r.u8()))
            elif t == 3:
                proto.k.append(r.number())
            elif t == 4:
                proto.k.append(r.lua_string() or b"")
            else:
                raise ValueError(f"unknown constant type {t}")
        np = r.integer()
        for _ in range(np):
            proto.p.append(load_function())
        nline = r.integer()
        proto.lineinfo = [r.integer() for _ in range(nline)]
        nloc = r.integer()
        for _ in range(nloc):
            name = (r.lua_string() or b"v").decode("utf-8", "replace")
            start = r.integer()
            end = r.integer()
            proto.locvars.append(LocVar(name, start, end))
        nup = r.integer()
        for _ in range(nup):
            name = (r.lua_string() or b"up").decode("utf-8", "replace")
            proto.upvalues.append(name)
        return proto

    return load_function()


class Decompiler:
    def __init__(self, proto: Proto, indent: int = 0, upvalue_names: list[str] | None = None):
        self.proto = proto
        self.indent = indent
        self.upvalue_names = upvalue_names or [
            (proto.upvalues[i] if i < len(proto.upvalues) else f"u{i}")
            for i in range(proto.nups)
        ]
        self.lines: list[str] = []
        self.reg_name = [self._reg_name(i) for i in range(proto.maxstack)]
        self.skip: set[int] = set()
        self.targets = self._jump_targets()
        self.vararg_reg: int | None = None

    def _pad(self) -> str:
        return "    " * self.indent

    def _reg_name(self, i: int) -> str:
        for loc in self.proto.locvars:
            if loc.name.startswith("("):
                continue
            if loc.startpc <= 0 and i < self.proto.numparams:
                if is_ident(loc.name):
                    return loc.name
        if i < self.proto.numparams:
            return f"a{i}"
        return f"r{i}"

    def _jump_targets(self) -> set[int]:
        targets: set[int] = set()
        code = self.proto.code
        for pc, inst in enumerate(code):
            op, a, b, c, bx, sbx = decode(inst)
            if op in (OP_JMP, OP_FORLOOP, OP_FORPREP):
                targets.add(pc + 1 + sbx)
            elif op == OP_TFORLOOP:
                targets.add(pc + 2)
            elif op == OP_LOADBOOL and c:
                targets.add(pc + 2)
        return targets

    def emit(self, text: str) -> None:
        if text == "":
            self.lines.append("")
            return
        for line in text.split("\n"):
            self.lines.append(self._pad() + line if line else "")

    def k(self, idx: int) -> Any:
        return self.proto.k[idx]

    def rk_value(self, x: int) -> Any:
        if x & 256:
            return self.k(x & 255)
        return None

    def rk(self, x: int, regs: list[str]) -> str:
        if x & 256:
            return const_code(self.k(x & 255))
        return regs[x]

    def _need_parens(self, expr: str) -> str:
        if expr.startswith("function") or " " in expr or any(op in expr for op in ("+", "-", "*", "/", "%", "^", "..", "==", "~=", "<=", ">=", "<", ">", " and ", " or ")):
            if not (expr.startswith("(") and expr.endswith(")")):
                if expr.startswith("not ") or expr.startswith("#") or expr.startswith("-"):
                    return expr
                return f"({expr})"
        return expr

    def decompile(self) -> str:
        proto = self.proto
        params = [self.reg_name[i] for i in range(proto.numparams)]
        if proto.is_vararg:
            params.append("...")
        header = f"function({', '.join(params)})"
        self.emit(header)
        self.indent += 1
        self._emit_block(0, len(proto.code), [self.reg_name[i] for i in range(proto.maxstack)])
        self.indent -= 1
        self.emit("end")
        return "\n".join(self.lines) + "\n"

    def _emit_block(self, start: int, end: int, regs: list[str]) -> None:
        pc = start
        code = self.proto.code
        while pc < end:
            if pc in self.skip:
                pc += 1
                continue
            inst = code[pc]
            op, a, b, c, bx, sbx = decode(inst)

            if op == OP_CLOSURE:
                pc = self._do_closure(pc, regs)
                continue
            if op == OP_FORPREP:
                pc = self._do_numeric_for(pc, end, regs)
                continue
            if op == OP_JMP and pc + 1 < end and decode(code[pc + 1])[0] == OP_TFORLOOP:
                pc = self._do_generic_for(pc, end, regs)
                continue
            if op in (OP_EQ, OP_LT, OP_LE, OP_TEST, OP_TESTSET) and pc + 1 < end and decode(code[pc + 1])[0] == OP_JMP:
                pc = self._do_test(pc, end, regs)
                continue
            if op == OP_JMP:
                target = pc + 1 + sbx
                if target < pc:
                    self.emit(f"-- loop back to {target}")
                elif target > pc + 1 and target <= end:
                    self.emit("do")
                    self.indent += 1
                    self._emit_block(pc + 1, min(target, end), regs)
                    self.indent -= 1
                    self.emit("end")
                    pc = min(target, end)
                    continue
                pc += 1
                continue

            self._do_simple(pc, regs)
            pc += 1

    def _flush_call_or_assign(self, dest: int, expr: str, regs: list[str], force_stmt: bool = False) -> None:
        regs[dest] = expr
        if force_stmt:
            self.emit(f"{self.reg_name[dest]} = {expr}")
            regs[dest] = self.reg_name[dest]

    def _do_simple(self, pc: int, regs: list[str]) -> None:
        inst = self.proto.code[pc]
        op, a, b, c, bx, sbx = decode(inst)

        if op == OP_MOVE:
            regs[a] = regs[b]
            self.emit(f"{self.reg_name[a]} = {regs[b]}")
            regs[a] = self.reg_name[a]
        elif op == OP_LOADK:
            regs[a] = const_code(self.k(bx))
            self.emit(f"{self.reg_name[a]} = {regs[a]}")
            regs[a] = self.reg_name[a]
        elif op == OP_LOADBOOL:
            regs[a] = "true" if b else "false"
            self.emit(f"{self.reg_name[a]} = {regs[a]}")
            regs[a] = self.reg_name[a]
            if c:
                self.skip.add(pc + 1)
        elif op == OP_LOADNIL:
            names = [self.reg_name[i] for i in range(a, b + 1)]
            self.emit(", ".join(names) + " = " + ", ".join(["nil"] * len(names)))
            for i in range(a, b + 1):
                regs[i] = "nil"
        elif op == OP_GETUPVAL:
            name = self.upvalue_names[b] if b < len(self.upvalue_names) else f"u{b}"
            self.emit(f"{self.reg_name[a]} = {name}")
            regs[a] = self.reg_name[a]
        elif op == OP_GETGLOBAL:
            g = self.k(bx)
            gname = g.decode("utf-8", "replace") if isinstance(g, bytes) else str(g)
            expr = gname if is_ident(gname) else f"_G[{const_code(g)}]"
            self.emit(f"{self.reg_name[a]} = {expr}")
            regs[a] = self.reg_name[a]
        elif op == OP_GETTABLE:
            key = self.rk(c, regs)
            kval = self.rk_value(c)
            if kval is not None:
                expr = index_code(regs[b], kval)
            else:
                expr = index_code(regs[b], None, key)
            self.emit(f"{self.reg_name[a]} = {expr}")
            regs[a] = self.reg_name[a]
        elif op == OP_SETGLOBAL:
            g = self.k(bx)
            gname = g.decode("utf-8", "replace") if isinstance(g, bytes) else str(g)
            lhs = gname if is_ident(gname) else f"_G[{const_code(g)}]"
            self.emit(f"{lhs} = {regs[a]}")
        elif op == OP_SETUPVAL:
            name = self.upvalue_names[b] if b < len(self.upvalue_names) else f"u{b}"
            self.emit(f"{name} = {regs[a]}")
        elif op == OP_SETTABLE:
            key = self.rk(b, regs)
            val = self.rk(c, regs)
            kval = self.rk_value(b)
            if kval is not None:
                lhs = index_code(regs[a], kval)
            else:
                lhs = index_code(regs[a], None, key)
            self.emit(f"{lhs} = {val}")
        elif op == OP_NEWTABLE:
            self.emit(f"{self.reg_name[a]} = {{}}")
            regs[a] = self.reg_name[a]
        elif op == OP_SELF:
            key = self.rk(c, regs)
            self.emit(f"{self.reg_name[a + 1]} = {regs[b]}")
            regs[a + 1] = self.reg_name[a + 1]
            kval = self.rk_value(c)
            if kval is not None:
                expr = index_code(regs[b], kval)
            else:
                expr = index_code(regs[b], None, key)
            self.emit(f"{self.reg_name[a]} = {expr}")
            regs[a] = self.reg_name[a]
        elif op in BINOPS:
            left = self.rk(b, regs)
            right = self.rk(c, regs)
            expr = f"{left} {BINOPS[op]} {right}"
            self.emit(f"{self.reg_name[a]} = {expr}")
            regs[a] = self.reg_name[a]
        elif op in UNOPS:
            expr = f"{UNOPS[op]}{self.rk(b, regs)}"
            self.emit(f"{self.reg_name[a]} = {expr}")
            regs[a] = self.reg_name[a]
        elif op == OP_CONCAT:
            parts = [regs[i] for i in range(b, c + 1)]
            expr = " .. ".join(parts)
            self.emit(f"{self.reg_name[a]} = {expr}")
            regs[a] = self.reg_name[a]
        elif op == OP_CALL or op == OP_TAILCALL:
            self._do_call(pc, regs, tail=(op == OP_TAILCALL))
            if op == OP_TAILCALL and pc + 1 < len(self.proto.code) and decode(self.proto.code[pc + 1])[0] == OP_RETURN:
                self.skip.add(pc + 1)
        elif op == OP_RETURN:
            if pc in self.skip:
                return
            if b == 1:
                if pc != len(self.proto.code) - 1:
                    self.emit("return")
            elif b == 0:
                vals = [regs[i] for i in range(a, self.proto.maxstack) if regs[i] and regs[i] != self.reg_name[i]]
                if not vals:
                    vals = [regs[a]]
                self.emit("return " + ", ".join(vals))
            else:
                vals = [regs[i] for i in range(a, a + b - 1)]
                self.emit("return " + ", ".join(vals))
        elif op == OP_SETLIST:
            n = b
            if n == 0:
                n = 1
            page = c
            start = (page - 1) * 50
            for i in range(n):
                self.emit(f"{regs[a]}[{start + i + 1}] = {regs[a + i + 1]}")
        elif op == OP_CLOSE:
            self.emit(f"-- close r{a}+")
        elif op == OP_VARARG:
            n = b - 1
            if n <= 0:
                regs[a] = "..."
                self.vararg_reg = a
            else:
                names = [self.reg_name[a + i] for i in range(n)]
                self.emit(", ".join(names) + " = ...")
                for i in range(n):
                    regs[a + i] = self.reg_name[a + i]
                self.vararg_reg = a + n - 1
        elif op == OP_TFORLOOP:
            pass
        elif op in (OP_FORLOOP, OP_FORPREP, OP_JMP):
            pass
        else:
            self.emit(f"-- unknown opcode {op} A={a} B={b} C={c}")

    def _do_call(self, pc: int, regs: list[str], tail: bool) -> None:
        inst = self.proto.code[pc]
        op, a, b, c, bx, sbx = decode(inst)
        if b == 0:
            last = self.vararg_reg if self.vararg_reg is not None and self.vararg_reg > a else a
            args = [regs[i] for i in range(a + 1, last + 1)]
        else:
            args = [regs[i] for i in range(a + 1, a + b)]
        fn = regs[a]
        # method call: previous SELF stored obj in a+1 and func in a
        call = f"{fn}({', '.join(args)})"
        if tail:
            self.emit("return " + call)
            return
        nret = c - 1
        if nret == 0:
            self.emit(call)
        elif nret == 1:
            self.emit(f"{self.reg_name[a]} = {call}")
            regs[a] = self.reg_name[a]
        elif nret < 0:
            self.emit(f"{self.reg_name[a]} = {call}")
            regs[a] = self.reg_name[a]
        else:
            names = [self.reg_name[a + i] for i in range(nret)]
            self.emit(", ".join(names) + " = " + call)
            for i in range(nret):
                regs[a + i] = self.reg_name[a + i]

    def _cond(self, pc: int, regs: list[str]) -> str:
        inst = self.proto.code[pc]
        op, a, b, c, bx, sbx = decode(inst)
        if op == OP_TEST:
            base = regs[a]
            return f"not {base}" if c else base
        if op == OP_TESTSET:
            base = regs[b]
            return f"not {base}" if c else base
        true_op, false_op = CMPOPS[op]
        left = self.rk(b, regs)
        right = self.rk(c, regs)
        return f"{left} {true_op if a == 0 else false_op} {right}"

    def _do_test(self, pc: int, end: int, regs: list[str]) -> int:
        code = self.proto.code
        jmp = decode(code[pc + 1])
        _, _, _, _, _, sbx = jmp
        false_tgt = pc + 2 + sbx
        cond = self._cond(pc, regs)

        # boolean assignment: EQ; JMP; LOADBOOL; LOADBOOL
        if pc + 3 < len(code):
            op2, a2, b2, c2, _, _ = decode(code[pc + 2])
            op3, a3, b3, c3, _, _ = decode(code[pc + 3])
            if op2 == OP_LOADBOOL and op3 == OP_LOADBOOL and c2 == 1 and false_tgt == pc + 3:
                dest = a2
                self.emit(f"{self.reg_name[dest]} = {cond}")
                regs[dest] = self.reg_name[dest]
                self.skip.add(pc + 1)
                self.skip.add(pc + 2)
                self.skip.add(pc + 3)
                return pc + 4

        then_end = false_tgt
        else_end = None
        if 0 < false_tgt <= len(code):
            prev_pc = false_tgt - 1
            if prev_pc > pc + 1:
                pop, *_rest, psbx = (*decode(code[prev_pc])[:5], decode(code[prev_pc])[5])
                if pop == OP_JMP:
                    skip = false_tgt + psbx
                    if skip > false_tgt:
                        then_end = prev_pc
                        else_end = skip

        # while: last of then is JMP back to pc
        if else_end is None and then_end - 1 > pc + 1:
            pop, *_, psbx = decode(code[then_end - 1])
            if pop == OP_JMP and then_end - 1 + 1 + psbx == pc:
                self.emit(f"while {cond} do")
                self.indent += 1
                self._emit_block(pc + 2, then_end - 1, regs)
                self.indent -= 1
                self.emit("end")
                return then_end

        self.emit(f"if {cond} then")
        self.indent += 1
        self._emit_block(pc + 2, then_end, regs)
        self.indent -= 1
        if else_end is not None:
            self.emit("else")
            self.indent += 1
            self._emit_block(false_tgt, else_end, regs)
            self.indent -= 1
            self.emit("end")
            return else_end
        self.emit("end")
        return then_end

    def _do_numeric_for(self, pc: int, end: int, regs: list[str]) -> int:
        inst = self.proto.code[pc]
        op, a, b, c, bx, sbx = decode(inst)
        loop_pc = pc + 1 + sbx
        body_end = loop_pc
        var = self.reg_name[a + 3]
        self.emit(f"for {var} = {regs[a]}, {regs[a + 1]}, {regs[a + 2]} do")
        self.indent += 1
        regs[a + 3] = var
        self._emit_block(pc + 1, body_end, regs)
        self.indent -= 1
        self.emit("end")
        return loop_pc + 1

    def _do_generic_for(self, pc: int, end: int, regs: list[str]) -> int:
        # JMP to TFORLOOP
        _, _, _, _, _, sbx = decode(self.proto.code[pc])
        tfor_pc = pc + 1 + sbx
        op, a, b, c, bx, sbx2 = decode(self.proto.code[tfor_pc])
        nvars = c
        names = [self.reg_name[a + 3 + i] for i in range(nvars)]
        self.emit(f"for {', '.join(names)} in {regs[a]}, {regs[a + 1]}, {regs[a + 2]} do")
        self.indent += 1
        for i, name in enumerate(names):
            regs[a + 3 + i] = name
        self._emit_block(pc + 1, tfor_pc, regs)
        self.indent -= 1
        self.emit("end")
        return tfor_pc + 2

    def _do_closure(self, pc: int, regs: list[str]) -> int:
        inst = self.proto.code[pc]
        op, a, b, c, bx, sbx = decode(inst)
        child = self.proto.p[bx]
        up_names: list[str] = []
        next_pc = pc + 1
        for i in range(child.nups):
            uop, ua, ub, uc, ubx, usbx = decode(self.proto.code[next_pc])
            if uop == OP_MOVE:
                up_names.append(self.reg_name[ub])
            elif uop == OP_GETUPVAL:
                up_names.append(self.upvalue_names[ub] if ub < len(self.upvalue_names) else f"u{ub}")
            else:
                up_names.append(f"u{i}")
            self.skip.add(next_pc)
            next_pc += 1
        inner = Decompiler(child, indent=0, upvalue_names=up_names)
        raw = inner.decompile().rstrip().splitlines()
        if not raw:
            self.emit(f"{self.reg_name[a]} = function() end")
        else:
            self.emit(f"{self.reg_name[a]} = {raw[0].lstrip()}")
            for line in raw[1:]:
                spaces = len(line) - len(line.lstrip(" "))
                level = spaces // 4
                content = line.lstrip(" ")
                self.lines.append(("    " * (self.indent + level) + content) if content else "")
        regs[a] = self.reg_name[a]
        return next_pc


def decompile_chunk(data: bytes) -> str:
    proto = undump(data)
    src_name = proto.source or "@chunk"
    header = [
        f"-- Decompiled Lua 5.1 chunk {src_name}",
        f"-- linedefined {proto.linedefined}-{proto.lastlinedefined}; "
        f"{len(proto.p)} child proto(s). Locals may be r0/r1 (debug stripped).",
        "",
    ]
    inner = Decompiler(proto, indent=0)
    # chunk is a vararg function with 0 params — emit body only
    body_decompiler = Decompiler(proto, indent=0)
    body_decompiler.indent = 0
    regs = [body_decompiler.reg_name[i] for i in range(proto.maxstack)]
    body_decompiler._emit_block(0, len(proto.code), regs)
    return "\n".join(header + body_decompiler.lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()
    data = Path(args.input).read_bytes()
    if data and data[0] == 0x1C:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from mta_luac_decrypt import decrypt_mta_luac, normalize_luaq

        data, _info = decrypt_mta_luac(data)
        data, _stats = normalize_luaq(data)
    text = decompile_chunk(data)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output} ({len(text)} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
