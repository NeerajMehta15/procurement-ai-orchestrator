# Phase 1 Implementation: Foundation & Vendor Onboarding Workflow

**Project:** Procurement AI Orchestrator (Hybrid Architecture)   
**Status:** ✅ Complete  
**Author:** Neeraj Mehta  
**Date:** January 2026

---

## Executive Summary
Phase 1 establishes the foundational architecture for the procurement orchestration system. We built a rule-based vendor onboarding workflow using LangGraph with PostgreSQL persistence, demonstrating the hybrid approach (rules-first, AI-selective) outlined in the master PRD.

**Key Achievement:** End-to-end workflow from vendor submission → validation → human approvals → database persistence, with full state management and audit trails.

---

## Problem Statement

### Current Manual Process
- Vendor onboarding takes 6+ days with sequential approvals
- 80% of time spent on coordination (email threads, status tracking)
- Fragmented decision context across teams
- No structured audit trail
- Manual routing errors (~12% of cases)

### Phase 1 Solution
Automated workflow orchestration that:
- Validates vendor submissions with rule-based logic
- Routes approvals to correct stakeholders automatically
- Pauses for human decision-making (human-in-the-loop)
- Persists complete state for resumption across sessions
- Logs all state transitions for compliance

**Scope:** Vendor onboarding workflow only (5 other workflows deferred to future phases)

---

## Architecture Decisions

### Decision 1: LangGraph vs AWS Step Functions

**Chosen:** LangGraph  

**Rationale:**
1. **AI Integration:** Phase 2 requires tight integration with Claude API for vendor risk assessment. LangGraph's native tool calling makes AI agents first-class citizens in the workflow, whereas Step Functions would require separate Lambda functions for each AI call.

2. **Local Development:** LangGraph workflows run locally with instant feedback loops. Step Functions require AWS deployment for every change, slowing iteration during development.

3. **Portfolio Value:** Demonstrating LangGraph expertise is highly valued in senior AI/ML engineering roles. Building custom orchestration shows deeper understanding of state machines and graph theory vs. configuring AWS services.

4. **Cost Control:** LangGraph execution cost = compute time only. Step Functions charge per state transition, which adds up with complex workflows.

**Trade-offs Accepted:**
- No out-of-box visual workflow monitoring (AWS console provides this for Step Functions)
- More infrastructure code to write (state persistence, retry logic)
- Less "enterprise-proven" than Step Functions

---

### Decision 2: Hybrid Database Schema

**Chosen:** Normalized core entities (vendors, skus, purchase_orders) + JSONB for workflow metadata  

**Rationale:**
1. **Core Entity Queryability:** Need to efficiently query "all approved vendors" or "vendors with risk score > 7". Normalized tables enable indexed lookups and foreign key enforcement.

2. **Workflow Flexibility:** Each workflow has unique metadata (vendor onboarding tracks parallel approvals; PO creation tracks approval levels L1/L2/L3). JSONB in `workflow_requests.metadata` provides schema flexibility without migrations.

3. **Dependency Validation:** Rule-based checks like "SKU creation requires approved vendor" are simple SQL queries: `WHERE vendor_id IN (SELECT id FROM vendors WHERE status='APPROVED')`.

**Schema Structure:**
```
Core Entities (12 tables):
├── vendors, skus, prices, purchase_orders, grns, invoices
├── workflow_requests (links workflows to entities)
├── workflow_state_transitions (audit trail)
├── approvals (human decisions)
├── dependencies (prerequisite tracking)
├── ai_agent_outputs (Phase 2)
└── users (authentication)
```

**Alternative Considered:** Pure JSONB (everything in `workflow_requests.data`)  
**Rejected Because:** Can't efficiently query vendor status or enforce foreign key constraints

---

### Decision 3: Two-Layer State Persistence

**Chosen:** LangGraph checkpoints (automatic) + Manual database sync  

**Rationale:**
1. **LangGraph Checkpoints:** Enable pause/resume functionality. When central manager needs to approve, workflow pauses and serializes entire state to `checkpoints` table. Days later, workflow resumes from exact checkpoint.

2. **Business Tables:** Store normalized, query-friendly data for reporting and business logic. LangGraph checkpoints are opaque blobs; our tables enable queries like "show all vendors pending finance approval."

**How They Work Together:**
```python
def validate_submission(state):
    # Business logic updates state
    new_state = {...}
    
    # Manual sync to business tables
    sync_vendor_state_to_db(new_state)
    
    # LangGraph automatically saves checkpoint
    return new_state
```

**Cost:** Extra code to maintain sync logic, but essential for production system

---

### Decision 4: State Schema Design

**Chosen:** Workflow-focused state (not database mirror)  

**Structure:**
```python
class VendorOnboardingState(TypedDict):
    # Identifiers
    request_id: str
    workflow_type: Literal["vendor_onboarding"]
    current_status: VendorStatus
    
    # Business data
    vendor_data: Dict[str, Any]
    
    # Workflow tracking
    central_manager_approval: Optional[Dict]
    dept_approvals: Dict[str, Optional[Dict]]
    
    # AI outputs (Phase 2)
    risk_assessment: Optional[Dict]
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    error: Optional[str]
```

**Rationale:**
- **Lean state:** Only data needed for routing decisions flows through graph
- **Approval tracking:** Dict structure enables checking "all departments responded?"
- **Error propagation:** Validation failures captured in `error` field
- **AI readiness:** `risk_assessment` placeholder for Phase 2 integration

**Alternative Considered:** Mirror database schema exactly  
**Rejected Because:** Creates tight coupling; database changes break workflow

---

## System Components

### 1. State Definitions (`orchestrator/states.py`)

**Purpose:** Type-safe definitions for data flowing through LangGraph workflows

**Contents:**
- `VendorOnboardingState` - Vendor approval workflow
- `SKUCreationState` - SKU validation workflow (Phase 2)
- `POCreationState` - Purchase order routing (Phase 4)
- `GRNVerificationState` - Goods receipt validation (Phase 4)
- `InvoiceProcessingState` - Invoice matching (Phase 4)

**Design Pattern:** TypedDict for static type checking
```python
VendorStatus = Literal["DRAFT", "CENTRAL_PENDING", "DEPT_REVIEW", "APPROVED", "REJECTED"]
```

**Key Insight:** Literal types enforce valid state transitions at compile time

---

### 2. State Manager (`orchestrator/state_manager.py`)

**Purpose:** Bridge between LangGraph in-memory state and PostgreSQL persistence

**Key Functions:**

**`sync_vendor_state_to_db(state)`**
- Upserts `vendors` table with current status
- Updates `workflow_requests` with metadata
- Idempotent (safe to call multiple times)

**`load_vendor_state_from_db(request_id)`**
- Reconstructs LangGraph state from database
- Useful for debugging or manual state inspection

**`log_state_transition(request_id, from_status, to_status)`**
- Writes to `workflow_state_transitions` for audit trail
- Called on every status change

**`save_approval(request_id, approval_type, decision, user_id)`**
- Persists human approval decisions
- Enables reporting on approval patterns

**Dependency Validators (Rule-Based):**
- `check_vendor_approved(vendor_id)` → `SELECT status FROM vendors WHERE id=?`
- `check_sku_approved(sku_id)` → Used in SKU → Price dependency validation
- `check_po_exists(po_id)` → Used in GRN verification

**Design Pattern:** Pure functions that take state, return updated state, no side effects except DB writes

---

### 3. Vendor Onboarding Workflow (`orchestrator/vendor_onboarding.py`)

**States:**
```
DRAFT → CENTRAL_PENDING → DEPT_REVIEW → APPROVED/REJECTED
```

**Nodes (Processing Units):**

1. **`validate_submission`**
   - Rule: Check required fields (name, category, contact_email, tax_id)
   - If missing → Status = REJECTED, error message set
   - If valid → Status = CENTRAL_PENDING
   - Syncs state to database

2. **`central_manager_review`**
   - Human-in-the-loop node
   - Workflow pauses here (via `interrupt_before=["central_review"]`)
   - Currently just returns state (Phase 2 will add AI risk assessment)
   - Human resumes by providing `central_manager_approval` data

3. **`route_to_parallel_approvals`**
   - Initializes `dept_approvals` dict: `{finance: None, legal: None, business: None}`
   - Status = DEPT_REVIEW
   - Phase 3 will refactor to use `Send()` for true parallel execution

4. **`aggregate_dept_approvals`**
   - Checks if all departments responded
   - If any `None` → Loop back (waiting)
   - If all responded → Check if all approved
   - Status = APPROVED (if unanimous) or REJECTED (if any reject)

**Conditional Routing Logic:**

**`should_proceed_after_validation`**
```python
if state['current_status'] == 'REJECTED':
    return "reject"  # Route to END
return "proceed"  # Route to central_review
```

**`should_proceed_after_central_review`**
```python
if state['central_manager_approval']['approved']:
    return "approved"  # Route to parallel approvals
return "rejected"  # Route to END
```

**`check_all_dept_approvals_complete`**
```python
if all(dept is not None for dept in state['dept_approvals'].values()):
    return "complete"  # Route to END
return "waiting"  # Loop back to aggregate node
```

**Graph Structure:**
```
validate
  ├─ reject → END
  └─ proceed → central_review
                  ├─ rejected → END
                  └─ approved → parallel_routing
                                   → aggregate
                                      ├─ waiting → aggregate (loop)
                                      └─ complete → END
```

**Key Design Decision:** Loops enabled via conditional edges pointing back to same node

---

### 4. Workflow Compilation (`orchestrator/workflow.py`)

**Purpose:** Compile LangGraph workflows with PostgreSQL checkpointing

**Setup:**
```python
checkpointer = PostgresSaver.from_conn_string(DB_URI)
checkpointer.setup()  # Creates: checkpoints, checkpoint_writes tables
```

**Compilation:**
```python
vendor_onboarding_app = vendor_onboarding_graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["central_review"]  # Pause for human input
)
```

**Workflow Registry:**
```python
WORKFLOWS = {
    "vendor_onboarding": vendor_onboarding_app,
    # Future: "sku_creation", "po_creation", etc.
}
```

**Helper Functions:**

**`execute_workflow(workflow_type, initial_state, thread_id)`**
- Starts workflow execution
- `thread_id` = unique identifier (typically `request_id`)
- Pauses at interrupt points

**`resume_workflow(workflow_type, thread_id, update_state)`**
- Resumes paused workflow
- Merges `update_state` (approval data) into checkpointed state
- Continues execution from pause point

**`get_workflow_state(workflow_type, thread_id)`**
- Retrieves current state from checkpoint
- Useful for status checks or debugging

**Critical Concept:** `thread_id` ties all checkpoint operations together. Same `thread_id` = same workflow execution instance.

---

## Data Flow: Vendor Onboarding

### End-to-End Flow

**1. User Submission**
```
User → Creates VendorOnboardingState with vendor_data
     → Calls execute_workflow(initial_state, thread_id=request_id)
```

**2. Validation Node**
```
LangGraph → Executes validate_submission(state)
          → Checks required fields
          → Updates status to CENTRAL_PENDING
          → Calls sync_vendor_state_to_db(state)
             ├─ INSERT INTO vendors (...)
             ├─ INSERT INTO workflow_requests (...)
             └─ INSERT INTO workflow_state_transitions (from=DRAFT, to=CENTRAL_PENDING)
          → LangGraph auto-saves checkpoint
          → Returns new_state
```

**3. Workflow Pause**
```
LangGraph → Reaches central_review node
          → Sees interrupt_before=["central_review"]
          → Saves checkpoint and exits
          → Execution paused
```

**4. Human Approval (Hours/Days Later)**
```
Central Manager → Reviews vendor in UI
                → Approves with comments
                → System calls resume_workflow(
                    thread_id=request_id,
                    update_state={central_manager_approval: {...}}
                  )
```

**5. Resume Execution**
```
LangGraph → Loads checkpoint from database
          → Merges approval data into state
          → Executes central_review node (now has approval data)
          → Conditional routing: approved=True → routes to parallel_routing
          → Executes parallel_routing node
             → Sets status = DEPT_REVIEW
             → Initializes dept_approvals dict
             → Calls sync_vendor_state_to_db(state)
          → Executes aggregate node
             → Checks dept_approvals: all None → returns "waiting"
             → Loops back to aggregate (paused state)
```

**6. Department Approvals**
```
Finance/Legal/Business → Each approves independently
                       → Each triggers resume_workflow with updated dept_approvals
                       → aggregate node checks completion
                       → When 3/3 approved → status = APPROVED
```

**7. Final State**
```
LangGraph → Status = APPROVED
          → Calls sync_vendor_state_to_db(state)
             ├─ UPDATE vendors SET status='APPROVED'
             ├─ UPDATE workflow_requests SET current_status='APPROVED'
             └─ INSERT INTO workflow_state_transitions (to=APPROVED)
          → Workflow reaches END node
          → Execution complete
```

---

## Database Tables: Before & After

### Before Workflow Execution

**`vendors`:** Empty  
**`workflow_requests`:** Empty  
**`workflow_state_transitions`:** Empty  
**`checkpoints`:** Empty  

### After Workflow Execution

**`vendors`:**
```sql
id                  | name                    | status   | risk_score
--------------------|-------------------------|----------|------------
abc-123-...         | TechVendor Solutions    | APPROVED | NULL (Phase 2)
```

**`workflow_requests`:**
```sql
id       | workflow_type        | entity_id   | current_status | metadata (JSONB)
---------|---------------------|-------------|----------------|------------------
abc-123  | vendor_onboarding   | abc-123     | APPROVED       | {central_manager_approval: {...}, dept_approvals: {...}}
```

**`workflow_state_transitions`:**
```sql
request_id | from_status      | to_status        | transitioned_at
-----------|------------------|------------------|------------------
abc-123    | NULL             | DRAFT            | 2026-01-29 10:00
abc-123    | DRAFT            | CENTRAL_PENDING  | 2026-01-29 10:00
abc-123    | CENTRAL_PENDING  | DEPT_REVIEW      | 2026-01-29 14:30
abc-123    | DEPT_REVIEW      | APPROVED         | 2026-01-30 09:15
```

**`checkpoints`:** (LangGraph internal)
```sql
thread_id | checkpoint (JSONB - serialized state)        | parent_checkpoint_id
----------|----------------------------------------------|----------------------
abc-123   | {request_id: "abc-123", status: "DRAFT"...}  | NULL
abc-123   | {request_id: "abc-123", status: "CENTRAL...} | checkpoint-001
abc-123   | {request_id: "abc-123", status: "APPROVED..} | checkpoint-002
```

---

## Testing Strategy

### Test Script: `scripts/test_vendor_workflow.py`

**Coverage:**
1. ✅ **Happy Path:** Valid vendor → all approvals → APPROVED
2. ✅ **Validation Failure:** Missing tax_id → REJECTED immediately
3. ✅ **Checkpoint Persistence:** Workflow pauses and resumes correctly
4. ✅ **State Retrieval:** `get_workflow_state()` returns accurate data
5. ✅ **Database Sync:** All tables updated correctly
6. ✅ **Audit Trail:** State transitions logged

**Test Flow:**
```
1. Submit vendor (DRAFT)
2. Execute workflow → validates → CENTRAL_PENDING (paused)
3. Retrieve state from checkpoint
4. Central manager approves
5. Resume workflow → DEPT_REVIEW
6. Finance approves (resume)
7. Legal approves (resume)
8. Business approves (resume)
9. Final status: APPROVED
10. Verify database persistence
```

**Test Validation:**
- Console output shows each step
- Supabase tables manually inspected
- Checkpoint table confirms state snapshots exist

**Test Results:** ✅ All tests passing (pending Supabase uptime)

---

## Challenges & Solutions

### Challenge 1: Understanding Two-Layer Persistence

**Problem:** Initially unclear why both LangGraph checkpoints and business tables were needed.

**Solution:** Realized they serve different purposes:
- Checkpoints = Workflow execution engine (pause/resume)
- Business tables = Query-friendly data for reports and business logic

**Learning:** Don't fight the framework - LangGraph needs checkpoints, accept and build on top.

---

### Challenge 2: State Sync Timing

**Problem:** When should state be synced to database? After every node? Only at state transitions?

**Solution:** Sync after every status change (via `log_state_transition` + `sync_vendor_state_to_db`). Ensures database always reflects current state even if workflow crashes.

**Trade-off:** Extra DB writes, but worth it for consistency.

---

### Challenge 3: Parallel Approvals Not Truly Parallel

**Problem:** Current implementation just checks a dict (`dept_approvals`), not actually executing in parallel.

**Solution (Phase 3):** Will refactor to use `Send()` for fan-out pattern:
```python
def route_to_parallel_approvals(state):
    return [
        Send("finance_node", state),
        Send("legal_node", state),
        Send("business_node", state)
    ]
```

**Current State:** Sequential dict updates work for Phase 1 demo; true parallelism deferred.

---

### Challenge 4: Type Safety vs Flexibility

**Problem:** TypedDict provides type hints but Python doesn't enforce at runtime.

**Solution:** Use Pydantic in Phase 2 for runtime validation:
```python
from pydantic import BaseModel

class VendorData(BaseModel):
    name: str
    tax_id: str
    # ... enforces types at runtime
```

**Decision:** TypedDict sufficient for Phase 1; Pydantic adds complexity.

---

## Key Learnings

### 1. LangGraph Mental Model

**Before:** Thought of LangGraph as "AI framework"  
**After:** It's a **state machine orchestrator** that happens to integrate well with AI

**Insight:** Nodes = processing functions, Edges = routing logic, State = data container. AI agents are just special nodes that call LLMs.

---

### 2. Checkpointing is Magical

**Before:** Worried about implementing pause/resume logic  
**After:** LangGraph handles it automatically with `checkpointer`

**How it works:**
1. Workflow reaches interrupt point → saves state to `checkpoints` table → exits
2. Resume called → loads state from `checkpoints` → continues from exact node
3. All state transitions preserved across sessions

**Limitation:** Checkpoints are opaque blobs (JSONB), can't query specific fields

---

### 3. Rule-Based Logic is Still King

**Before:** Assumed AI would handle most logic  
**After:** 80% of workflow is simple if-else rules

**Examples:**
- Amount-based routing: `if amount <= 150K → L1 else L2`
- Quantity validation: `if GRN_qty > PO_qty → REJECT`
- Dependency checks: `if vendor_status != APPROVED → BLOCK`

**Takeaway:** Use AI only where rules can't handle complexity (semantic analysis, fuzzy matching, document interpretation)

---

### 4. State Schema Design is Critical

**Before:** Started with database-mirroring state (too heavy)  
**After:** Workflow-focused state (lean, fast)

**Best Practice:** State should contain:
- ✅ Data needed for routing decisions
- ✅ Workflow metadata (approvals, errors)
- ❌ NOT all database fields
- ❌ NOT derived data (compute on-demand)

---

## Production Readiness Assessment

### What Works ✅
- Complete vendor onboarding workflow
- State persistence with full audit trail
- Human-in-the-loop pattern
- Validation error handling
- Database schema supports all 6 workflows

### What's Missing ⚠️
- No AI agents yet (Phase 2)
- Parallel approvals not truly parallel (Phase 3)
- No API layer (Phase 4) - currently script-based
- No authentication (mock user IDs)
- No retry logic for failed DB writes
- No monitoring/alerting
- No deployment scripts

### Technical Debt 📝
- `aggregate_dept_approvals` loops inefficiently (refactor with Send() in Phase 3)
- State sync logic duplicated across nodes (extract to decorator)
- No unit tests (only integration test script)
- Type validation only at compile time (add Pydantic runtime checks)

---

## Next Steps: Phase 2 (Weeks 3-4)

### Goal: Add AI Intelligence

**1. Build Vendor Risk Agent**
- File: `agents/vendor_intelligence/agent.py`
- Input: Vendor data (financials, category, history)
- Output: Risk score (1-10) + factors + recommendations
- Integration: Called in `central_manager_review` node

**2. Modify Vendor Onboarding Workflow**
```python
def central_manager_review(state):
    # NEW: Call AI agent
    risk_assessment = assess_vendor_risk(state['vendor_data'])
    
    return {
        **state,
        'risk_assessment': risk_assessment
    }
```

**3. Store AI Outputs**
- Populate `ai_agent_outputs` table
- Update `vendors.risk_score` JSONB field

**4. Test AI Integration**
- Verify risk assessment appears in workflow state
- Validate structured output parsing
- Test with edge cases (missing data, high-risk vendors)

**5. Build SKU Matching Agent (Stretch Goal)**
- Semantic duplicate detection
- Integrate into SKU Creation workflow

---

## Metrics & Success Criteria

### Phase 1 Success Criteria ✅

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Vendor workflow states implemented | 4 | 4 | ✅ |
| Database tables created | 12 | 12 | ✅ |
| Test requests processed | 10 | 2 (limited by Supabase downtime) | 🚧 |
| State transitions logged | 100% | 100% | ✅ |
| Checkpoint pause/resume works | Yes | Yes | ✅ |

### Phase 2 Target Metrics

| Metric | Target |
|--------|--------|
| AI agent accuracy | ≥ 95% |
| Risk assessment latency | < 5 seconds |
| False positive rate | < 5% |

---

## Conclusion

Phase 1 successfully established the foundational architecture for the procurement orchestration system. We validated the hybrid approach (rules + AI) by building a complete rule-based workflow with state management, database persistence, and human-in-the-loop patterns.

**Key Achievements:**
1. ✅ Production-grade database schema (12 tables)
2. ✅ LangGraph workflow with checkpointing
3. ✅ End-to-end vendor onboarding flow
4. ✅ Full audit trail and state transitions
5. ✅ Extensible architecture for 5 remaining workflows

**Architecture validated:** Rules-first approach works; AI integration points clearly identified.

**Next:** Phase 2 will add AI intelligence (Vendor Risk Agent) while maintaining the rule-based foundation.

---

## Appendix: File Structure
```
procurement-ai-orchestrator/
├── orchestrator/
│   ├── states.py                    # ✅ State type definitions
│   ├── state_manager.py             # ✅ DB sync functions
│   ├── vendor_onboarding.py         # ✅ Workflow graph
│   └── workflow.py                  # ✅ Compilation + checkpointing
├── database/
│   └── migrations/
│       └── 001_initial_schema.sql   # ✅ Database schema
├── scripts/
│   └── test_vendor_workflow.py      # ✅ End-to-end test
├── docs/
│   └── phase1-implementation.md     # ✅ This document
└── .env                             # ✅ DATABASE_URL configured
```

**Lines of Code:** ~800 (excluding comments)  
**Time Investment:** ~12 hours (learning + implementation)  
**Knowledge Gained:** LangGraph state machines, PostgreSQL checkpointing, hybrid persistence patterns

---

*Document Version: 1.0*  
*Last Updated: January 29, 2026*

Additional Document: Architecture Diagram
docs/architecture/phase1-architecture.md
markdown# Phase 1 Architecture: System Components & Data Flow

## High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        User Layer                                │
│  (Scripts / Future API)                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  workflow.py (Compilation & Execution)                    │  │
│  │  - execute_workflow()                                     │  │
│  │  - resume_workflow()                                      │  │
│  │  - get_workflow_state()                                   │  │
│  └────────────────┬─────────────────────────────────────────┘  │
│                   │                                              │
│                   ▼                                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  vendor_onboarding.py (LangGraph State Machine)          │  │
│  │                                                            │  │
│  │  validate → central_review → parallel_routing → aggregate │  │
│  │                                                            │  │
│  │  Conditional Routing (Rule-Based Logic)                   │  │
│  └────────────────┬─────────────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   State Management Layer                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  state_manager.py                                         │  │
│  │  - sync_vendor_state_to_db()                             │  │
│  │  - log_state_transition()                                │  │
│  │  - save_approval()                                       │  │
│  │  - check_vendor_approved() [Rule validators]            │  │
│  └────────────────┬─────────────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Data Persistence Layer                         │
│                                                                   │
│  ┌─────────────────────┐         ┌──────────────────────────┐  │
│  │  Business Tables    │         │  LangGraph Tables        │  │
│  │  (Supabase)         │         │  (Auto-created)          │  │
│  │                     │         │                          │  │
│  │  - vendors          │         │  - checkpoints           │  │
│  │  - workflow_requests│         │  - checkpoint_writes     │  │
│  │  - approvals        │         │                          │  │
│  │  - transitions      │         │                          │  │
│  │  - dependencies     │         │                          │  │
│  └─────────────────────┘         └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interactions

### Scenario: Vendor Submission Flow
```
1. User Script
   └─> execute_workflow(initial_state, thread_id)
       │
       ▼
2. workflow.py
   └─> vendor_onboarding_app.invoke(state, config)
       │
       ▼
3. LangGraph Engine
   └─> Executes node: validate_submission(state)
       │
       ▼
4. vendor_onboarding.py (validate node)
   ├─> Validates required fields (rule-based)
   ├─> Updates status: DRAFT → CENTRAL_PENDING
   └─> Calls: sync_vendor_state_to_db(state)
       │
       ▼
5. state_manager.py
   ├─> INSERT INTO vendors (...)
   ├─> INSERT INTO workflow_requests (...)
   └─> INSERT INTO workflow_state_transitions (...)
       │
       ▼
6. Supabase (Business Tables)
   └─> Data persisted
       │
       ▼
7. LangGraph Engine (Automatic)
   └─> INSERT INTO checkpoints (thread_id, state_blob)
       │
       ▼
8. LangGraph Checkpointer
   └─> State snapshot saved
       │
       ▼
9. vendor_onboarding.py
   └─> Reaches node: central_review
       └─> interrupt_before=["central_review"] triggered
           └─> Execution pauses, returns to user
```

### Scenario: Resume After Approval
```
1. User Script
   └─> resume_workflow(thread_id, approval_data)
       │
       ▼
2. workflow.py
   └─> Loads checkpoint from database
   └─> Merges approval_data into state
   └─> Invokes: vendor_onboarding_app.invoke(updated_state, config)
       │
       ▼
3. LangGraph Engine
   └─> Continues from central_review node
   └─> Conditional routing: approved=True
   └─> Executes node: parallel_routing(state)
       │
       ▼
4. vendor_onboarding.py (parallel_routing node)
   ├─> Updates status: CENTRAL_PENDING → DEPT_REVIEW
   ├─> Initializes dept_approvals: {finance: None, legal: None, business: None}
   └─> Calls: sync_vendor_state_to_db(state)
       │
       ▼
5. state_manager.py
   ├─> UPDATE vendors SET status='DEPT_REVIEW'
   └─> INSERT INTO workflow_state_transitions (...)
       │
       ▼
6. LangGraph continues to aggregate node
   └─> Checks dept_approvals completion
   └─> Returns "waiting" (loops back)
```

---

## State Flow Diagram
```
┌──────────────────────────────────────────────────────────────┐
│                  VendorOnboardingState                        │
├──────────────────────────────────────────────────────────────┤
│  request_id: "abc-123"                                        │
│  workflow_type: "vendor_onboarding"                           │
│  current_status: "DRAFT"  ─────────────────┐                 │
│  vendor_data: {name, tax_id, ...}          │                 │
│  central_manager_approval: None            │                 │
│  dept_approvals: {}                        │                 │
│  risk_assessment: None                     │                 │
│  created_at: 2026-01-29 10:00              │                 │
│  updated_at: 2026-01-29 10:00              │                 │
│  error: None                               │                 │
└──────────────────────────────────────────┬─┴─────────────────┘
                                           │
                        ┌──────────────────▼──────────────────┐
                        │   validate_submission node           │
                        │   - Checks required fields           │
                        │   - If invalid: status="REJECTED"    │
                        │   - If valid: status="CENTRAL_PENDING│
                        └──────────────────┬──────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────┐
│  current_status: "CENTRAL_PENDING"                            │
│  error: None                                                  │
└──────────────────────────────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼──────────────────┐
                        │   central_manager_review node        │
                        │   - Waits for approval (interrupt)   │
                        │   - Human provides approval data     │
                        └──────────────────┬──────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────┐
│  central_manager_approval: {approved: true, comments: "..."}  │
└──────────────────────────────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼──────────────────┐
                        │   parallel_routing node              │
                        │   - Initializes dept_approvals       │
                        │   - status="DEPT_REVIEW"             │
                        └──────────────────┬──────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────┐
│  current_status: "DEPT_REVIEW"                                │
│  dept_approvals: {finance: None, legal: None, business: None} │
└──────────────────────────────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼──────────────────┐
                        │   aggregate node                     │
                        │   - Checks if all responded          │
                        │   - Loops until 3/3 approvals        │
                        └──────────────────┬──────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────┐
│  dept_approvals: {                                            │
│    finance: {approved: true, ...},                            │
│    legal: {approved: true, ...},                              │
│    business: {approved: true, ...}                            │
│  }                                                             │
│  current_status: "APPROVED"                                   │
└────────────────────────────────────────────────────────────────┘
```

---
