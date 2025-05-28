from csrspy.enums import Reference, VerticalDatum

# Constants
REQUIRED_FILE_COLS_GEOGRAPHIC = [
    "Timestamp",
    "Filename",
    "Origin (Latitude[deg]",
    "Longitude[deg]",
    "Altitude[m])",
    "Roll(X)[deg]",
    "Pitch(Y)[deg]",
    "Yaw(Z)[deg]",
    "Omega[deg]",
    "Phi[deg]",
    "Kappa[deg]",
]

REQUIRED_FILE_COLS_CARTESIAN = [
    "Timestamp",
    "Filename",
    "Origin (X[m]",
    "Y[m]",
    "Z[m])",
    "Roll(X)[deg]",
    "Pitch(Y)[deg]",
    "Yaw(Z)[deg]",
    "Omega[deg]",
    "Phi[deg]",
    "Kappa[deg]",
]

VERTICAL_DATUM_OPTS = [
    ("WGS84", VerticalDatum.WGS84),
    ("GRS80", VerticalDatum.GRS80),
    ("CGG2013a", VerticalDatum.CGG2013A),
    ("CGG2013", VerticalDatum.CGG2013),
    ("HT2_2010v70", VerticalDatum.HT2_2010v70),
]

REFERENCE_FRAME_OPTS = [
    ("WGS84", Reference.WGS84),
    ("NAD83 (CSRS)", Reference.NAD83CSRS),
    ("ITRF1988", Reference.ITRF88),
    ("ITRF1989", Reference.ITRF89),
    ("ITRF1990", Reference.ITRF90),
    ("ITRF1991", Reference.ITRF91),
    ("ITRF1992", Reference.ITRF92),
    ("ITRF1993", Reference.ITRF93),
    ("ITRF1994", Reference.ITRF94),
    ("ITRF1996", Reference.ITRF96),
    ("ITRF1997", Reference.ITRF97),
    ("ITRF2000", Reference.ITRF00),
    ("ITRF2005", Reference.ITRF05),
    ("ITRF2008", Reference.ITRF08),
    ("ITRF2014", Reference.ITRF14),
    ("ITRF2020", Reference.ITRF20),
]

COORD_TYPE_OPTS = ["Geographic", "Projected", "Cartesian"]
