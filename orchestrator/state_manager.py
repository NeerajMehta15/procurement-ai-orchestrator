from typing import TypedDict, Literal, Optional, Dict, Any, List
from datetime import datetime



######################################### Vendor Onboarding Workflow State #########################################
VendorStatus = Literal[
    "DRAFT",
    "CENTRAL_PENDING", 
    "DEPT_REVIEW",
    "APPROVED",
    "REJECTED"
]

class VendorOnboardingState(TypedDict):
    """State for vendor onboarding workflow"""
    
    # Core identifiers
    request_id: str
    workflow_type: Literal["vendor_onboarding"]
    current_status: VendorStatus
    
    # Vendor data
    vendor_data: Dict[str, any]  # name, category, financials, etc.
    
    # Approval tracking
    central_manager_approval: Optional[Dict[str, any]] 
    dept_approvals: Dict[str, Optional[Dict[str, any]]] 
    
    # AI outputs (Phase 2)
    risk_assessment: Optional[Dict[str, any]]
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    error: Optional[str]


######################################### Contract Review Workflow State #########################################
