
import random
import simpy
from .config import COSTS, CAPACITY, INITIAL_STAFF

class Department:
    def __init__(self, env, name, initial_patients=0, initial_staff=0):
        self.env = env
        self.name = name
        
        # 1. Resources
        
        # Staff: Modeled as a large resource where we block (MAX - current) slots
        # Max reasonable staff = 100 per dept?
        self.max_staff_possible = 200
        self.staff_limit = initial_staff if initial_staff > 0 else INITIAL_STAFF.get(name, 0)
        self.staff = simpy.PriorityResource(env, capacity=self.max_staff_possible)
        
        # Block unused capacity immediately
        # We need to block (200 - initial) slots
        self.blockers = []
        self.excess_capacity = self.max_staff_possible - self.staff_limit
        if self.excess_capacity > 0:
            for _ in range(self.excess_capacity):
                self.env.process(self._create_blocker())
        
        # Beds: Fixed capacity usually? Or can vary?
        # Prompt: "Temporary Extra staff...". Beds seem fixed.
        # "Set number of rooms/beds... 30 for ER".
        # Assume Beds are fixed for now.
        self.capacity_limit = CAPACITY[name]
        self.beds = simpy.Resource(env, capacity=self.capacity_limit)
        
        # 2. State
        self.queue = [] 
        self.active_patients = [] 
        
        # 3. Random Event States
        self.closed_rooms = 0 
        self.staff_reduction = 0 # Events reduce the 'visible' limit
        self.event_blockers = []

        # 4. Metrics
        self.total_wait_cost = 0
        self.total_diversion_cost = 0 
        self.total_staff_cost = 0 
        self.temp_staff_count = 0 # Tracks temps *paid for* this hour (handled by simulation manager)

    def _create_blocker(self):
        """Creates a high-priority request to block a staff slot."""
        # Priority -1 is higher than default 0? SimPy PriorityResource: lower is higher priority?
        # Default is 0? documentation says "smaller number = higher priority" usually?
        # SimPy default priority is 0. simple numbers.
        # Let's use priority -10 to ensure we block it before patients (prio 0).
        with self.staff.request(priority=-10) as req:
            yield req
            # Hold indefinitely until cancelled?
            # We need a way to release this specific request if we increase capacity.
            # SimPy request context manager releases on exit.
            # We need to KEEP it held.
            # So we yield an event that we can trigger later?
            event = self.env.event()
            self.blockers.append(event)
            yield event

    def set_staff_level(self, new_level):
        """
        Adjusts the effective staff limit to `new_level`.
        Current real usage = (200 - len(blockers)).
        We want (200 - len(blockers)) == new_level.
        => len(blockers) should be 200 - new_level.
        """
        target_blockers = self.max_staff_possible - new_level
        current_blockers = len(self.blockers)
        
        if target_blockers > current_blockers:
            # Need MORE blockers (Reduce Staff)
            diff = target_blockers - current_blockers
            for _ in range(diff):
                self.env.process(self._create_blocker())
                
        elif target_blockers < current_blockers:
            # Need FEWER blockers (Increase Staff)
            diff = current_blockers - target_blockers
            for _ in range(diff):
                if self.blockers:
                    event = self.blockers.pop()
                    event.succeed() # Release the lock

        self.staff_limit = new_level

    def can_accept_patient(self, hour):
        if self.name == 'StepDown':
            if hour >= 23 or hour < 6:
                return False
        return True

    def get_available_resources(self):
        # Effective Capacity = Capacity - Event_Closed
        # Effective Staff = Staff_Limit - Event_Reduction
        # Note: Event reduction should ALSO be modeled as blockers?
        # Or just checking logic?
        # "Wait penalty" checks this.
        # "1 Staff has to leave". logic: `apply_event_effect` should use blockers too.
        
        real_capacity = max(0, self.capacity_limit - self.closed_rooms)
        real_staff = max(0, self.staff_limit - self.staff_reduction)
        
        # Available = Real - Currently_Used
        # Currently_Used = (Max - Blockers) - Free?
        # No, self.staff.count includes Blockers.
        # Used_by_Patients = self.staff.count - len(self.blockers) - len(self.event_blockers)
        # Free = Real_Staff - Used_by_Patients?
        # Simpler: free = self.staff.capacity - self.staff.count?
        # No, capacity is 200.
        # free_slots = 200 - count.
        # But some are blocked.
        # We assume Blockers are counted in `count`.
        # So `free_slots` is truly free.
        
        free_beds = self.capacity_limit - self.closed_rooms - self.beds.count
        
        # Identify how many blockers are active
        # Wait, if we added event blockers, they are in `count`.
        # So `self.staff.count` measures (Patients + Blockers + EventBlockers).
        # We want to know if `Patients` can fit.
        # If `count < 200`, there is a slot.
        # But we only want to allow `count < 200` IF `count < (200 - Unused_Blockers)`?
        # No, we set the blockers specifically to define the limit.
        # So `free_staff` = `200 - self.staff.count`.
        # If we blocked correctly, `200 - count` is exactly the available space for patients.
        
        free_staff = self.max_staff_possible - self.staff.count
        
        return free_beds, free_staff

    def log_patient_entry(self, patient):
        self.queue.append(patient)
        patient.status = f'Waiting in {self.name}'
        patient.wait_start_time = self.env.now

    def admit_patient(self, patient):
        if patient in self.queue:
            self.queue.remove(patient)
        self.active_patients.append(patient)
        patient.status = f'In Treatment {self.name}'
        
        wait_duration = self.env.now - patient.wait_start_time
        patient.total_wait_time += wait_duration
        cost_per_hour = COSTS[self.name]['Wait']
        self.total_wait_cost += wait_duration * cost_per_hour

    def discharge_patient(self, patient):
        if patient in self.active_patients:
            self.active_patients.remove(patient)

    def update_staff_cost(self):
        # Staff cost logic is handled by Simulation manager (which knows about hiring temps)
        # But we can store it here too.
        # `simulation.py` handles the hiring calculation.
        pass

    def apply_event_effect(self, effect_type, duration_hours):
        if effect_type == 'staff_leave':
            # Block a staff slot for X hours
            self.env.process(self._create_event_blocker(duration_hours))
        elif effect_type == 'room_close':
            self.closed_rooms += 1
            self.env.process(self._recover_room(duration_hours))

    def _create_event_blocker(self, duration):
        with self.staff.request(priority=-20) as req: # Higher prio than normal blockers?
            yield req
            self.staff_reduction += 1
            yield self.env.timeout(duration)
            self.staff_reduction -= 1

    def _recover_room(self, duration):
        yield self.env.timeout(duration)
        self.closed_rooms = max(0, self.closed_rooms - 1)
