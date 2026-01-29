"""
End-to-end test for Vendor Onboarding Workflow.
Tests: validation → central review → parallel approvals → final status
"""

import sys
import os
from datetime import datetime
import uuid

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.workflow import execute_workflow, resume_workflow, get_workflow_state
from orchestrator.states import VendorOnboardingState


def print_section(title: str):
    """Pretty print section headers"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_vendor_onboarding_workflow():
    """Test complete vendor onboarding flow"""
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    print_section("TEST: Vendor Onboarding Workflow")
    print(f"Request ID: {request_id}\n")
    
    
    # ========================================
    # STEP 1: Create Initial Submission
    # ========================================
    print_section("Step 1: Submit Vendor for Onboarding")
    
    initial_state: VendorOnboardingState = {
        "request_id": request_id,
        "workflow_type": "vendor_onboarding",
        "current_status": "DRAFT",
        "vendor_data": {
            "name": "TechVendor Solutions Inc.",
            "category": "IT Services",
            "contact_email": "contact@techvendor.com",
            "tax_id": f"TAX{uuid.uuid4().hex[:8].upper()}",  # Unique tax ID
            "financials": {
                "annual_revenue": 5000000,
                "employee_count": 50
            }
        },
        "central_manager_approval": None,
        "dept_approvals": {},
        "risk_assessment": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "error": None
    }
    
    print(f"Vendor Name: {initial_state['vendor_data']['name']}")
    print(f"Category: {initial_state['vendor_data']['category']}")
    print(f"Tax ID: {initial_state['vendor_data']['tax_id']}")
    print(f"Initial Status: {initial_state['current_status']}")
    
    
    # ========================================
    # STEP 2: Execute Workflow (Will Pause at Central Review)
    # ========================================
    print_section("Step 2: Execute Workflow (Validation → Central Review)")
    
    try:
        result = execute_workflow(
            workflow_type="vendor_onboarding",
            initial_state=initial_state,
            thread_id=request_id
        )
        
        print(f"✓ Workflow executed")
        print(f"Current Status: {result['current_status']}")
        print(f"Error: {result.get('error', 'None')}")
        
        # Check if workflow paused at central_review
        if result['current_status'] == 'CENTRAL_PENDING':
            print("\n⏸️  Workflow paused at CENTRAL_PENDING (waiting for central manager approval)")
        
    except Exception as e:
        print(f"✗ Workflow execution failed: {e}")
        return
    
    
    # ========================================
    # STEP 3: Check Workflow State from Checkpoint
    # ========================================
    print_section("Step 3: Retrieve Current State from Checkpoint")
    
    current_state = get_workflow_state("vendor_onboarding", request_id)
    
    if current_state:
        print(f"✓ State retrieved from checkpoint")
        print(f"Status: {current_state['current_status']}")
        print(f"Vendor: {current_state['vendor_data']['name']}")
    else:
        print("✗ Could not retrieve state")
        return
    
    
    # ========================================
    # STEP 4: Simulate Central Manager Approval
    # ========================================
    print_section("Step 4: Central Manager Approves Vendor")
    
    central_approval = {
        "central_manager_approval": {
            "approved": True,
            "timestamp": datetime.now().isoformat(),
            "comments": "Vendor looks solid, financials verified",
            "user_id": "cm-001"  # Mock user ID
        }
    }
    
    print(f"Approval Decision: APPROVED")
    print(f"Comments: {central_approval['central_manager_approval']['comments']}")
    
    try:
        result = resume_workflow(
            workflow_type="vendor_onboarding",
            thread_id=request_id,
            update_state=central_approval
        )
        
        print(f"\n✓ Workflow resumed")
        print(f"New Status: {result['current_status']}")
        
        if result['current_status'] == 'DEPT_REVIEW':
            print("\n📋 Workflow moved to DEPT_REVIEW (parallel approvals)")
            print(f"Pending approvals: {list(result['dept_approvals'].keys())}")
        
    except Exception as e:
        print(f"✗ Resume failed: {e}")
        return
    
    
    # ========================================
    # STEP 5: Simulate Department Approvals (Parallel)
    # ========================================
    print_section("Step 5: Department Approvals (Finance, Legal, Business)")

    # All departments approve in parallel (collected before resuming workflow)
    print("\n[All Teams] Reviewing in parallel...")
    all_dept_approvals = {
        "dept_approvals": {
            "finance": {
                "approved": True,
                "timestamp": datetime.now().isoformat(),
                "comments": "Budget allocated, payment terms acceptable",
                "user_id": "finance-001"
            },
            "legal": {
                "approved": True,
                "timestamp": datetime.now().isoformat(),
                "comments": "Contract terms reviewed, compliance verified",
                "user_id": "legal-001"
            },
            "business": {
                "approved": True,
                "timestamp": datetime.now().isoformat(),
                "comments": "Strategic fit confirmed, capabilities verified",
                "user_id": "business-001"
            }
        }
    }

    print("  [Finance] Approved - Budget allocated, payment terms acceptable")
    print("  [Legal] Approved - Contract terms reviewed, compliance verified")
    print("  [Business] Approved - Strategic fit confirmed, capabilities verified")

    result = resume_workflow("vendor_onboarding", request_id, all_dept_approvals)
    print(f"\n✓ All departments approved")
    print(f"   Status: {result['current_status']}")


    # ========================================
    # STEP 6: Check Final Status
    # ========================================
    print_section("Step 6: Final Workflow Status")
    
    final_state = get_workflow_state("vendor_onboarding", request_id)
    
    if final_state:
        print(f"✓ Workflow completed")
        print(f"Final Status: {final_state['current_status']}")
        print(f"Vendor: {final_state['vendor_data']['name']}")
        print(f"All Approvals: {len([v for v in final_state['dept_approvals'].values() if v])}/3")
        
        if final_state['current_status'] == 'APPROVED':
            print("\n🎉 SUCCESS: Vendor fully approved!")
        else:
            print(f"\n⚠️  Unexpected final status: {final_state['current_status']}")
    else:
        print("✗ Could not retrieve final state")
    
    
    # ========================================
    # STEP 7: Verify Database Persistence
    # ========================================
    print_section("Step 7: Verify Database Persistence")
    
    from orchestrator.state_manager import load_vendor_state_from_db
    
    db_state = load_vendor_state_from_db(request_id)
    
    if db_state:
        print(f"✓ State persisted to database")
        print(f"DB Status: {db_state['current_status']}")
        print(f"DB Vendor Name: {db_state['vendor_data']['name']}")
    else:
        print("⚠️  State not found in database (this is expected if sync failed)")
    
    
    print_section("TEST COMPLETE")
    print(f"Request ID: {request_id}")
    print("Check Supabase to verify:")
    print("  - vendors table has new entry")
    print("  - workflow_requests table has entry")
    print("  - workflow_state_transitions has audit trail")
    print("  - checkpoints table has LangGraph state snapshots")


def test_validation_failure():
    """Test workflow with invalid vendor data"""
    
    print_section("TEST: Validation Failure")
    
    request_id = str(uuid.uuid4())
    
    # Missing required field: tax_id
    invalid_state: VendorOnboardingState = {
        "request_id": request_id,
        "workflow_type": "vendor_onboarding",
        "current_status": "DRAFT",
        "vendor_data": {
            "name": "Incomplete Vendor",
            "category": "IT Services",
            "contact_email": "test@vendor.com",
            # "tax_id": MISSING!
        },
        "central_manager_approval": None,
        "dept_approvals": {},
        "risk_assessment": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "error": None
    }
    
    print(f"Submitting vendor with missing tax_id...")
    
    result = execute_workflow(
        workflow_type="vendor_onboarding",
        initial_state=invalid_state,
        thread_id=request_id
    )
    
    print(f"\n✓ Workflow executed")
    print(f"Final Status: {result['current_status']}")
    print(f"Error Message: {result.get('error')}")
    
    if result['current_status'] == 'REJECTED':
        print("\n✓ Validation correctly rejected incomplete submission")
    else:
        print("\n✗ Expected REJECTED status")


if __name__ == "__main__":
    print("\n🚀 Starting Vendor Onboarding Workflow Tests\n")
    
    # Test 1: Successful workflow
    try:
        test_vendor_onboarding_workflow()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Validation failure
    print("\n\n")
    try:
        test_validation_failure()
    except Exception as e:
        print(f"\n❌ Validation test failed: {e}")
    
    print("\n✅ All tests completed\n")