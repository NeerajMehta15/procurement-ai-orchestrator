"""
Initial database schema migration
Run with: python database/migrations/001_initial_schema.py
"""

MIGRATION_SQL = """
-- Create users table first (referenced by other tables)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Core entity tables
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    tax_id VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,
    risk_score JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL,
    duplicate_check_result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku_id UUID REFERENCES skus(id) ON DELETE RESTRICT,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    status VARCHAR(50) NOT NULL,
    valid_from DATE,
    valid_to DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_number VARCHAR(50) UNIQUE NOT NULL,
    vendor_id UUID REFERENCES vendors(id) ON DELETE RESTRICT,
    price_id UUID REFERENCES prices(id) ON DELETE RESTRICT,
    amount DECIMAL(15, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    approval_level VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS grns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grn_number VARCHAR(50) UNIQUE NOT NULL,
    po_id UUID REFERENCES purchase_orders(id) ON DELETE RESTRICT,
    quantity_received INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    physical_verification_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    grn_id UUID REFERENCES grns(id) ON DELETE RESTRICT,
    amount DECIMAL(15, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    document_url TEXT,
    ocr_extraction JSONB,
    line_items JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Workflow orchestration tables
CREATE TABLE IF NOT EXISTS workflow_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    current_status VARCHAR(50) NOT NULL,
    metadata JSONB,
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(workflow_type, entity_id)
);

CREATE TABLE IF NOT EXISTS workflow_state_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES workflow_requests(id) ON DELETE CASCADE,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    transitioned_by_user_id UUID REFERENCES users(id),
    reason TEXT,
    transitioned_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES workflow_requests(id) ON DELETE CASCADE,
    approval_type VARCHAR(50) NOT NULL,
    decision VARCHAR(20),
    approver_user_id UUID REFERENCES users(id),
    comments TEXT,
    decided_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(request_id, approval_type)
);

CREATE TABLE IF NOT EXISTS dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES workflow_requests(id) ON DELETE CASCADE,
    depends_on_request_id UUID REFERENCES workflow_requests(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(request_id, depends_on_request_id)
);

CREATE TABLE IF NOT EXISTS ai_agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES workflow_requests(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    output JSONB NOT NULL,
    model_used VARCHAR(100),
    generated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_vendors_status ON vendors(status);
CREATE INDEX IF NOT EXISTS idx_workflow_requests_type_status ON workflow_requests(workflow_type, current_status);
CREATE INDEX IF NOT EXISTS idx_approvals_request ON approvals(request_id);
CREATE INDEX IF NOT EXISTS idx_dependencies_request ON dependencies(request_id);
"""

if __name__ == "__main__":
    import psycopg2
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    
    try:
        cur.execute(MIGRATION_SQL)
        conn.commit()
        print("✓ Migration completed successfully")
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
    finally:
        cur.close()
        conn.close()