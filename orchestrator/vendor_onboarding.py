"""
Vendor Onboarding Workflow using LangGraph.
States: DRAFT → CENTRAL_PENDING → DEPT_REVIEW → APPROVED/REJECTED
"""

from langgraph.graph import StateGraph, END
from typing import Literal
from datetime import datetime

from orchestrator.states import VendorOnboardingState
from orchestrator.state_manager import (
    sync_vendor_state_to_db,
    log_state_transition,
    save_approval
)


######################################### 
# Node Functions (Processing Logic)
#########################################

def validate_submission(state: VendorOnboardingState) -> VendorOnboardingState:
    """
    Validate vendor submission data.
    Rule-based checks for required fields.
    """
    vendor_data = state['vendor_data']
    
    # Required fields validation
    required_fields = ['name', 'category', 'contact_email', 'tax_id']
    missing = [f for f in required_fields if f not in vendor_data or not vendor_data[f]]
    
    if missing:
        new_state = {
            **state,
            'current_status': 'REJECTED',
            'error': f'Missing required fields: {", ".join(missing)}',
            'updated_at': datetime.now()
        }
        
        # Log transition
        log_state_transition(
            state['request_id'],
            from_status=state['current_status'],
            to_status='REJECTED',
            reason=f'Validation failed: {new_state["error"]}'
        )
        
        # Sync to DB
        sync_vendor_state_to_db(new_state)
        
        return new_state
    
    # Validation passed - move to central review
    new_state = {
        **state,
        'current_status': 'CENTRAL_PENDING',
        'updated_at': datetime.now(),
        'error': None
    }
    
    # Log transition
    log_state_transition(
        state['request_id'],
        from_status=state['current_status'],
        to_status='CENTRAL_PENDING'
    )
    
    # Sync to DB
    sync_vendor_state_to_db(new_state)
    
    return new_state


def central_manager_review(state: VendorOnboardingState) -> VendorOnboardingState:
    """
    Wait for central manager approval.
    This is a human-in-the-loop node - execution pauses here.
    Human resumes workflow by providing approval data.
    """
    # In Phase 2, this is where Vendor Risk Agent would be called
    # For now, just return state (checkpoint handles waiting)
    
    return state


def route_to_parallel_approvals(state: VendorOnboardingState) -> VendorOnboardingState:
    """
    Prepare state for parallel department reviews.
    Initialize approval tracking for Finance, Legal, Business.
    """
    new_state = {
        **state,
        'current_status': 'DEPT_REVIEW',
        'dept_approvals': {
            'finance': None,
            'legal': None,
            'business': None
        },
        'updated_at': datetime.now()
    }
    
    # Log transition
    log_state_transition(
        state['request_id'],
        from_status=state['current_status'],
        to_status='DEPT_REVIEW'
    )
    
    # Sync to DB
    sync_vendor_state_to_db(new_state)
    
    return new_state


def aggregate_dept_approvals(state: VendorOnboardingState) -> VendorOnboardingState:
    """
    Collect parallel approval results and make final decision.
    All departments must approve for vendor to be approved.
    """
    approvals = state['dept_approvals']

    # Check if all departments have responded
    if any(v is None for v in approvals.values()):
        # Still waiting for approvals
        return state
    
    # All departments responded - check if all approved
    all_approved = all(
        dept['approved'] for dept in approvals.values() if dept is not None
    )
    
    final_status = 'APPROVED' if all_approved else 'REJECTED'
    
    new_state = {
        **state,
        'current_status': final_status,
        'updated_at': datetime.now()
    }
    
    # Log transition
    log_state_transition(
        state['request_id'],
        from_status=state['current_status'],
        to_status=final_status,
        reason='All department approvals collected'
    )
    
    # Sync to DB
    sync_vendor_state_to_db(new_state)
    
    return new_state


######################################### 
# Conditional Routing (Rule Logic)
#########################################

def should_proceed_after_validation(
    state: VendorOnboardingState
) -> Literal["proceed", "reject"]:
    """Route after validation check"""
    if state['current_status'] == 'REJECTED':
        return "reject"
    return "proceed"


def should_proceed_after_central_review(
    state: VendorOnboardingState
) -> Literal["approved", "rejected"]:
    """Route after central manager review"""
    approval = state.get('central_manager_approval')
    
    # If no approval data yet, this shouldn't be called
    # (checkpoint will pause execution)
    if not approval:
        return "rejected"
    
    if approval.get('approved'):
        return "approved"
    return "rejected"


def check_all_dept_approvals_complete(
    state: VendorOnboardingState
) -> Literal["complete", "waiting"]:
    """Check if all departments have responded"""
    approvals = state['dept_approvals']
    
    if all(v is not None for v in approvals.values()):
        return "complete"
    return "waiting"


######################################### 
# Build the Graph
#########################################

def create_vendor_onboarding_workflow() -> StateGraph:
    """
    Create the vendor onboarding LangGraph workflow.
    
    Flow:
    1. validate → Check required fields
    2. central_review → Wait for central manager (human-in-the-loop)
    3. parallel_routing → Fan out to 3 departments
    4. aggregate → Collect results and finalize
    """
    
    workflow = StateGraph(VendorOnboardingState)
    
    # Add nodes
    workflow.add_node("validate", validate_submission)
    workflow.add_node("central_review", central_manager_review)
    workflow.add_node("parallel_routing", route_to_parallel_approvals)
    workflow.add_node("aggregate", aggregate_dept_approvals)
    
    # Set entry point
    workflow.set_entry_point("validate")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "validate",
        should_proceed_after_validation,
        {
            "proceed": "central_review",
            "reject": END
        }
    )
    
    workflow.add_conditional_edges(
        "central_review",
        should_proceed_after_central_review,
        {
            "approved": "parallel_routing",
            "rejected": END
        }
    )
    
    workflow.add_edge("parallel_routing", "aggregate")
    
    workflow.add_conditional_edges(
        "aggregate",
        check_all_dept_approvals_complete,
        {
            "complete": END,
            "waiting": "aggregate"  # Loop until all approvals received
        }
    )
    
    return workflow