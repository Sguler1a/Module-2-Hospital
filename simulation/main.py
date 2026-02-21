
from .hospital import HospitalSimulation
from .optimizer import StaffingOptimizer
import time

def main():
    print("=== Hospital Simulation & Optimization ===")
    
    # 1. Run Baseline
    print("\nRunning Baseline Simulation (Initial Staffing)...")
    baseline_sim = HospitalSimulation(duration_hours=24)
    baseline_cost = baseline_sim.run()
    print(f"Baseline Total Cost: ${baseline_cost:,.2f}")
    
    # 2. Run Optimization
    print("\nRunning Optimization (Genetic Algorithm)...")
    start_time = time.time()
    optimizer = StaffingOptimizer()
    best_schedule, min_cost = optimizer.run()
    duration = time.time() - start_time
    
    print(f"\nOptimization Complete in {duration:.1f} seconds")
    print(f"Optimized Total Cost: ${min_cost:,.2f}")
    print(f"Savings: ${baseline_cost - min_cost:,.2f} ({(baseline_cost - min_cost)/baseline_cost*100:.1f}%)")
    
    # 3. Validation Run
    print("\nValidating Best Schedule...")
    val_sim = HospitalSimulation(duration_hours=24, staffing_schedule=best_schedule)
    val_cost = val_sim.run()
    print(f"Validation Run Cost: ${val_cost:,.2f}")

    # 4. detailed Output
    print("\n=== Optimized Staffing Schedule ===")
    print(f"{'Hour':<5} | {'ER':<5} {'Surg':<5} {'CC':<5} {'SD':<5} | {'Total':<5} | {'Temps':<5}")
    print("-" * 50)
    
    total_regulars = sum(val_sim.initial_staff_counts.values())
    
    for h in range(24):
        sched = best_schedule[h]
        er = sched.get('ER', 0)
        surg = sched.get('Surgery', 0)
        cc = sched.get('CriticalCare', 0)
        sd = sched.get('StepDown', 0)
        
        total_needed = er + surg + cc + sd
        temps = max(0, total_needed - total_regulars)
        
        print(f"{h:<5} | {er:<5} {surg:<5} {cc:<5} {sd:<5} | {total_needed:<5} | {temps:<5}")

if __name__ == "__main__":
    main()
