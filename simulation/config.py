
# Simulation Configuration

# ---------------------------------------------------------
# 1. Arrival Rates (Average Patients per Hour)
# Keys: 0-23 (Hour of Day)
# Values: Mean arrival rate for Poisson distribution
# ---------------------------------------------------------
ARRIVAL_RATES = {
    0: (2.84, 1.53),
    1: (2.46, 1.34),
    2: (2.26, 1.30),
    3: (2.09, 1.15),
    4: (1.97, 1.08),
    5: (2.01, 1.11),
    6: (2.32, 1.28),
    7: (2.87, 1.53),
    8: (4.14, 2.06),
    9: (5.13, 2.33),
    10: (5.49, 2.44),
    11: (5.73, 2.56),
    12: (5.85, 2.54),
    13: (5.65, 2.46),
    14: (5.63, 2.50),
    15: (5.69, 2.38),
    16: (5.85, 2.47),
    17: (6.04, 2.57),
    18: (5.83, 2.46),
    19: (5.65, 2.40),
    20: (5.46, 2.42),
    21: (5.07, 2.31),
    22: (4.38, 2.17),
    23: (3.53, 1.84),
}

# ---------------------------------------------------------
# 2. Department Capacities & Initial State
# ---------------------------------------------------------
# Capacities (Beds/Rooms)
CAPACITY = {
    'ER': 75,  
    'Surgery': 9,
    'CriticalCare': 18,
    'StepDown': 40 
}

# Initial State
INITIAL_STAFF = {
    'ER': 18,
    'Surgery': 6,
    'CriticalCare': 13,
    'StepDown': 24
}

INITIAL_PATIENTS = {
    'ER': 16,
    'Surgery': 4,
    'CriticalCare': 12,
    'StepDown': 22
}

# ---------------------------------------------------------
# 3. Patient Flow Probabilities
# ---------------------------------------------------------

# ER Entry
AMBULANCE_RATE = 0.18 # 18% of ER entries are ambulances

# ER Disposition (Destination after ER)
# "Of the ER admissions after being seen for an hour..."
ER_DISPOSITION = {
    'Surgery': 0.05,
    'CriticalCare': 0.10,
    'StepDown': 0.20,
    'Home': 0.65 # Remaining 65%
}

# PMF for Transfers (Assumed based on summation logic)
# (Move count, Probability)
TRANSFER_RATES = {
    ('Surgery', 'CriticalCare'): {0: 0.5417, 1: 0.3750, 2: 0.0417, 3: 0.0416}, # Adjusted 0.417 -> 0.0417 to sum to ~1
    ('Surgery', 'StepDown'): {0: 0.4583, 1: 0.2083, 2: 0.2083, 3: 0.1250},   # Sum: 0.9999
    ('CriticalCare', 'StepDown'): {0: 0.6250, 1: 0.2500, 2: 0.1250, 3: 0.0}
}

# Direct Entry from Outside (PMF)
DIRECT_ENTRY_RATES = {
    'Surgery': {0: 0.792, 1: 0.125, 2: 0.042, 3: 0.041},
    'StepDown': {0: 0.667, 1: 0.292, 2: 0.042, 3: 0.0},
    'CriticalCare': {0: 0.833, 1: 0.167, 2: 0.0, 3: 0.0}
}

# Step Down Departures (Going Home)
# "Chance per number of people will leave from step down"
STEP_DOWN_DEPARTURE_RATES = {
    0: 0.1667, 1: 0.1667, 2: 0.2500, 3: 0.2500, 4: 0.0833, 5: 0.0833
}

# ---------------------------------------------------------
# 4. Costs
# ---------------------------------------------------------
COSTS = {
    'ER': {'Wait': 150, 'Diversion': 5000, 'ExtraStaff': 40},
    'Surgery': {'Wait': 3750, 'ExtraStaff': 40},
    'CriticalCare': {'Wait': 3750, 'ExtraStaff': 40},
    'StepDown': {'Wait': 3750, 'ExtraStaff': 40}
}

# ---------------------------------------------------------
# 5. Timing & Constraints
# ---------------------------------------------------------
DEFAULT_SERVICE_TIME = 1.0 # Hours (Assumed since not explicitly varied per dept in prompt)
CHECK_INTERVAL = 1.0 # Hour (Patients check efficiently every hour)

