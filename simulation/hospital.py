
import simpy
import random
import numpy as np
from .config import (
    ARRIVAL_RATES, CAPACITY, COSTS, INITIAL_STAFF, INITIAL_PATIENTS,
    TRANSFER_RATES, DIRECT_ENTRY_RATES, ER_DISPOSITION,
    AMBULANCE_RATE, STEP_DOWN_DEPARTURE_RATES
)

from .department import Department
from .patient import Patient

class HospitalSimulation:
    def __init__(self, duration_hours=24, staffing_schedule=None):
        """
        staffing_schedule: Dict {Hour: {'ER': count, ...}}
        If None, uses INITIAL_STAFF constantly.
        """
        self.env = simpy.Environment()
        self.duration = duration_hours
        self.staffing_schedule = staffing_schedule
        
        # 1. Initialize Departments
        # If schedule provided, use Hour 0 counts for init?
        # Or standard init?
        # Let's use standard init for object creation, update immediately if schedule exists.
        
        self.initial_staff_counts = INITIAL_STAFF
        if self.staffing_schedule:
            # Use Hour 0 if available
            if 0 in self.staffing_schedule:
                self.initial_staff_counts = self.staffing_schedule[0]
            
        self.departments = {
            'ER': Department(self.env, 'ER', INITIAL_PATIENTS['ER'], self.initial_staff_counts.get('ER', 0)),
            'Surgery': Department(self.env, 'Surgery', INITIAL_PATIENTS['Surgery'], self.initial_staff_counts.get('Surgery', 0)),
            'CriticalCare': Department(self.env, 'CriticalCare', INITIAL_PATIENTS['CriticalCare'], self.initial_staff_counts.get('CriticalCare', 0)),
            'StepDown': Department(self.env, 'StepDown', INITIAL_PATIENTS['StepDown'], self.initial_staff_counts.get('StepDown', 0))
        }
        
        # 2. State & Metrics
        self.total_patients = 0
        self.total_cost = 0
        self.total_staff_setup_cost = 0
        self.total_staff_hourly_cost = 0
        self.last_hour_temps = 0 # Track for hiring cost

    def run(self):
        # Start core processes
        self.env.process(self.arrival_generator())
        self.env.process(self.direct_arrival_generator())
        self.env.process(self.transfer_manager())
        self.env.process(self.random_event_manager())
        self.env.process(self.hourly_staff_manager())
        
        # Run
        self.env.run(until=self.duration)
        
        # Final Calculation
        self.calculate_total_cost()
        return self.total_cost

    def arrival_generator(self):
        for hour in range(self.duration):
            mean, std_dev = ARRIVAL_RATES.get(hour % 24, (2.0, 1.0))
            num_arrivals = max(0, int(np.round(np.random.normal(mean, std_dev))))
            for _ in range(num_arrivals):
                delay = random.random()
                self.env.process(self.handle_er_arrival(delay))
            yield self.env.timeout(1.0)

    def handle_er_arrival(self, delay):
        yield self.env.timeout(delay)
        p = Patient(self.total_patients, self.env.now)
        self.total_patients += 1
        dept = self.departments['ER']
        
        is_ambulance = random.random() < AMBULANCE_RATE
        
        # Check Capacity (Bed + Staff availability implicitly checked by queue size/flow? No, explicit diversion)
        # "if you can not take ambulances they will need to be diverted"
        # "take" implied entering the queue? Or entering treatment?
        # Usually implies entering queue is possible unless physically full.
        # But wait, "Wait times" implies queue.
        # So "Not take" means "Queue Full"?
        # Or "No beds"?
        # Let's assume diversion if NO BEDS.
        
        # Check Real Bed Availability (ignoring events/blockers?)
        # department.get_available_resources returns Free Beds.
        free_beds, _ = dept.get_available_resources()
        
        if is_ambulance and free_beds <= 0:
            dept.total_diversion_cost += COSTS['ER']['Diversion']
            p.status = 'Diverted'
            return

        dept.log_patient_entry(p)
        
        with dept.beds.request() as bed_req, dept.staff.request() as staff_req:
            yield bed_req & staff_req
            dept.admit_patient(p)
            yield self.env.timeout(1.0) # Treatment
            self.process_er_disposition(p)
            dept.discharge_patient(p)

    def process_er_disposition(self, patient):
        r = random.random()
        if r < 0.05: target = 'Surgery'
        elif r < 0.15: target = 'CriticalCare'
        elif r < 0.35: target = 'StepDown'
        else: target = 'Home'
        
        if target == 'Home':
            patient.status = 'Discharged'
        else:
            self.env.process(self.transfer_patient(patient, target))

    def transfer_patient(self, patient, target_name):
        target_dept = self.departments[target_name]
        
        # Arrivals Waiting Penalty Logic
        free_beds, free_staff = target_dept.get_available_resources()
        if free_beds <= 0 or free_staff <= 0:
            target_dept.total_wait_cost += COSTS[target_name]['Wait']
            
        target_dept.log_patient_entry(patient)
        
        with target_dept.beds.request() as bed_req, target_dept.staff.request() as staff_req:
            yield bed_req & staff_req
            target_dept.admit_patient(patient)
            
            # Wait for Transfer Event
            patient.transfer_event = self.env.event()
            yield patient.transfer_event
            
            target_dept.discharge_patient(patient)

    def direct_arrival_generator(self):
        for hour in range(self.duration):
            for dept_name, pmf in DIRECT_ENTRY_RATES.items():
                if dept_name not in self.departments: continue
                
                vals = list(pmf.keys())
                weights = list(pmf.values())
                count = random.choices(vals, weights=weights, k=1)[0]
                
                for _ in range(count):
                    p = Patient(self.total_patients, self.env.now)
                    self.total_patients += 1
                    self.env.process(self.transfer_patient(p, dept_name))
            yield self.env.timeout(1.0)

    def transfer_manager(self):
        while True:
            yield self.env.timeout(1.0)
            
            # Pathways
            pathways = [('Surgery', 'CriticalCare'), ('Surgery', 'StepDown'), ('CriticalCare', 'StepDown')]
            for src, dst in pathways:
                pmf = TRANSFER_RATES.get((src, dst), {})
                if not pmf: continue
                vals, weights = list(pmf.keys()), list(pmf.values())
                count = random.choices(vals, weights=weights, k=1)[0]
                
                src_dept = self.departments[src]
                candidates = [p for p in src_dept.active_patients if hasattr(p, 'transfer_event') and not p.transfer_event.triggered]
                to_move = candidates[:count]
                for p in to_move:
                    p.transfer_event.succeed(value=dst)
                    self.env.process(self.transfer_patient(p, dst))
            
            # Step Down -> Home
            pmf = STEP_DOWN_DEPARTURE_RATES
            vals, weights = list(pmf.keys()), list(pmf.values())
            count = random.choices(vals, weights=weights, k=1)[0]
            sd_dept = self.departments['StepDown']
            candidates = [p for p in sd_dept.active_patients if hasattr(p, 'transfer_event') and not p.transfer_event.triggered]
            to_go_home = candidates[:count]
            for p in to_go_home:
                p.transfer_event.succeed(value='Home')
                p.status = 'Discharged'

    def random_event_manager(self):
        while True:
            delay = random.randint(2, 4)
            yield self.env.timeout(delay)
            
            dept_name = random.choice(['ER', 'Surgery', 'CriticalCare', 'StepDown'])
            dept = self.departments[dept_name]
            
            event_type = 'staff_leave'
            duration = 1
            
            if dept_name == 'ER':
                 if random.random() < 0.5: duration = max(1, 24 - (self.env.now % 24))
            elif dept_name == 'Surgery': event_type = 'room_close'
            elif dept_name == 'CriticalCare': event_type = 'room_close'
            elif dept_name == 'StepDown':
                 if random.random() < 0.5: duration = max(1, 24 - (self.env.now % 24))
            
            dept.apply_event_effect(event_type, duration)

    def hourly_staff_manager(self):
        """Updates staff levels based on schedule and calculates costs."""
        total_regular_staff = sum(INITIAL_STAFF.values()) # 61
        
        for hour in range(self.duration):
            # 1. Determine Target Staffing
            current_targets = {}
            if self.staffing_schedule and hour in self.staffing_schedule:
                current_targets = self.staffing_schedule[hour]
            else:
                # Default: Initial or Previous? Default to Initial to be safe/consistent
                current_targets = INITIAL_STAFF # Or self.initial_staff_counts
            
            # 2. Apply to Departments
            total_target_needed = 0
            for name, dept in self.departments.items():
                target = current_targets.get(name, INITIAL_STAFF[name])
                dept.set_staff_level(target)
                total_target_needed += target
            
            # 3. Calculate Temp Staff Costs
            temps_needed = max(0, total_target_needed - total_regular_staff)
            
            # Setup Cost (if increased)
            if temps_needed > self.last_hour_temps:
                new_hires = temps_needed - self.last_hour_temps
                self.total_staff_setup_cost += new_hires * 40 # Assuming 40 is hiring cost/setup?
                # "Temporary Extra staff... cost is 40... wait/setup"
                # "Extra Staff: 40" in Costs table.
                # Assuming 40 per hour AND 40 for setup logic?
                # "if the cost is 40 and they work for 2 hrs they are charged for the 1 hr wait/setup and 2 hrs they work with total cost = 120"
                # This implies 40 per hour, including setup hour.
                # So yes, 1*40 setup + 2*40 work = 120.
                
            # Hourly Work Cost
            self.total_staff_hourly_cost += temps_needed * 40
            
            self.last_hour_temps = temps_needed
            
            yield self.env.timeout(1.0)

    def calculate_total_cost(self):
        total = self.total_staff_setup_cost + self.total_staff_hourly_cost
        for name, dept in self.departments.items():
            total += dept.total_wait_cost
            total += dept.total_diversion_cost
            # dept.total_staff_cost is redundant if we calculate globally, 
            # but department might track its specific breakdown?
            # We used global calculation in hourly_staff_manager. 
            # dept.total_staff_cost was a placeholder in department.py.
            # We ignore it here.
            
        self.total_cost = total

if __name__ == "__main__":
    # Test Run
    sim = HospitalSimulation(duration_hours=24)
    cost = sim.run()
    print(f"Baseline Cost: {cost}")
