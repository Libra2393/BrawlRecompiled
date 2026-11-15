"""Shared patterns for the region remap scripts: LIT/MACRO/FUNC/SDA find US addresses in the wiicompiled/runtime C++
source, NOT_ADDR lists literals in the address range that are not addresses. The disc identity swaps (TEXT) are
per region, in each project's region.json. Imported by remap_runtime_region.py and remap_from_log_region.py."""
import re

LIT = re.compile(r"(?<![0-9A-Za-z_])0x(8[01][0-9A-Fa-f]{6}|9[4-7][0-9A-Fa-f]{6})(u?)(?![0-9A-Fa-f])")
# Function overrides take the address bare: PPC_NATIVE_OVERRIDE_VOID(801D8690, ...). (NSMBW_GX_POKE_NOOP's address
# only names the function it defines; the override after it carries the real one.)
MACRO = re.compile(r"\b(PPC_NATIVE_OVERRIDE\w*\(\s*)([0-9A-Fa-f]{8})\b")
# Calls into translated guest code by the translator's own symbol name: func_801D66A8(cpu).
FUNC = re.compile(r"\bfunc_([0-9A-Fa-f]{8})\b")
SDA = re.compile(r"(r13 - 0x|Sda1Offset = 0x|OffsetFromR13 = 0x)([0-9A-Fa-f]{4})")
# Values in the address range that are not guest addresses.
NOT_ADDR = {("src/hle/gx/gx_dl.cpp", 0x80808081)}
