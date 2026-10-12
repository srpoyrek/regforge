"""HTML register-reference writer: one renderer class per element, composed recursively.

The renderers sit in folders that nest the way the elements contain one another, and every
module holds one class::

    html/
      writer.py            HtmlWriter, the entry point
      context.py           ElementHtml (a block, filled from a template), LeafHtml (a phrase)
      wording.py           number formats and small helpers that belong to no element
      device/              DeviceHtml, DeviceFacts, CpuHtml, FactsHtml, LicenseHtml, ProvenanceHtml
        peripheral/        PeripheralHtml, AddressBlockHtml, InterruptHtml, DimHtml, placement
          register/        RegisterHtml, and the leaves of its own settings: AccessHtml,
                           DataTypeHtml, ProtectionHtml, ResetHtml, ModifiedWriteValuesHtml,
                           ReadActionHtml, WriteConstraintHtml, SideEffectsHtml
            bit_map/       BitMapHtml, BitHtml
            field/         FieldHtml
              enum_set/    EnumSetHtml, EnumValueHtml

A field says its access, its reset and what a write or a read does in the register's words, so
it uses the leaves in the register's folder. The tests mirror this tree, one file for each
module (``tests/writers/html/test_layout.py`` keeps it so); the templates stay together in
``regforge/writers/templates/html/``, one for each block.
"""

from regforge.writers.html.writer import HtmlWriter as HtmlWriter
