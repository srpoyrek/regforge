"""The lint-demo device: a deliberately-flawed chip the linter must flag.

`lint_demo.svd` trips the addressBlock/overlap checks (and a resolve warning) on
purpose. These tests lock the exact findings -- the whole point of the fixture --
and confirm regforge still emits valid, byte-stable C for a flawed footprint.
"""

from regforge import __version__
from regforge.check import Severity, run_checks
from regforge.provenance import Provenance, sha256_file
from regforge.readers.svd import SvdReader
from regforge.resolve import expand_dim, resolve_defaults, resolve_derived
from regforge.writers.c import CWriter

GOLDEN_COMMAND = "regforge tests/fixtures/svd/lint_demo.svd -o tests/golden/c/lint_demo.h"


def test_cross_peripheral_overlaps_are_errors(lint_demo_device):
    errors = [f.message for f in run_checks(lint_demo_device) if f.severity is Severity.ERROR]
    assert len(errors) == 4
    assert any("UART and TIMER" in m and "overlapping" in m for m in errors)
    # Two copies on one address: the <dimIncrement> 0 case, named as such.
    assert any("SAME0 and SAME1" in m and "one <dim> declaration (SAME%s)" in m for m in errors)
    # Copies whose stride is smaller than their footprint.
    assert any(
        "OVL0 and OVL1" in m and "dimIncrement is smaller than the footprint" in m for m in errors
    )
    # The last copy running into an unrelated peripheral.
    assert any("SER3 and SPIX" in m and "SER3 was expanded from SER%s" in m for m in errors)


def test_array_addressing_warnings_are_flagged(lint_demo_device):
    warnings = [f.message for f in run_checks(lint_demo_device) if f.severity is Severity.WARNING]
    assert any("PWMX.CH[4]: array stride 8" in m and "CH0..CH3" in m for m in warnings)
    assert any("FIFOX.DATA%s: DATA8..DATA15 (8 of its 16 copies" in m for m in warnings)
    assert not any(m.startswith("FIFOX.DATA9") for m in warnings)  # one line, not eight


def test_reader_reports_increment_without_dim(lint_demo_svd_path):
    reader = SvdReader()
    reader.read(lint_demo_svd_path)
    assert reader.warnings == ["NOTDIM: <dimIncrement> without <dim> -- ignored"]


def test_addressblock_warnings_are_flagged(lint_demo_device):
    messages = " ".join(
        f.message for f in run_checks(lint_demo_device) if f.severity is Severity.WARNING
    )
    assert "FLASH.FAR" in messages and "outside" in messages  # register outside its block
    assert "DMA: addressBlocks" in messages and "overlap" in messages  # intra-peripheral overlap


def test_resolve_warns_on_unspecified_access(lint_demo_svd_path):
    # Read fresh: the resolved fixture has already consumed the warnings.
    device = SvdReader().read(lint_demo_svd_path)
    warnings = resolve_defaults(device)
    assert any("MISC.REG" in w and "access unspecified" in w for w in warnings)


def test_expand_warnings_are_locked(lint_demo_svd_path):
    device = SvdReader().read(lint_demo_svd_path)
    findings = expand_dim(device)
    messages = [f.message for f in findings]
    assert (
        "TMRU%s: interrupt 'TMRU_IRQ' (vector 43) has no %s -- attached to TMRU0 only; "
        "TMRU1 have no vector of their own"
    ) in messages
    assert not any(m.startswith("TMRX%s") for m in messages)  # per-copy names: no finding
    assert any("DMAX.CH[%s]: dimIndex ignored" in m for m in messages)
    assert any("TMRY: <dim> on a name without a %s" in m and "TMRY0..TMRY1" in m for m in messages)
    assert any("GHOST%s: <dim> 0 declares nothing -- dropped" in m for m in messages)
    errors = [f.message for f in findings if f.severity is Severity.ERROR]
    assert sorted(errors) == [
        "SAME%s: <dimIncrement> 0 puts all 2 copies at one address",
        "TMRW%s: <dim> 2 without <dimIncrement> -- the copies' addresses are unknown; "
        "emitted as one instance, TMRW",
        "TMRZ%s: dimIndex labels repeat (0,0,1) -- two copies cannot share a name; "
        "falling back to 0..2",
    ]
    assert len(findings) == 7


def test_cluster_derived_from_is_reported(lint_demo_svd_path):
    device = SvdReader().read(lint_demo_svd_path)
    expand_dim(device)
    warnings = resolve_derived(device)
    assert any("DMAX.EXTRA: derivedFrom 'CH' on a cluster" in w for w in warnings)


def test_derived_from_a_template_is_resolved_to_its_first_copy(lint_demo_svd_path):
    device = SvdReader().read(lint_demo_svd_path)
    expand_dim(device)
    warnings = resolve_derived(device)
    template = [w for w in warnings if "names the template" in w]
    assert (
        "TMRV: derivedFrom names the template 'TMRX%s' -- resolved to its first copy, TMRX0"
        in template
    )
    # SERX%s inherited <dim> 4 from SER%s (own stride 0x200), so four copies each resolve.
    assert [w.split(":")[0] for w in template if w.startswith("SERX")] == [
        "SERX0",
        "SERX1",
        "SERX2",
        "SERX3",
    ]
    by_name = {p.name: p for p in device.peripherals}
    assert [by_name[f"SERX{i}"].base_address for i in range(4)] == [
        0x40063000 + 0x200 * i for i in range(4)
    ]
    assert [r.name for r in by_name["SERX3"].registers] == ["CR"]


def test_dimmed_instances_share_the_vector_in_the_header(lint_demo_device):
    output = CWriter().render(lint_demo_device)
    assert output.count("#define LD_TMRU_IRQ_IRQ ") == 1  # copy 0 only
    assert "#define LD_TMRY1_BASE (0x40058100UL)" in output  # index appended, header compiles
    assert (
        "#define LD_TMRX0_IRQ LD_TMRX0_IRQn  "
        "/* vector 41 -- shared with LD_TMRX1; demux in ISR */" in output
    )
    assert (
        "#define LD_TMRX1_IRQ LD_TMRX1_IRQn  "
        "/* vector 41 -- shared with LD_TMRX0; demux in ISR */" in output
    )


def test_header_matches_golden(lint_demo_device, lint_demo_svd_path, lint_demo_golden_path):
    provenance = Provenance(
        source_path="tests/fixtures/svd/lint_demo.svd",
        source_sha256=sha256_file(lint_demo_svd_path),
        tool_version=__version__,
        command=GOLDEN_COMMAND,
    )
    generated = CWriter().render(lint_demo_device, provenance)
    assert generated == lint_demo_golden_path.read_text(encoding="utf-8")

    # Note: the demo header is compiled across the full toolchain matrix by
    # tests/writers/c/test_compiles.py::test_lint_demo_header_compiles.


def test_alternate_register_findings_are_locked(lint_demo_svd_path):
    from regforge.resolve import resolve_alternates

    device = SvdReader().read(lint_demo_svd_path)
    expand_dim(device)
    resolve_derived(device)
    findings = resolve_alternates(device)
    assert sorted(f.message for f in findings if f.severity is Severity.ERROR) == [
        "ALTX.D: alternateRegister 'NOPE' -- no register of that name in ALTX; treated as an "
        "ordinary register"
    ]
    assert sorted(f.message for f in findings if f.severity is Severity.WARNING) == [
        "ALTX.B: alternateRegister 'A_Out' is at offset 0x0, not 0x8 -- an alternate view must "
        "share the offset; left unrelated",
        "ALTX.C: alternateRegister names itself -- ignored",
        "ALTX.G: alternateRegister 'F' has a different <dim> shape -- left unrelated",
    ]


def test_alternate_register_check_findings_are_locked(lint_demo_device):
    warnings = [f.message for f in run_checks(lint_demo_device) if f.severity is Severity.WARNING]
    assert (
        "ALTX.A_Out: alternate views disagree on resetValue (A_Out=0x0, A_In=0xFF) -- one "
        "register has one reset"
    ) in warnings
    assert (
        "ALTX.CCR_X: the common prefix 'CCR' is already a member of the block -- the union is "
        "named CCR_X and its views keep their full names"
    ) in warnings
