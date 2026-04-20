import pytest
from pathlib import Path
from datetime import datetime
from dot_swarm.models import SwarmPaths, WorkItem, ItemState, Claim
from dot_swarm.operations import (
    read_queue, write_queue, claim_item, done_item, read_claims,
    resolve_claims
)

@pytest.fixture
def swarm_paths(tmp_path):
    swarm = tmp_path / ".swarm"
    swarm.mkdir()
    paths = SwarmPaths.from_swarm_dir(swarm)
    return paths

def test_claim_creates_file(swarm_paths):
    # Setup initial queue
    item = WorkItem(id="SWC-001", description="Test item", state=ItemState.OPEN)
    write_queue(swarm_paths, [], [item], [])
    
    # Claim it
    claim_item(swarm_paths, "SWC-001", "agent-1")
    
    # Verify claim file exists
    claims_dir = swarm_paths.claims
    assert claims_dir.is_dir()
    claim_files = list(claims_dir.glob("SWC-001_agent-1_*.json"))
    assert len(claim_files) == 1
    
    # Verify read_queue resolves it to CLAIMED
    active, pending, done = read_queue(swarm_paths)
    assert len(active) == 1
    assert active[0].id == "SWC-001"
    assert active[0].state == ItemState.CLAIMED
    assert active[0].claimed_by == "agent-1"

def test_done_clears_claims(swarm_paths):
    # Setup initial queue with an item
    item = WorkItem(id="SWC-001", description="Test item", state=ItemState.OPEN)
    write_queue(swarm_paths, [], [item], [])
    
    # Claim it
    claim_item(swarm_paths, "SWC-001", "agent-1")
    assert len(list(swarm_paths.claims.glob("SWC-001_*.json"))) == 1
    
    # Mark as done
    done_item(swarm_paths, "SWC-001", "agent-1")
    
    # Verify claim file is gone
    assert len(list(swarm_paths.claims.glob("SWC-001_*.json"))) == 0
    
    # Verify queue.md has it as DONE
    active, pending, done = read_queue(swarm_paths)
    assert len(done) == 1
    assert done[0].id == "SWC-001"
    assert done[0].state == ItemState.DONE

def test_concurrent_claims_newest_wins(swarm_paths):
    # Setup initial queue
    item = WorkItem(id="SWC-001", description="Test item", state=ItemState.OPEN)
    write_queue(swarm_paths, [], [item], [])
    
    # Multiple claims with different timestamps (simulating async git merges)
    from dot_swarm.operations import write_claim
    
    c1 = Claim(item_id="SWC-001", agent_id="agent-1", state=ItemState.CLAIMED, 
               timestamp=datetime(2026, 4, 20, 10, 0))
    c2 = Claim(item_id="SWC-001", agent_id="agent-2", state=ItemState.CLAIMED, 
               timestamp=datetime(2026, 4, 20, 11, 0)) # Newer
    
    write_claim(swarm_paths, c1)
    write_claim(swarm_paths, c2)
    
    # Verify newest wins
    active, pending, done = read_queue(swarm_paths)
    assert active[0].claimed_by == "agent-2"
    assert active[0].claimed_at == datetime(2026, 4, 20, 11, 0)
