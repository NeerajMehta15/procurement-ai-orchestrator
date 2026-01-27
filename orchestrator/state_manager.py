"""
Database synchronization for LangGraph workflow states.
Handles persistence of workflow state to PostgreSQL tables.
"""

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from datetime import datetime
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

from orchestrator.states import (
    VendorOnboardingState,
    SKUCreationState,
    PriceApprovalState,
    POCreationState,
    GRNVerificationState,
    InvoiceProcessingState
)

load_dotenv()

# Database connection
def get_db_connection():
    """Get PostgreSQL connection to Supabase"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))


######################################### 
# Vendor Onboarding State Sync
#########################################

def sync_vendor_state_to_db(state: VendorOnboardingState) -> None:
    """
    Sync vendor onboarding state to database.
    Updates: vendors, workflow_requests, workflow_state_transitions
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        vendor_data = state['vendor_data']
        
        # 1. Upsert vendor record
        cur.execute("""
            INSERT INTO vendors (id, name, category, contact_email, tax_id, status, risk_score, created_at, updated_at)
            VALUES (%(vendor_id)s, %(name)s, %(category)s, %(contact_email)s, %(tax_id)s, %(status)s, %(risk_score)s, %(created_at)s, %(updated_at)s)
            ON CONFLICT (tax_id) 
            DO UPDATE SET 
                status = EXCLUDED.status,
                risk_score = EXCLUDED.risk_score,
                updated_at = EXCLUDED.updated_at
            RETURNING id
        """, {
            'vendor_id': state['request_id'],  # Using request_id as vendor_id for simplicity
            'name': vendor_data['name'],
            'category': vendor_data['category'],
            'contact_email': vendor_data['contact_email'],
            'tax_id': vendor_data['tax_id'],
            'status': state['current_status'],
            'risk_score': Json(state.get('risk_assessment')),
            'created_at': state['created_at'],
            'updated_at': state['updated_at']
        })
        
        vendor_id = cur.fetchone()[0]
        
        # 2. Upsert workflow_requests record
        cur.execute("""
            INSERT INTO workflow_requests (id, workflow_type, entity_id, entity_type, current_status, metadata, created_at, updated_at)
            VALUES (%(request_id)s, %(workflow_type)s, %(entity_id)s, 'vendor', %(current_status)s, %(metadata)s, %(created_at)s, %(updated_at)s)
            ON CONFLICT (workflow_type, entity_id)
            DO UPDATE SET
                current_status = EXCLUDED.current_status,
                metadata = EXCLUDED.metadata,
                updated_at = EXCLUDED.updated_at
        """, {
            'request_id': state['request_id'],
            'workflow_type': state['workflow_type'],
            'entity_id': vendor_id,
            'current_status': state['current_status'],
            'metadata': Json({
                'central_manager_approval': state.get('central_manager_approval'),
                'dept_approvals': state.get('dept_approvals'),
                'error': state.get('error')
            }),
            'created_at': state['created_at'],
            'updated_at': state['updated_at']
        })
        
        # 3. Log state transition (if status changed)
        # TODO: Track previous status to detect changes
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to sync vendor state to DB: {e}")
    finally:
        cur.close()
        conn.close()


def load_vendor_state_from_db(request_id: str) -> Optional[VendorOnboardingState]:
    """Load vendor onboarding state from database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                wr.id as request_id,
                wr.workflow_type,
                wr.current_status,
                wr.metadata,
                wr.created_at,
                wr.updated_at,
                v.name,
                v.category,
                v.contact_email,
                v.tax_id,
                v.risk_score
            FROM workflow_requests wr
            JOIN vendors v ON wr.entity_id = v.id
            WHERE wr.id = %s
        """, (request_id,))
        
        row = cur.fetchone()
        
        if not row:
            return None
        
        return VendorOnboardingState(
            request_id=row['request_id'],
            workflow_type=row['workflow_type'],
            current_status=row['current_status'],
            vendor_data={
                'name': row['name'],
                'category': row['category'],
                'contact_email': row['contact_email'],
                'tax_id': row['tax_id']
            },
            central_manager_approval=row['metadata'].get('central_manager_approval'),
            dept_approvals=row['metadata'].get('dept_approvals', {}),
            risk_assessment=row['risk_score'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            error=row['metadata'].get('error')
        )
        
    finally:
        cur.close()
        conn.close()


def log_state_transition(
    request_id: str, 
    from_status: Optional[str], 
    to_status: str,
    user_id: Optional[str] = None,
    reason: Optional[str] = None
) -> None:
    """Log workflow state transition for audit trail"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO workflow_state_transitions 
            (request_id, from_status, to_status, transitioned_by_user_id, reason, transitioned_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (request_id, from_status, to_status, user_id, reason, datetime.now()))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


def save_approval(
    request_id: str,
    approval_type: str,  # 'central_manager', 'finance', 'legal', 'business'
    decision: str,  # 'approved', 'rejected', 'pending'
    approver_user_id: str,
    comments: Optional[str] = None
) -> None:
    """Save approval decision to database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO approvals (request_id, approval_type, decision, approver_user_id, comments, decided_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (request_id, approval_type)
            DO UPDATE SET
                decision = EXCLUDED.decision,
                approver_user_id = EXCLUDED.approver_user_id,
                comments = EXCLUDED.comments,
                decided_at = EXCLUDED.decided_at
        """, (request_id, approval_type, decision, approver_user_id, comments, datetime.now()))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


######################################### 
# Dependency Validation (Rule-Based)
#########################################

def check_vendor_approved(vendor_id: str) -> bool:
    """Rule-based check: Is vendor approved?"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT status FROM vendors WHERE id = %s", (vendor_id,))
        result = cur.fetchone()
        return result and result[0] == 'APPROVED'
    finally:
        cur.close()
        conn.close()


def check_sku_approved(sku_id: str) -> bool:
    """Rule-based check: Is SKU approved?"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT status FROM skus WHERE id = %s", (sku_id,))
        result = cur.fetchone()
        return result and result[0] == 'APPROVED'
    finally:
        cur.close()
        conn.close()


def check_price_approved(price_id: str) -> bool:
    """Rule-based check: Is price approved?"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT status FROM prices WHERE id = %s", (price_id,))
        result = cur.fetchone()
        return result and result[0] == 'APPROVED'
    finally:
        cur.close()
        conn.close()


def check_po_exists(po_id: str) -> bool:
    """Rule-based check: Does PO exist?"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM purchase_orders WHERE id = %s", (po_id,))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


def check_grn_exists(grn_id: str) -> bool:
    """Rule-based check: Does GRN exist?"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM grns WHERE id = %s", (grn_id,))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


######################################### 
# TODO: Add sync functions for other workflows
# - sync_sku_state_to_db()
# - sync_price_state_to_db()
# - sync_po_state_to_db()
# - sync_grn_state_to_db()
# - sync_invoice_state_to_db()
#########################################