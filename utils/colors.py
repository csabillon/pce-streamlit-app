# utils/colors.py

# 1) OPEN / CLOSE states → keep SLB Extended Green & Red
OC_COLORS = {
    "OPEN":  "#3CBE46",  # Ext Green 4 
    "CLOSE": "#F03D2E",  # Ext Red 4   
}

# 2) POD COLORS → SLB Core Blue & custom warm orange
BY_COLORS = {
    "Blue Pod":   "#6E8CC8",  # SLB Frost Blue 1
    "Yellow Pod": "#E87722",  # custom warm orange
}

# 3) FLOW-CATEGORY COLORS → Analogous Teal → Purple → Red
FLOW_COLORS = {
    "Low":  "#50CDB4",  # Ext Teal 5   
    "Mid":  "#875EC7",  # Ext Purple 5 
    "High": "#EB5E5E",  # Ext Red 5   
}

# 4) FLOW CATEGORY ORDER
FLOW_CATEGORY_ORDER = ["Low", "Mid", "High"]
