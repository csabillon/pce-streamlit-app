# logic/tag_maps.py
def get_rig_tags(rig):
    if rig == "Drillmax":
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
        # Drillmax Well Pressure is ScaledValue12
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
        # Other rigs Well Pressure is ScaledValue48
        pressure_map["Well Pressure"] = f"{pressure_base}.ScaledValue48"

    for v in valve_map:
        pressure_map.setdefault(v, default_press_tag)

    return {
        "valve_map": valve_map,
        "vol_ext": vol_ext,
        "active_pod_tag": active_pod_tag,
        "pressure_map": pressure_map,
        "eds_base_tag": eds_base_tag,
    }
