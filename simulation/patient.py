
class Patient:
    def __init__(self, p_id, arrival_time):
        self.id = p_id
        self.arrival_time = arrival_time
        self.status = 'Arrived' # Arrived, Waiting, Treating, Discharged
        self.history = []
        self.wait_start_time = 0
        self.total_wait_time = 0

    def log(self, message):
        self.history.append(message)
    
    def __repr__(self):
        return f"Patient({self.id}, {self.status})"
