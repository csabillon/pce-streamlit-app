# logic/tag_maps.py

from functools import lru_cache

@lru_cache(maxsize=8)
def get_rig_tags(rig):
    if rig == "Drillmax":
        _prefix = f"pi-no:{rig}.BOP.CBM.Valve_Status"
        valve_map = {
            "Upper Annular": _prefix + "1",
            "Lower Annular": _prefix + "5",
            "LMRP Connector": _prefix + "2",
            "Upper Blind Shear": _prefix + "6",
            "Casing Shear Ram": _prefix + "7",
            "Lower Blind Shear": _prefix + "70",
            "Upper Pipe Ram": _prefix + "8",
            "Middle Pipe Ram": _prefix + "9",
            "Lower Pipe Ram": _prefix + "10",
            "Test Ram": _prefix + "74",
            "Wellhead Connector": _prefix + "11",
        }
        vol_ext = f"pi-no:{rig}.BOP.CBM.HPU_MAINACC_ACC_NoReset"
        active_pod_tag = f"pi-no:{rig}.BOP.CBM.ActiveSem"
        pressure_base = f"pi-no:{rig}.BOP.CBM"
        eds_base_tag = f"pi-no:{rig}.BOP.CBM."
        pressure_map = {
            **{v: f"{pressure_base}.ScaledValue{n}" for v, n in [
                ("Upper Annular", 8), ("Lower Annular", 8),
                ("Wellhead Connector", 10), ("LMRP Connector", 10),
            ]},
        }
        default_press_tag = f"{pressure_base}.ScaledValue11"
        pressure_map["Well Pressure"] = f"{pressure_base}.ScaledValue12"
    else:
        _prefix = f"pi-no:{rig}.BOP.CBM.Valve_Status"
        valve_map = {
            "Upper Annular": _prefix + "1",
            "Lower Annular": _prefix + "5",
            "LMRP Connector": _prefix + "2",
            "Upper Blind Shear": _prefix + "6",
            "Casing Shear Ram": _prefix + "7",
            "Lower Blind Shear": _prefix + "14",
            "Upper Pipe Ram": _prefix + "8",
            "Middle Pipe Ram": _prefix + "9",
            "Lower Pipe Ram": _prefix + "10",
            "Test Ram": _prefix + "74",
            "Wellhead Connector": _prefix + "11",
        }
        vol_ext = f"pi-no:{rig}.BOP.Div_Hpu.HPU_MAINACC_ACC_NONRST"
        active_pod_tag = f"pi-no:{rig}.BOP.CBM.ActiveSem_CBM"
        pressure_base = f"pi-no:{rig}.BOP.DCP"
        eds_base_tag = f"pi-no:{rig}.BOP.SEM_"
        pressure_map = {
            **{v: f"{pressure_base}.ScaledValue{n}" for v, n in [
                ("Upper Annular", 12), ("Lower Annular", 14),
                ("Wellhead Connector", 20), ("LMRP Connector", 16),
            ]},
        }
        default_press_tag = f"{pressure_base}.ScaledValue18"
        pressure_map["Well Pressure"] = f"{pressure_base}.ScaledValue48"

    for v in valve_map:
        pressure_map.setdefault(v, default_press_tag)

    simple_map_rams = {
        256: "VENT",
        513: "OPEN", 514: "CLOSE", 515: "OPEN", 516: "CLOSE",
        1025: "OPEN", 1026: "CLOSE", 1027: "OPEN", 1028: "CLOSE",
        4096: "ERROR",
    }
    function_map_rams = {
        256: "VENT",
        513: "OPEN", 514: "CLOSE", 515: "OPEN VENT", 516: "CLOSE VENT",
        1025: "OPEN", 1026: "CLOSE", 1027: "OPEN VENT", 1028: "CLOSE VENT",
        4096: "ERROR",
    }
    simple_map_connector = {
        256: "VENT",
        513: "LATCH", 514: "UNLATCH", 515: "LATCH", 516: "UNLATCH",
        1025: "LATCH", 1026: "UNLATCH", 1027: "LATCH", 1028: "UNLATCH",
        4096: "ERROR",
    }
    function_map_connector = {
        256: "VENT",
        513: "LATCH", 514: "UNLATCH", 515: "LATCH VENT", 516: "UNLATCH VENT",
        1025: "LATCH", 1026: "UNLATCH", 1027: "LATCH VENT", 1028: "UNLATCH VENT",
        4096: "ERROR",
    }

    per_valve_simple_map = {}
    per_valve_function_map = {}
    for v in valve_map:
        if "Connector" in v:
            per_valve_simple_map[v] = simple_map_connector
            per_valve_function_map[v] = function_map_connector
        else:
            per_valve_simple_map[v] = simple_map_rams
            per_valve_function_map[v] = function_map_rams

    return {
        "valve_map": valve_map,
        "vol_ext": vol_ext,
        "active_pod_tag": active_pod_tag,
        "pressure_map": pressure_map,
        "eds_base_tag": eds_base_tag,
        "per_valve_simple_map": per_valve_simple_map,
        "per_valve_function_map": per_valve_function_map,
    }
