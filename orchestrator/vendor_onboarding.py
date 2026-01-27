from langgraph.graph import StateGraph, END
from orchestrator.states import VendorOnboardingState
from typing import Literal

# ============================================
# NODE FUNCTIONS (Your Processing Logic)
# ============================================

def validate_submission(state: VendorOnboardingState) -> VendorOnboardingState:
    """Validate vendor submission data"""
    vendor_data = state['vendor_data']
    
    # Rule-based validation
    required_fields = ['name', 'category', 'contact_email', 'tax_id']
    missing = [f for f in required_fields if f not in vendor_data]
    
    if missing:
        return {
            **state,
            'current_status': 'REJECTED',
            'error': f'Missing required fields: {missing}'
        }
    
    # Valid submission - move to central review
    return {
        **state,
        'current_status': 'CENTRAL_PENDING'
    }


def central_manager_review(state: VendorOnboardingState) -> VendorOnboardingState:
    """Wait for central manager approval (human-in-the-loop)"""
    # In real implementation, this pauses execution
    # Human resumes by providing approval data
    
    # For now, just return state (checkpoint handles waiting)
    return state


def route_to_parallel_approvals(state: VendorOnboardingState) -> VendorOnboardingState:
    """Prepare state for parallel department reviews"""
    return {
        **state,
        'current_status': 'DEPT_REVIEW',
        'dept_approvals': {
            'finance': None,
            'legal': None,
            'business': None
        }
    }


def aggregate_dept_approvals(state: VendorOnboardingState) -> VendorOnboardingState:
    """Collect parallel approval results and make final decision"""
    approvals = state['dept_approvals']
    
# Check if all departments have responded
    if any(v is None for v in approvals.values()):
        return state  # Still waiting
    
    # Check if all approved
    all_approved = all(
        dept['approved'] for dept in approvals.values()
    )
    
    return {
        **state,
        'current_status': 'APPROVED' if all_approved else 'REJECTED'
    }


# ============================================
# CONDITIONAL ROUTING (Your Rule Logic)
# ============================================

def should_proceed_after_validation(
    state: VendorOnboardingState
) -> Literal["proceed", "reject"]:
    """Route after validation"""
    if state['current_status'] == 'REJECTED':
        return "reject"
    return "proceed"


def should_proceed_after_central_review(
    state: VendorOnboardingState
) -> Literal["approved", "rejected"]:
    """Route after central manager review"""
    approval = state.get('central_manager_approval')
    
    if approval and approval['approved']:
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


# ============================================
# BUILD THE GRAPH
# ============================================

def create_vendor_onboarding_workflow():
    """Create the vendor onboarding LangGraph workflow"""
    
    workflow = StateGraph(VendorOnboardingState)
    
    # Add nodes
    workflow.add_node("validate", validate_submission)
    workflow.add_node("central_review", central_manager_review)
    workflow.add_node("parallel_routing", route_to_parallel_approvals)
    workflow.add_node("aggregate", aggregate_dept_approvals)
    
    # Set entry point
    workflow.set_entry_point("validate")
    
    # Add edges
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
            "waiting": "aggregate"  # Loop until all approvals in
        }
    )
    
    return workflow.compile()