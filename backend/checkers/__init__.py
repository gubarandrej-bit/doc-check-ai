"""Пакет детерминированных проверок."""
from checkers.base import Checker, CheckResult
from checkers import cable_journal, cable_selection, power_sources, batteries
from checkers import schematics, spec_crosscheck
from checkers import fire_coverage, fire_cable, fire_power, fire_soue, fire_docs
from checkers import scs, video, skud, security_alarm, asu_asutp

CHECKERS = [
    cable_journal.CableJournalSpecChecker,
    cable_selection.CableSelectionChecker,
    power_sources.PowerSourcesChecker,
    batteries.BatteryChecker,
    schematics.SchematicChecker,
    spec_crosscheck.EquipmentSpecChecker,
    fire_coverage.FireEquipmentCoverageChecker,
    fire_cable.FireAlarmCableChecker,
    fire_power.FirePowerDualChecker,
    fire_soue.FireSoueChecker,
    fire_docs.FireDocsCompleteChecker,
    scs.ScsChecker,
    video.VideoSurveillanceChecker,
    skud.SkudChecker,
    security_alarm.SecurityAlarmChecker,
    asu_asutp.AsuAsutpChecker,
]