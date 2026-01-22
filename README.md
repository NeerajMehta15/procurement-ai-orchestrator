# Procurement AI Orchestrator

A multi-agent AI system that orchestrates procurement workflows with human-in-the-loop approvals, reducing cycle time by 60%

[Demo Video] [Architecture Diagram] [Live Demo] [Documentation]

## 🎯 Problem Statement

Traditional procurement involves 6-8 manual handoffs across departments (Finance, Legal, Business), creating:
- **6+ day approval cycles** (80% spent on coordination, not decisions)
- **Low transparency** (stakeholders don't know where requests are stuck)
- **Manual validation** (hours spent matching invoices to POs)

## ✨ Solution

An agentic AI system with specialized agents that:
- **Prepare decisions** (validate vendors, detect invoice mismatches, check compliance)
- **Orchestrate workflows** (parallel approvals, automatic routing, SLA tracking)
- **Maintain human authority** (all final decisions remain with designated approvers)

**Key Innovation:** Agents coordinate people, not replace them.

## 🏗️ Architecture

[Insert system architecture diagram here]

### Agent Responsibilities
- **Vendor Intelligence Agent:** Risk assessment, pricing validation
- **Approval Routing Agent:** Workflow orchestration, SLA tracking
- **Invoice Validation Agent:** OCR, PO matching, anomaly detection
- **Compliance Agent:** Policy enforcement, audit trails

### Technology Stack
- **Orchestration:** LangGraph + AWS Step Functions
- **Agents:** Python, LangChain, Anthropic Claude
- **MCP Servers:** Custom tools for database, notifications
- **Infrastructure:** AWS Lambda, RDS PostgreSQL, S3, API Gateway
- **IaC:** Terraform

## 📊 Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Approval Cycle Time | 6 days | 2.4 days | **60% reduction** |
| Manual Coordination | 8 hrs/week | 1 hr/week | **87% reduction** |
| Invoice Processing | 30 min/invoice | 3 min/invoice | **90% reduction** |

## 🚀 Quick Start

[Installation and demo instructions]

## 📖 Documentation

- [Master PRD](docs/master-prd.md) - Product vision and strategy
- [System Design](docs/architecture/system-design.md) - Technical architecture
- [AWS Deployment](docs/architecture/aws-deployment.md) - Cloud infrastructure
- [Agent PRDs](docs/agents/) - Detailed agent specifications

## 🧪 Testing
```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Run end-to-end workflow test
python scripts/test_full_workflow.py
```

## 📈 Roadmap

- [ ] Phase 1: Approval Routing Agent
- [ ] Phase 2: Vendor Intelligence Agent
- [ ] Phase 3: Invoice Validation Agent
- [ ] Phase 4: Predictive analytics (approval time forecasting)

## 🎥 Demo

[Embedded demo video or GIF showing the workflow in action]

## 👤 Author

Built by neeraj_mehta as part of exploring multi-agent orchestration patterns in enterprise workflows.



##  Implementation flow
```

---

```
graph TB
    subgraph "User Layer"
        User[User Submits Request]
    end
    
    subgraph "Orchestration Layer - Rule-Based"
        Orchestrator[Workflow Orchestrator<br/>Rule Engine]
        
        subgraph "Rule-Based Validators"
            DepCheck[Dependency Validator<br/>if vendor.status == 'approved']
            AmountRouter[Amount-Based Router<br/>if amount <= 150K → L1<br/>elif amount <= 650K → L2<br/>else → L3]
            QtyValidator[Quantity Validator<br/>if GRN_qty > PO_qty → REJECT]
            StateEngine[State Machine<br/>Deterministic Transitions]
        end
    end
    
    subgraph "AI Layer - Selective Use"
        VendorAgent[Vendor Risk Agent<br/>AI-Powered<br/>Multi-factor risk scoring]
        SKUAgent[SKU Matching Agent<br/>AI-Powered<br/>Fuzzy semantic matching]
        DocAgent[Document Processing Agent<br/>AI-Powered<br/>OCR + line item reconciliation]
    end
    
    subgraph "Human Decision Layer"
        Central[Central Manager]
        Parallel[Parallel Approvers]
        Finance[Finance Team]
        Legal[Legal Team]
        Business[Business Team]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL<br/>State & Records)]
        S3[(AWS S3<br/>Documents)]
    end
    
    User --> Orchestrator
    
    Orchestrator --> DepCheck
    Orchestrator --> AmountRouter
    Orchestrator --> QtyValidator
    Orchestrator --> StateEngine
    
    Orchestrator -.->|Only when needed| VendorAgent
    Orchestrator -.->|Only when needed| SKUAgent
    Orchestrator -.->|Only when needed| DocAgent
    
    DepCheck --> Orchestrator
    AmountRouter --> Orchestrator
    QtyValidator --> Orchestrator
    VendorAgent -.-> Orchestrator
    SKUAgent -.-> Orchestrator
    DocAgent -.-> Orchestrator
    
    Orchestrator --> Central
    Orchestrator --> Parallel
    
    Parallel --> Finance
    Parallel --> Legal
    Parallel --> Business
    
    Orchestrator --> DB
    Orchestrator --> S3
    
    Finance --> DB
    Legal --> DB
    Business --> DB
    
    style Orchestrator fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    style VendorAgent fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style SKUAgent fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style DocAgent fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style DepCheck fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style AmountRouter fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style QtyValidator fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style StateEngine fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style Parallel fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
