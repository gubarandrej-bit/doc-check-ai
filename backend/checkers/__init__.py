from checkers.base import Checker, CheckResult
from checkers import cable_journal, cable_selection, power_sources, batteries, schematics, spec_crosscheck

CHECKERS = [
    cable_journal.CableJournalSpecChecker,
    cable_selection.CableSelectionChecker,
    power_sources.PowerSourcesChecker,
    batteries.BatteryChecker,
    schematics.SchematicChecker,
    spec_crosscheck.EquipmentSpecChecker,
]