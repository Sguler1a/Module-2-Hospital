
import random
import copy
from .config import INITIAL_STAFF
from .hospital import HospitalSimulation
import numpy as np

# Genetic Algorithm Parameters defaults
# These can now be passed to the StaffingOptimizer
POPULATION_SIZE = 5
GENERATIONS = 100
MUTATION_RATE = 0.1
ELITISM = 2

class StaffingOptimizer:
    def __init__(self, population_size=POPULATION_SIZE, generations=GENERATIONS, mutation_rate=MUTATION_RATE, elitism=ELITISM):
        self.depts = ['ER', 'Surgery', 'CriticalCare', 'StepDown']
        self.hours = 24
        self.best_solution = None
        self.best_cost = float('inf')
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elitism = elitism

    def generate_random_schedule(self):
        """Generates a random staffing schedule."""
        schedule = {}
        for h in range(self.hours):
            schedule[h] = {}
            for dept in self.depts:
                # Random variation around initial staffing
                base = INITIAL_STAFF[dept]
                variation = random.randint(-2, 4) 
                schedule[h][dept] = max(1, base + variation)
        return schedule
    def _get_schedule_hash(self, schedule):
        """Converts schedule to a hashable tuple to check for uniqueness."""
        return tuple(tuple(sorted(schedule[h].items())) for h in range(self.hours))

    def evaluate(self, schedule, iterations=5):
        """Runs simulation multiple times and returns average cost."""
        costs = []
        # Run iterations to average out random noise
        for _ in range(iterations):
            sim = HospitalSimulation(duration_hours=24, staffing_schedule=schedule)
            sim.run()
            costs.append(sim.total_cost)
        return sum(costs) / len(costs)

    def crossover(self, parent1, parent2):
        """Uniform Crossover."""
        child = {}
        for h in range(self.hours):
            child[h] = {}
            for dept in self.depts:
                if random.random() < 0.5:
                    child[h][dept] = parent1[h][dept]
                else:
                    child[h][dept] = parent2[h][dept]
        return child

    def mutate(self, schedule):
        """Randomly changes staffing levels."""
        mutated = copy.deepcopy(schedule)
        for h in range(self.hours):
            if random.random() < self.mutation_rate:
                dept = random.choice(self.depts)
                change = random.choice([-1, 1])
                mutated[h][dept] = max(1, mutated[h][dept] + change)
        return mutated

    def run(self):
        print("Starting Optimization...")
        # 1. Initialize Population
        population = [self.generate_random_schedule() for _ in range(self.population_size)]
        # Add Baseline
        baseline = {h: INITIAL_STAFF.copy() for h in range(24)}
        population[0] = baseline
        
        # Prepare Baseline for comparison
        baseline_schedule = {h: INITIAL_STAFF.copy() for h in range(24)}
        
        # Maintain top unique contenders across all generations
        top_contenders = [] # List of tuples: (cost, schedule, hash)
        
        for gen in range(self.generations):
            # 2. Evaluate
            scored_pop = []
            for solution in population:
                cost = self.evaluate(solution)
                scored_pop.append((cost, solution))
            
            # Evaluate Baseline for this generation's conditions
            current_baseline_cost = self.evaluate(baseline_schedule)
            
            scored_pop.sort(key=lambda x: x[0])
            
            # Update Top Contenders list with unique schedules
            for cost, schedule in scored_pop:
                sched_hash = self._get_schedule_hash(schedule)
                # Check if it's already in top contenders
                if not any(tc[2] == sched_hash for tc in top_contenders):
                    top_contenders.append((cost, schedule, sched_hash))
            
            # Keep only the top 5 unique contenders
            top_contenders.sort(key=lambda x: x[0])
            top_contenders = top_contenders[:5]
            
            # Update Best cost for print tracking (lowest seen during 5-eval phase)
            if top_contenders[0][0] < self.best_cost:
                self.best_cost = top_contenders[0][0]
                print(f"Generation {gen}: New Best Cost (5-eval) = {self.best_cost:,.2f} | Baseline Cost = {current_baseline_cost:,.2f}")
            else:
                 print(f"Generation {gen}: Best Cost (5-eval) = {self.best_cost:,.2f} | Baseline Cost = {current_baseline_cost:,.2f}")

            # 3. Selection (Top 50% of the current generation)
            survivors = scored_pop[:self.population_size//2]
            
            # 4. Next Generation
            new_pop = [s[1] for s in survivors[:self.elitism]] # Elitism
            
            while len(new_pop) < self.population_size:
                p1 = random.choice(survivors)[1]
                p2 = random.choice(survivors)[1]
                child = self.crossover(p1, p2)
                child = self.mutate(child)
                new_pop.append(child)
            
            population = new_pop
            
        # --- Final Validation Phase ---
        print("\n--- Starting Final Validation Phase ---")
        print(f"Validating top {len(top_contenders)} unique schedules across 100 iterations...")
        
        validated_results = []
        for i, (old_cost, schedule, _) in enumerate(top_contenders):
            val_cost = self.evaluate(schedule, iterations=100)
            validated_results.append((val_cost, schedule))
            print(f"Contender {i+1}: 5-eval Cost = {old_cost:,.2f} -> 100-eval Validation Cost = {val_cost:,.2f}")
            
        # Re-evaluate baseline for fair comparison
        validated_baseline_cost = self.evaluate(baseline_schedule, iterations=100)
        print(f"Baseline 100-eval Validation Cost = {validated_baseline_cost:,.2f}")
        
        # Sort by validation cost
        validated_results.sort(key=lambda x: x[0])
        
        self.best_cost = validated_results[0][0]
        self.best_solution = validated_results[0][1]
        
        print(f"\nValidation Complete. True Best Cost: {self.best_cost:,.2f}")
            
        return self.best_solution, self.best_cost

if __name__ == "__main__":
    opt = StaffingOptimizer()
    best_schedule, min_cost = opt.run()
    
    print("\nOptimization Complete")
    print(f"Minimum Cost: {min_cost}")
    # print("Best Schedule:", best_schedule)
