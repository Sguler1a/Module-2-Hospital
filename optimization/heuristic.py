from simulation.models import Hospital
from simulation.config import *

class RuleBasedOptimizer:
    def __init__(self, hospital: Hospital):
        self.hospital = hospital

    def get_action(self, hour_str):
        """
        Determine actions for the current hour based on the state.
        Returns: {DeptName: {hire: int, remove: int, move_to: {Dest: int}}}
        """
        actions = {}
        
        # Simple Greedy Heuristic
        # 1. ER Logic: Priority to avoid Diversions
        # Check if ER needs staff (High Queue or Ambulance risk)
        er = self.hospital.departments[DEPT_ER]
        er_action = {"hire": 0, "remove": 0, "move_to": {}}
        
        # Calculate stress
        # If queue > 5 or capacity reached, consider hiring/adding
        # We know ambulances arrive. If current capacity < current load, risk!
        # But hiring takes 1 hour. So we must predict? 
        # Or just react: if queue is growing, hire.
        
        if er.waiting_queue > 5:
            er_action["hire"] = 2
        elif er.waiting_queue > 20: 
            er_action["hire"] = 5
        
        # Check idle staff (oversupply)
        total_pats = er.waiting_queue + len(er.in_treatment)
        staff = er.get_total_staff()
        if staff > total_pats + 5:
             # Remove extra first
            if er.extra_staff > 0:
                er_action["remove"] = 1
            # Or move scheduled? (Not implemented in this simple heuristic yet)
            
        actions[DEPT_ER] = er_action
        
        # 2. General Logic for others
        for dept_name in [DEPT_SURGERY, DEPT_ICU, DEPT_STEP_DOWN]:
            dept = self.hospital.departments[dept_name]
            act = {"hire": 0, "remove": 0, "move_to": {}}
            
            # Simple thresholding
            if dept.waiting_queue > 5:
                act["hire"] = 1
            elif dept.waiting_queue > 10:
                act["hire"] = 2
                
            if dept.get_total_staff() > (dept.waiting_queue + len(dept.in_treatment)) + 3:
                if dept.extra_staff > 0:
                    act["remove"] = 1
            
            actions[dept_name] = act
            
        return actions
