
import time
import asyncio

# Mock data structures
class Group:
    def __init__(self, id, name, cooldown_minutes, batch_size):
        self.id = id
        self.name = name
        self.cooldown_minutes = cooldown_minutes
        self.batch_size = batch_size
        self.messages_sent_today = 0
        self.max_messages_per_day = 100
        self.start_hour = 0
        self.end_hour = 24

class MockDB:
    def __init__(self, groups):
        self.groups = groups
    def commit(self): pass
    def close(self): pass

async def simulate_automation_loop(groups_from_db):
    group_cooldowns = {}
    iteration = 0
    
    # We'll run for 3 iterations to see the cooldown in action
    while iteration < 3:
        print(f"\n--- Iteration {iteration} ---")
        # Step 1: Simulate the query (Distinct)
        seen_ids = set()
        active_groups = []
        for g in groups_from_db:
            if g.id not in seen_ids:
                active_groups.append(g)
                seen_ids.add(g.id)
        
        print(f"Active Groups to process: {[g.name for g in active_groups]}")
        
        for group in active_groups:
            # Step 2: Check Cooldown
            if group.id in group_cooldowns and time.time() < group_cooldowns[group.id]:
                remaining = int(group_cooldowns[group.id] - time.time())
                print(f"⏳ Group {group.name} is on cooldown. Remaining: {remaining}s.")
                continue
            
            # Step 3: Process Batch
            print(f"📦 Processing Group: {group.name} | Batch Size: {group.batch_size}")
            for i in range(group.batch_size):
                print(f"  📩 Sending message {i+1}/{group.batch_size} for {group.name}")
                group.messages_sent_today += 1
            
            # Step 4: Set Cooldown
            cooldown_sec = group.cooldown_minutes * 60
            group_cooldowns[group.id] = time.time() + cooldown_sec
            print(f"🛌 Group {group.name} batch finished. Cooldown set for {group.cooldown_minutes}m.")
        
        iteration += 1
        if iteration < 3:
            print("🕒 Task loop sleeping (simulated 2s)...")
            await asyncio.sleep(2)

async def main():
    # Setup: Group A has 2 instances (simulating duplicate join)
    g1 = Group(1, "Group Alpha", cooldown_minutes=1, batch_size=2)
    g1_dup = Group(1, "Group Alpha", cooldown_minutes=1, batch_size=2)
    
    # In the actual code, distinct() handles this. Here we simulate the list.
    all_rows = [g1, g1_dup]
    
    print("Testing logic with duplicate group entries and 1-minute cooldown...")
    await simulate_automation_loop(all_rows)

if __name__ == "__main__":
    asyncio.run(main())
