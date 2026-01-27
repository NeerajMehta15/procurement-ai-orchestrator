from langgraph.checkpoint.postgres import PostgresSaver
from orchestrator.vendor_onboarding import create_vendor_onboarding_workflow
import os

# Database connection
DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/procurement"
)

# Create checkpointer
checkpointer = PostgresSaver.from_conn_string(DB_URI)

# Compile workflow with persistence
vendor_onboarding_app = create_vendor_onboarding_workflow()
vendor_onboarding_app = vendor_onboarding_app.compile(
    checkpointer=checkpointer
)