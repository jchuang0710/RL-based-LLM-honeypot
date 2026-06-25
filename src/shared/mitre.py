"""MITRE ATT&CK state parsing and index translation."""

from __future__ import annotations

import re


TACTIC_IDS = [
    "TA0001", "TA0002", "TA0003", "TA0004", "TA0005", "TA0006",
    "TA0007", "TA0008", "TA0009", "TA0011", "TA0010", "TA0040",
]

TECHNIQUE_IDS = [
    "T1548", "T1134", "T1531", "T1087", "T1098", "T1650", "T1583",
    "T1595", "T1557", "T1071", "T1010", "T1560", "T1123", "T1119",
    "T1020", "T1197", "T1547", "T1037", "T1176", "T1217", "T1185",
    "T1110", "T1612", "T1115", "T1651", "T1580", "T1538", "T1526",
    "T1619", "T1059", "T1092", "T1586", "T1554", "T1584", "T1609",
    "T1613", "T1659", "T1136", "T1543", "T1555", "T1485", "T1132",
    "T1486", "T1530", "T1602", "T1213", "T1005", "T1039", "T1025",
    "T1565", "T1001", "T1074", "T1030", "T1622", "T1491", "T1140",
    "T1610", "T1587", "T1652", "T1006", "T1561", "T1484", "T1482",
    "T1189", "T1568", "T1114", "T1573", "T1499", "T1611", "T1585",
    "T1546", "T1480", "T1048", "T1041", "T1011", "T1052", "T1567",
    "T1190", "T1203", "T1212", "T1211", "T1068", "T1210", "T1133",
    "T1008", "T1083", "T1222", "T1657", "T1495", "T1187", "T1606",
    "T1592", "T1589", "T1590", "T1591", "T1615", "T1200", "T1564",
    "T1665", "T1574", "T1562", "T1656", "T1525", "T1070", "T1202",
    "T1105", "T1490", "T1056", "T1559", "T1534", "T1570", "T1654",
    "T1036", "T1556", "T1578", "T1112", "T1601", "T1111", "T1621",
    "T1104", "T1106", "T1599", "T1498", "T1046", "T1135", "T1040",
    "T1095", "T1571", "T1027", "T1588", "T1137", "T1003", "T1201",
    "T1120", "T1069", "T1566", "T1598", "T1647", "T1653", "T1542",
    "T1057", "T1055", "T1572", "T1090", "T1012", "T1620", "T1219",
    "T1563", "T1021", "T1018", "T1091", "T1496", "T1207", "T1014",
    "T1053", "T1029", "T1113", "T1597", "T1596", "T1593", "T1594",
    "T1505", "T1648", "T1489", "T1129", "T1072", "T1518", "T1608",
    "T1528", "T1649", "T1558", "T1539", "T1553", "T1195", "T1218",
    "T1082", "T1614", "T1016", "T1049", "T1033", "T1216", "T1007",
    "T1569", "T1529", "T1124", "T1080", "T1221", "T1205", "T1537",
    "T1127", "T1199", "T1552", "T1535", "T1550", "T1204", "T1078",
    "T1125", "T1497", "T1600", "T1102", "T1047", "T1220",
]


def parse_state_response(
    response: str,
    *,
    default_tactic: str = "TA0001",
    default_technique: str = "T1003",
) -> tuple[str, str]:
    """Extract a tactic and base technique ID from an LLM response."""
    tactic_match = re.search(r"\bTA\d{4}\b", response)
    technique_match = re.search(r"\bT\d{4}(?:\.\d{3})?\b", response)
    tactic = tactic_match.group(0) if tactic_match else default_tactic
    technique = technique_match.group(0)[:5] if technique_match else default_technique
    return tactic, technique


def tactic_index(tactic: str, default: int = 1) -> int:
    return TACTIC_IDS.index(tactic) if tactic in TACTIC_IDS else default


def technique_index(technique: str, default: int = 1) -> int:
    base_technique = technique[:5]
    return TECHNIQUE_IDS.index(base_technique) if base_technique in TECHNIQUE_IDS else default
