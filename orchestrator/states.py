"""
State type definitions for all procurement workflows.
These define the shape of data flowing through LangGraph.
"""

from typing import TypedDict, Literal, Optional, Dict, Any
from datetime import datetime


######################################### 
# Vendor Onboarding Workflow State
#########################################

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
    vendor_data: Dict[str, Any]  # name, category, contact_email, tax_id, financials, etc.
    
    # Approval tracking
    central_manager_approval: Optional[Dict[str, Any]]  # {approved: bool, timestamp, comments, user_id}
    dept_approvals: Dict[str, Optional[Dict[str, Any]]]  # {finance: {...}, legal: {...}, business: {...}}
    
    # AI outputs (Phase 2)
    risk_assessment: Optional[Dict[str, Any]]  # {score: int, factors: [...], recommendations: [...]}
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    error: Optional[str]


######################################### 
# SKU Creation Workflow State (Phase 2)
#########################################

SKUStatus = Literal[
    "DRAFT",
    "VALIDATION",
    "BUSINESS_APPROVAL",
    "APPROVED",
    "REJECTED"
]

class SKUCreationState(TypedDict):
    """State for SKU creation workflow"""
    
    request_id: str
    workflow_type: Literal["sku_creation"]
    current_status: SKUStatus
    
    # SKU data
    sku_data: Dict[str, Any]  # name, category, description, vendor_id
    
    # Dependency validation
    vendor_id: str  # Must reference approved vendor
    
    # AI duplicate detection
    duplicate_check_result: Optional[Dict[str, Any]]
    
    # Approval tracking
    business_approval: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    error: Optional[str]


######################################### 
# Price Approval Workflow State (Phase 4)
#########################################

PriceStatus = Literal[
    "DRAFT",
    "VALIDATION",
    "MANAGER_APPROVAL",
    "APPROVED",
    "REJECTED"
]

class PriceApprovalState(TypedDict):
    """State for price approval workflow"""
    
    request_id: str
    workflow_type: Literal["price_approval"]
    current_status: PriceStatus
    
    price_data: Dict[str, Any]  # amount, currency, valid_from, valid_to, sku_id
    
    # Dependencies
    sku_id: str  # Must reference approved SKU
    
    # Approval
    manager_approval: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    error: Optional[str]


######################################### 
# PO Creation Workflow State (Phase 4)
#########################################

POStatus = Literal[
    "DRAFT",
    "COMPLIANCE_CHECK",
    "PO_L1",
    "PO_L2",
    "PO_L3",
    "APPROVED",
    "REJECTED"
]

class POCreationState(TypedDict):
    """State for purchase order creation workflow"""
    
    request_id: str
    workflow_type: Literal["po_creation"]
    current_status: POStatus
    
    po_data: Dict[str, Any]  # po_number, vendor_id, price_id, amount, quantity
    
    # Rule-based routing
    approval_level: Literal["L1", "L2", "L3"]  # Derived from amount
    
    # Dependencies
    vendor_id: str
    price_id: str
    
    # Approval
    level_approval: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    error: Optional[str]


######################################### 
# GRN Verification Workflow State (Phase 4)
#########################################

GRNStatus = Literal[
    "RECEIVED",
    "VALIDATION",
    "MANAGER_APPROVAL",
    "APPROVED",
    "REJECTED"
]

class GRNVerificationState(TypedDict):
    """State for goods receipt note verification workflow"""
    
    request_id: str
    workflow_type: Literal["grn_verification"]
    current_status: GRNStatus
    
    grn_data: Dict[str, Any]  # grn_number, po_id, quantity_received
    
    # Rule-based validation
    po_id: str
    po_quantity: int  # Retrieved from PO for comparison
    
    # Approval
    manager_approval: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    error: Optional[str]


######################################### 
# Invoice Processing Workflow State (Phase 4)
#########################################

InvoiceStatus = Literal[
    "RECEIVED",
    "VALIDATION",
    "FINANCE_APPROVAL",
    "APPROVED",
    "REJECTED"
]

class InvoiceProcessingState(TypedDict):
    """State for invoice processing workflow"""
    
    request_id: str
    workflow_type: Literal["invoice_processing"]
    current_status: InvoiceStatus
    
    invoice_data: Dict[str, Any]  # invoice_number, grn_id, amount, document_url, line_items
    
    # AI document processing (Phase 2)
    ocr_extraction: Optional[Dict[str, Any]]
    line_item_matches: Optional[Dict[str, Any]]
    
    # Dependencies
    grn_id: str
    
    # Approval
    finance_approval: Optional[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime
    error: Optional[str]