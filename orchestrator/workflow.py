"""
LangGraph workflow compilation with PostgreSQL checkpointing.
Compiles all workflow graphs and makes them ready for execution.
"""

from langgraph.checkpoint.postgres import PostgresSaver
from orchestrator.vendor_onboarding import create_vendor_onboarding_workflow
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection for checkpointing
DB_URI = os.getenv("DATABASE_URL")

if not DB_URI:
    raise ValueError("DATABASE_URL environment variable not set")

# Initialize PostgreSQL checkpointer
# This creates necessary tables for LangGraph state persistence
checkpointer = PostgresSaver.from_conn_string(DB_URI)

# Setup checkpoint tables (run once)
try:
    checkpointer.setup()
    print("✓ LangGraph checkpoint tables initialized")
except Exception as e:
    print(f"Note: Checkpoint tables may already exist ({e})")


######################################### 
# Compile Workflows
#########################################

# Vendor Onboarding Workflow
vendor_onboarding_graph = create_vendor_onboarding_workflow()
vendor_onboarding_app = vendor_onboarding_graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["central_review"]  # Pause before central manager review
)

print("✓ Vendor onboarding workflow compiled")


######################################### 
# Workflow Registry (for dynamic access)
#########################################

WORKFLOWS = {
    "vendor_onboarding": vendor_onboarding_app,
    # "sku_creation": sku_creation_app,
    # "price_approval": price_approval_app,
    # "po_creation": po_creation_app,
    # "grn_verification": grn_verification_app,
    # "invoice_processing": invoice_processing_app,
}


def get_workflow(workflow_type: str):
    """Get compiled workflow by type"""
    if workflow_type not in WORKFLOWS:
        raise ValueError(f"Unknown workflow type: {workflow_type}")
    return WORKFLOWS[workflow_type]


######################################### 
# Helper: Execute Workflow
#########################################

def execute_workflow(workflow_type: str, initial_state: dict, thread_id: str):
    """
    Execute a workflow with checkpointing.
    
    Args:
        workflow_type: "vendor_onboarding", "sku_creation", etc.
        initial_state: Starting state dict
        thread_id: Unique identifier for this workflow execution (usually request_id)
    
    Returns:
        Final state after execution
    """
    app = get_workflow(workflow_type)
    
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Execute workflow
    result = app.invoke(initial_state, config)
    
    return result


def resume_workflow(workflow_type: str, thread_id: str, update_state: dict):
    """
    Resume a paused workflow (e.g., after human approval).
    
    Args:
        workflow_type: "vendor_onboarding", etc.
        thread_id: The thread_id used in initial execution
        update_state: State updates (e.g., approval data)
    
    Returns:
        Updated final state
    """
    app = get_workflow(workflow_type)
    
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Get current state from checkpoint
    current_state = app.get_state(config)
    
    # Merge updates
    updated_state = {**current_state.values, **update_state}
    
    # Resume execution
    result = app.invoke(updated_state, config)
    
    return result


def get_workflow_state(workflow_type: str, thread_id: str):
    """
    Get current state of a workflow execution.
    
    Args:
        workflow_type: "vendor_onboarding", etc.
        thread_id: The thread_id used in execution
    
    Returns:
        Current state dict
    """
    app = get_workflow(workflow_type)
    
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    state = app.get_state(config)
    
    return state.values if state else None