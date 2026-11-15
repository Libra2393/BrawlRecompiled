"""Shared patterns for the PAL remap scripts: LIT/MACRO/FUNC/SDA find US addresses in the wiicompiled/runtime C++
source, NOT_ADDR lists literals in the address range that are not addresses, TEXT is plain string swaps.
Imported by remap_runtime_pal.py (addresses from PalAddr) and remap_from_log.py (addresses from the log)."""
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
# After the addresses: the disc's identity (text, so the address pass never sees it). Partition boot.bin, which the
# game reads at 0x80000000 and game_folder.cpp checks, says revision 0 on the PAL disc (its outer header says 1).
TEXT = [("0x52534245", "0x52534250"), ("/52534245/", "/52534250/"),  # game code RSBE -> RSBP, NAND title folders
        ('{0x80000004u, 0x30310001u, "Disc maker/id"});  // "01", disc 0, revision 1 (boot.bin)',
         '{0x80000004u, 0x30310000u, "Disc maker/id"});  // "01", disc 0, revision 0 (the PAL partition\'s boot.bin)'),
        ("constexpr int kRevision = 1;", "constexpr int kRevision = 0;  // the PAL partition's boot.bin (Dolphin shows 1)"),
        ("This port runs only revision 0 (Dolphin shows it under Properties > Info).",
         "This port runs only the PAL disc Dolphin shows as revision 1 (Properties > Info)."),
        ("(USA, RSBE01, revision 1)", "(Europe, RSBP01, revision 1)"), ("(USA, RSBE01)", "(Europe, RSBP01)"),
        ("(RSBE01 revision 1)", "(Europe, RSBP01)"), ("RSBE01", "RSBP01")]
